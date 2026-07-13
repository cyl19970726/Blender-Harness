"""Blender-side quicklook action.

This file is executed by Blender, not imported by the host package.  It only
uses bpy/mathutils and writes raw views plus an inspection report.  The host
process validates media, hashes outputs and commits the run atomically.
"""

import argparse
import json
import math
import sys
import traceback
from pathlib import Path

import bpy
from mathutils import Vector


VIEW_DIRECTIONS = {
    "front": Vector((0.0, -1.0, 0.0)),
    "back": Vector((0.0, 1.0, 0.0)),
    "left": Vector((-1.0, 0.0, 0.0)),
    "right": Vector((1.0, 0.0, 0.0)),
    "top": Vector((0.0, 0.0, 1.0)),
    "hero": Vector((1.15, -1.35, 0.75)).normalized(),
    "closeup": Vector((0.9, -1.25, 0.35)).normalized(),
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--subject-mode", choices=("single_object", "whole_scene"), default="single_object")
    return parser.parse_args(argv)


def import_asset(path):
    suffix = path.suffix.lower()
    if suffix == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(path))
    else:
        # The host starts Blender with --factory-startup and explicitly enables
        # import add-ons. Calling read_factory_settings here disables those
        # add-ons on Blender 4.0 system packages, so clear objects instead.
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        if suffix in {".glb", ".gltf"}:
            result = bpy.ops.import_scene.gltf(filepath=str(path))
        elif suffix == ".fbx":
            result = bpy.ops.import_scene.fbx(filepath=str(path))
        elif suffix == ".obj":
            if hasattr(bpy.ops.wm, "obj_import"):
                result = bpy.ops.wm.obj_import(filepath=str(path))
            else:
                result = bpy.ops.import_scene.obj(filepath=str(path))
        else:
            raise RuntimeError("unsupported quicklook input: %s" % suffix)
        if set(result) != {"FINISHED"}:
            raise RuntimeError("asset import did not finish: %s" % sorted(result))


def visible_geometry(subject_mode):
    geometry = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type in {"MESH", "CURVE", "SURFACE", "META", "FONT"} and not obj.hide_render
    ]
    if subject_mode == "single_object" and len(geometry) != 1:
        raise RuntimeError(
            "single_object subject mode requires exactly one visible geometry object; found %d. "
            "Use whole_scene explicitly when all visible geometry belongs to the review subject." % len(geometry)
        )
    return geometry


def bounds(objects):
    points = []
    for obj in objects:
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    if not points:
        raise RuntimeError("asset contains no renderable geometry")
    minimum = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maximum = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    center = (minimum + maximum) * 0.5
    dimensions = maximum - minimum
    if max(dimensions) <= 1e-8:
        raise RuntimeError("asset bounds are empty or degenerate")
    return minimum, maximum, center, dimensions


def inspect_scene(minimum, maximum, dimensions):
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    vertices = 0
    polygons = 0
    triangles = 0
    for obj in meshes:
        mesh = obj.data
        vertices += len(mesh.vertices)
        polygons += len(mesh.polygons)
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
    return {
        "blender_version": bpy.app.version_string,
        "embedded_python": sys.version.split()[0],
        "object_count": len(bpy.context.scene.objects),
        "mesh_object_count": len(meshes),
        "material_count": len(bpy.data.materials),
        "armature_count": sum(1 for obj in bpy.context.scene.objects if obj.type == "ARMATURE"),
        "action_count": len(bpy.data.actions),
        "vertex_count": vertices,
        "polygon_count": polygons,
        "triangle_count": triangles,
        "bounds": {
            "min": list(minimum),
            "max": list(maximum),
            "dimensions": list(dimensions),
        },
    }


def configure_scene(size):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.show_specular_highlight = True
    # Blender renamed the AgX looks in 5.x. Choose from the runtime enum so
    # quicklook stays usable across supported Blender releases.
    look_items = {
        item.identifier
        for item in scene.view_settings.bl_rna.properties["look"].enum_items
    }
    for candidate in ("AgX - Medium High Contrast", "Medium High Contrast", "None"):
        if candidate in look_items:
            scene.view_settings.look = candidate
            break
    for obj in scene.objects:
        if obj.type in {"ARMATURE", "EMPTY", "LIGHT", "CAMERA"}:
            obj.hide_render = True
    camera_data = bpy.data.cameras.new("BH_QUICKLOOK_CAMERA")
    camera_data.lens = 55
    camera = bpy.data.objects.new("BH_QUICKLOOK_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    camera.hide_render = False
    scene.camera = camera
    return camera


def aim(camera, location, target):
    camera.location = location
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()


def render_views(output, camera, center, dimensions):
    output.mkdir(parents=True, exist_ok=True)
    radius = max(dimensions) * 0.5
    fov = camera.data.angle
    base_distance = max(radius / math.tan(fov * 0.42), radius * 2.8)
    rendered = []
    for name, direction in VIEW_DIRECTIONS.items():
        distance = base_distance * (0.72 if name == "closeup" else 1.0)
        target = center + Vector((0.0, 0.0, dimensions.z * 0.08))
        aim(camera, target + direction * distance, target)
        path = output / (name + ".png")
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        rendered.append(str(path.name))
    return rendered


def main():
    args = parse_args()
    input_path = Path(args.input).resolve()
    output = Path(args.output).resolve()
    report_path = output / "quicklook-report.raw.json"
    output.mkdir(parents=True, exist_ok=True)
    try:
        import_asset(input_path)
        geometry = visible_geometry(args.subject_mode)
        minimum, maximum, center, dimensions = bounds(geometry)
        camera = configure_scene(args.size)
        views_dir = output / "views"
        rendered = render_views(views_dir, camera, center, dimensions)
        report = {
            "status": "succeeded",
            "input": str(input_path),
            "subject": {
                "mode": args.subject_mode,
                "objects": [obj.name for obj in geometry],
            },
            "views": rendered,
            "metrics": inspect_scene(minimum, maximum, dimensions),
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        report = {
            "status": "failed",
            "input": str(input_path),
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
