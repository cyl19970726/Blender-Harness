"""渲染 FBX 动画多帧帧条(验证动作动态)。鲁棒取景:用中间帧 evaluated(变形后)顶点算包围盒。
Usage: blender -b -P scripts/render_fbx_anim.py -- <fbx> <outdir> [nframes] [size] [yaw_deg]"""
import bpy, sys, math, os, mathutils
argv = sys.argv[sys.argv.index("--")+1:]
fbx, outdir = argv[0], argv[1]
nframes = int(argv[2]) if len(argv) > 2 else 8
res = int(argv[3]) if len(argv) > 3 else 480
yaw = math.radians(float(argv[4])) if len(argv) > 4 else 0.0
os.makedirs(outdir, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx)
fmin, fmax = 1e9, -1e9
for a in bpy.data.actions:
    fr = a.frame_range; fmin = min(fmin, fr[0]); fmax = max(fmax, fr[1])
if fmax < fmin: fmin, fmax = 1, 120
print("frame range", fmin, fmax)
sc = bpy.context.scene
def evaluated_bounds(frame):
    sc.frame_set(int(frame))
    deps = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in [o for o in sc.objects if o.type == "MESH"]:
        ev = o.evaluated_get(deps)
        try: me = ev.to_mesh()
        except Exception: continue
        for v in me.vertices:
            pts.append(o.matrix_world @ v.co)
        ev.to_mesh_clear()
    return pts
pts = evaluated_bounds((fmin+fmax)//2) or evaluated_bounds(fmin)
minc = mathutils.Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
maxc = mathutils.Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center = (minc+maxc)/2; dims = maxc-minc
print("bounds dims", round(dims.x,3), round(dims.y,3), round(dims.z,3))
# up-axis: pick the largest dim as height (Z usually after FBX import to Blender Z-up)
h = max(dims.x, dims.y, dims.z)
cam_data = bpy.data.cameras.new("cam"); cam_data.type = "ORTHO"
cam_data.ortho_scale = h*1.3
cam = bpy.data.objects.new("cam", cam_data); sc.collection.objects.link(cam)
sc.camera = cam
dist = h*4
# orbit camera around Z(up) by yaw, looking horizontally at center
cx = center.x + dist*math.sin(yaw); cy = center.y - dist*math.cos(yaw)
cam.location = (cx, cy, center.z)
cam.rotation_euler = (math.radians(90), 0, yaw)
for ang in [(60,0,30),(60,0,-160),(120,0,200)]:
    ld = bpy.data.lights.new("L", type="SUN"); ld.energy = 3
    L = bpy.data.objects.new("L", ld); sc.collection.objects.link(L); L.rotation_euler = tuple(math.radians(x) for x in ang)
world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.16,0.17,0.2,1)
engs = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engs else "BLENDER_EEVEE"
sc.render.resolution_x = sc.render.resolution_y = res
for i in range(nframes):
    f = int(fmin + (fmax-fmin)*i/(nframes-1)); sc.frame_set(f)
    sc.render.filepath = os.path.join(outdir, "f%02d.png" % i)
    bpy.ops.render.render(write_still=True)
print("done")
