"""三视图渲染:正/侧/背 正交视角,白底,供混元多视图图生3D。
Usage: blender -b -P scripts/render_threeview.py -- <glb> <outdir> [size]"""
import bpy, sys, math, os, mathutils
argv = sys.argv[sys.argv.index("--")+1:]
glb, outdir = argv[0], argv[1]
res = int(argv[2]) if len(argv) > 2 else 1024
os.makedirs(outdir, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
# reset any animation to rest/frame 0
bpy.context.scene.frame_set(0)
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
coords = []
for o in objs:
    for v in o.bound_box:
        coords.append(o.matrix_world @ mathutils.Vector(v))
minc = mathutils.Vector((min(c.x for c in coords), min(c.y for c in coords), min(c.z for c in coords)))
maxc = mathutils.Vector((max(c.x for c in coords), max(c.y for c in coords), max(c.z for c in coords)))
center = (minc+maxc)/2
dims = maxc-minc
cam_data = bpy.data.cameras.new("cam"); cam_data.type = "ORTHO"
cam_data.ortho_scale = max(dims.x, dims.z) * 1.15
cam = bpy.data.objects.new("cam", cam_data); bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam
# soft even lighting (character sheet style)
for ang in [(55,0,35),(55,0,-150),(120,0,200)]:
    ld = bpy.data.lights.new("L", type="SUN"); ld.energy = 2.5
    L = bpy.data.objects.new("L", ld); bpy.context.scene.collection.objects.link(L)
    L.rotation_euler = (math.radians(ang[0]), math.radians(ang[1]), math.radians(ang[2]))
world = bpy.data.worlds.new("w"); bpy.context.scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (1,1,1,1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
sc.render.resolution_x = sc.render.resolution_y = res
sc.render.film_transparent = False
dist = max(dims) * 3
# front(+Y looking -Y? glb front usually -Z toward viewer). Use: front=-Y axis, side=+X, back=+Y
# GLB faces +X -> front cam looks -X. Corrected turnaround:
views = {
  "front": ( dist, 0, 0, 90, 0, 90),
  "side":  ( 0, -dist, 0, 90, 0, 0),
  "back":  (-dist, 0, 0, 90, 0, -90),
}
for name,(x,y,z,rx,ry,rz) in views.items():
    cam.location = (center.x+x, center.y+y, center.z+z)
    cam.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    sc.render.filepath = os.path.join(outdir, name+".png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name)
