"""Strip baked textures -> clean metallic-gold PBR, decimate, re-export a light GLB.
For solid-gold props (元宝): a clean Principled metal beats a matte baked texture, and
dropping the 3 images + decimating cuts a 16MB Hunyuan GLB to a few hundred KB (no Draco,
so no decoder config needed in three.js/A-Frame).

Usage: blender --background --python scripts/glb_cleanup_gold.py -- <in.glb> <out.glb> [target_tris]
"""
import bpy, sys

argv = sys.argv[sys.argv.index("--") + 1:]
src, out = argv[0], argv[1]
target_tris = int(argv[2]) if len(argv) > 2 else 12000

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]

# clean metallic-gold material (足金)
gold = bpy.data.materials.new("Gold足金")
gold.use_nodes = True
bsdf = gold.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.95, 0.70, 0.16, 1.0)
bsdf.inputs["Metallic"].default_value = 1.0
bsdf.inputs["Roughness"].default_value = 0.28

total_before = 0
for o in meshes:
    total_before += sum(len(p.vertices) - 2 for p in o.data.polygons)
    o.data.materials.clear()
    o.data.materials.append(gold)
    # decimate
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    if tris > target_tris:
        m = o.modifiers.new("dec", "DECIMATE")
        m.ratio = max(0.05, float(target_tris) / float(tris))
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier="dec")

# drop now-orphaned images
for img in list(bpy.data.images):
    if img.users == 0:
        bpy.data.images.remove(img)

total_after = 0
for o in meshes:
    total_after += sum(len(p.vertices) - 2 for p in o.data.polygons)

bpy.ops.export_scene.gltf(
    filepath=out, export_format="GLB",
    export_materials="EXPORT", export_image_format="NONE",
    export_yup=True,
)
print("TRIS %d -> %d ; wrote %s" % (total_before, total_after, out))
