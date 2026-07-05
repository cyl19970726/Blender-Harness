"""Render static GLB model multiview boards for source-asset inspection.

Usage:
  blender -b -P scripts/render_glb_multiview.py -- <in.glb> <outdir> [size]

This is intentionally small and dependency-free. It is for raw-source
inspection, not final lighting/lookdev.
"""
import json
import math
import os
import sys

import bpy
import mathutils


argv = sys.argv[sys.argv.index("--") + 1:]
src = argv[0]
outdir = argv[1]
res = int(argv[2]) if len(argv) > 2 else 768
os.makedirs(outdir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
scene = bpy.context.scene

mesh_objects = [o for o in scene.objects if o.type == "MESH"]
if not mesh_objects:
    raise SystemExit("No mesh objects found after GLB import")


def mesh_points():
    pts = []
    for obj in mesh_objects:
        for corner in obj.bound_box:
            pts.append(obj.matrix_world @ mathutils.Vector(corner))
    return pts


pts = mesh_points()
minc = mathutils.Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
maxc = mathutils.Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center = (minc + maxc) / 2
dims = maxc - minc
max_dim = max(dims.x, dims.y, dims.z)

tris = 0
verts = 0
for obj in mesh_objects:
    verts += len(obj.data.vertices)
    tris += sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons)

report = {
    "source": src,
    "mesh_count": len(mesh_objects),
    "object_count": len(scene.objects),
    "vertex_count": verts,
    "triangle_count_estimate": tris,
    "bounds_min": [round(minc.x, 6), round(minc.y, 6), round(minc.z, 6)],
    "bounds_max": [round(maxc.x, 6), round(maxc.y, 6), round(maxc.z, 6)],
    "bounds_size": [round(dims.x, 6), round(dims.y, 6), round(dims.z, 6)],
    "materials": [m.name for m in bpy.data.materials],
    "images": [{"name": img.name, "size": list(img.size)} for img in bpy.data.images],
    "animations": [a.name for a in bpy.data.actions],
}
with open(os.path.join(outdir, "import-report.json"), "w") as f:
    json.dump(report, f, indent=2)

world = bpy.data.worlds.new("world")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.025, 0.026, 0.03, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.8

for rot in [(55, 0, 35), (65, 0, -145), (35, 0, 155)]:
    data = bpy.data.lights.new("sun", type="SUN")
    data.energy = 2.5
    light = bpy.data.objects.new("sun", data)
    scene.collection.objects.link(light)
    light.rotation_euler = tuple(math.radians(v) for v in rot)

cam_data = bpy.data.cameras.new("camera")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("camera", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def look_at(obj, target):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render_view(name, direction, scale=1.22):
    direction = mathutils.Vector(direction).normalized()
    cam.location = center + direction * max_dim * 4.0
    look_at(cam, center)
    cam.data.ortho_scale = max_dim * scale
    scene.render.filepath = os.path.join(outdir, f"{name}.png")
    bpy.ops.render.render(write_still=True)


engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
scene.render.resolution_x = res
scene.render.resolution_y = res
scene.view_settings.view_transform = "Filmic"
scene.view_settings.look = "Medium High Contrast"
scene.view_settings.exposure = 0
scene.view_settings.gamma = 1

views = [
    ("front", (0, -1, 0), 1.22),
    ("back", (0, 1, 0), 1.22),
    ("left", (-1, 0, 0), 1.22),
    ("right", (1, 0, 0), 1.22),
    ("top", (0, 0, 1), 1.22),
    ("iso45", (1, -1, 0.55), 1.25),
    ("closeup", (0.72, -1, 0.35), 0.55),
]
for item in views:
    render_view(*item)

print(json.dumps(report, indent=2))
