"""把 FBX 骨架动画渲成关节球帧条(无 mesh 时验证动作动态)。
Usage: blender -b -P scripts/render_skeleton_anim.py -- <fbx> <outdir> [nframes] [size] [yaw]"""
import bpy, sys, math, os, mathutils
argv = sys.argv[sys.argv.index("--")+1:]
fbx, outdir = argv[0], argv[1]
nframes = int(argv[2]) if len(argv) > 2 else 8
res = int(argv[3]) if len(argv) > 3 else 460
yaw = math.radians(float(argv[4])) if len(argv) > 4 else 0.0
os.makedirs(outdir, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx)
sc = bpy.context.scene
arm = next(o for o in sc.objects if o.type == "ARMATURE")
# frame range
fmin, fmax = 1, 120
if arm.animation_data and arm.animation_data.action:
    fr = arm.animation_data.action.frame_range; fmin, fmax = int(fr[0]), int(fr[1])
else:
    # search NLA / any action
    for a in bpy.data.actions:
        fr=a.frame_range; fmin,fmax=int(fr[0]),int(fr[1])
print("frame range", fmin, fmax)
HANDS = ("hand","wrist","finger","thumb")
HEAD = ("head","neck")
def world_heads(frame):
    sc.frame_set(frame)
    bpy.context.view_layer.update()
    out = []
    for pb in arm.pose.bones:
        w = arm.matrix_world @ pb.head
        nm = pb.name.lower()
        kind = "hand" if any(k in nm for k in HANDS) else ("head" if any(k in nm for k in HEAD) else "body")
        out.append((w, kind))
        if pb.children == ():  # leaf: also add tail
            out.append((arm.matrix_world @ pb.tail, kind))
    return out
# bounds from mid frame
mid = world_heads((fmin+fmax)//2)
xs=[p[0].x for p in mid]; ys=[p[0].y for p in mid]; zs=[p[0].z for p in mid]
center=mathutils.Vector(((min(xs)+max(xs))/2,(min(ys)+max(ys))/2,(min(zs)+max(zs))/2))
h=max(max(xs)-min(xs),max(ys)-min(ys),max(zs)-min(zs))
print("height", round(h,3))
mats={}
for k,c in (("hand",(1,0.4,0.2)),("head",(0.3,0.8,1)),("body",(0.95,0.85,0.5))):
    m=bpy.data.materials.new(k); m.use_nodes=True
    m.node_tree.nodes["Principled BSDF"].inputs[0].default_value=(*c,1)
    mats[k]=m
cam_data=bpy.data.cameras.new("c"); cam_data.type="ORTHO"; cam_data.ortho_scale=h*1.35
cam=bpy.data.objects.new("c",cam_data); sc.collection.objects.link(cam); sc.camera=cam
dist=h*4
cam.location=(center.x+dist*math.sin(yaw),center.y-dist*math.cos(yaw),center.z)
cam.rotation_euler=(math.radians(90),0,yaw)
for ang in [(60,0,30),(60,0,-150)]:
    ld=bpy.data.lights.new("L",type="SUN"); ld.energy=3
    L=bpy.data.objects.new("L",ld); sc.collection.objects.link(L); L.rotation_euler=tuple(math.radians(x) for x in ang)
world=bpy.data.worlds.new("w"); sc.world=world; world.use_nodes=True
world.node_tree.nodes["Background"].inputs[0].default_value=(0.13,0.14,0.17,1)
engs=[e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
sc.render.engine="BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engs else "BLENDER_EEVEE"
sc.render.resolution_x=sc.render.resolution_y=res
r=h*0.022
balls=[]
def clear():
    for b in balls: bpy.data.objects.remove(b,do_unlink=True)
    balls.clear()
for i in range(nframes):
    f=int(fmin+(fmax-fmin)*i/(nframes-1))
    pts=world_heads(f); clear()
    for w,kind in pts:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r*(1.7 if kind!="body" else 1.0),location=w)
        b=bpy.context.active_object; b.data.materials.append(mats[kind]); balls.append(b)
    sc.render.filepath=os.path.join(outdir,"f%02d.png"%i)
    bpy.ops.render.render(write_still=True)
    print("frame",i,"@",f)
