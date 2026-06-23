"""把 HY-Motion 源骨架动画(rest-relative)retarget 到目标已绑骨角色,烘成动画并导出 GLB。
FK 重定向:对每根映射骨,把"源骨相对其 rest 的世界旋转增量"施加到目标骨的 rest 上。
Usage: blender -b -P scripts/retarget_bake.py -- <target_rigged.fbx> <source_motion.fbx> <out.glb>"""
import bpy, sys, math
from mathutils import Matrix, Quaternion
argv = sys.argv[sys.argv.index("--")+1:]
tgt_f, src_f, out_glb = argv[0], argv[1], argv[2]

MAP = {  # target_bone : source_bone
 "Hips":"Pelvis","Spine":"Spine1","Spine1":"Spine2","Spine2":"Spine3","Neck":"Neck","Head":"Head",
 "LeftShoulder":"L_Collar","LeftArm":"L_Shoulder","LeftForeArm":"L_Elbow","LeftHand":"L_Wrist",
 "RightShoulder":"R_Collar","RightArm":"R_Shoulder","RightForeArm":"R_Elbow","RightHand":"R_Wrist",
 "LeftUpLeg":"L_Hip","LeftLeg":"L_Knee","LeftFoot":"L_Ankle",
 "RightUpLeg":"R_Hip","RightLeg":"R_Knee","RightFoot":"R_Ankle",
}

DAMP = {  # per-target-bone delta scale: crown must stay level, bow modest, arms full
 "Head":0.0,"Neck":0.5,"Hips":0.0,
 "Spine":0.7,"Spine1":0.7,"Spine2":0.6,
 "LeftShoulder":1.0,"LeftArm":1.0,"LeftForeArm":1.0,"LeftHand":1.0,
 "RightShoulder":1.0,"RightArm":1.0,"RightForeArm":1.0,"RightHand":1.0,
 "LeftUpLeg":0.25,"LeftLeg":0.25,"LeftFoot":0.0,
 "RightUpLeg":0.25,"RightLeg":0.25,"RightFoot":0.0,
}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=tgt_f)
tgt_arm = next(o for o in bpy.context.scene.objects if o.type=="ARMATURE")
tgt_objs = set(bpy.context.scene.objects)
bpy.ops.import_scene.fbx(filepath=src_f)
src_arm = next(o for o in bpy.context.scene.objects if o.type=="ARMATURE" and o not in tgt_objs)

# 绑骨自带的动作(如 MotionType 待机)→ 改名 Idle 保留;拱手 bake 进一个新建 Gongshou action
_idle = tgt_arm.animation_data.action if (tgt_arm.animation_data and tgt_arm.animation_data.action) else None
if _idle: _idle.name = "Idle"; _idle.use_fake_user = True
if not tgt_arm.animation_data: tgt_arm.animation_data_create()
_gong = bpy.data.actions.new("Gongshou"); _gong.use_fake_user = True
tgt_arm.animation_data.action = _gong

# frame range
fmin, fmax = 1, 120
if src_arm.animation_data and src_arm.animation_data.action:
    fr = src_arm.animation_data.action.frame_range; fmin, fmax = int(fr[0]), int(fr[1])
print("frames", fmin, fmax)

# rest WORLD 3x3 for both (bone.matrix_local is armature-space rest)
def rest_world3(arm, bone): return (arm.matrix_world @ arm.data.bones[bone].matrix_local).to_3x3()
# rest LOCAL-relative-to-parent 3x3 for target
def rest_parent_rel3(arm, bname):
    b = arm.data.bones[bname]
    if b.parent: return (b.parent.matrix_local.inverted() @ b.matrix_local).to_3x3()
    return b.matrix_local.to_3x3()

bpy.context.scene.frame_set(fmin); bpy.context.view_layer.update()
S_rest = {s: (src_arm.matrix_world @ src_arm.pose.bones[s].matrix).to_3x3() for s in MAP.values()}  # frame-1 neutral
T_rest = {t: rest_world3(tgt_arm, t) for t in MAP}
# target hierarchy order (parents before children)
order = [b.name for b in tgt_arm.data.bones if b.name in MAP]  # data.bones is already hierarchy order

for pb in tgt_arm.pose.bones: pb.rotation_mode = "QUATERNION"
sc = bpy.context.scene
for f in range(fmin, fmax+1):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    S_anim = {s: (src_arm.matrix_world @ src_arm.pose.bones[s].matrix).to_3x3() for s in MAP.values()}
    for t in order:
        s = MAP[t]
        delta = S_anim[s] @ S_rest[s].inverted()                 # world rotation increment of source
        d = DAMP.get(t, 1.0)
        if d != 1.0:
            qd = Quaternion().slerp(delta.to_quaternion(), d)     # scale rotation toward identity
            delta = qd.to_matrix()
        desired_world = delta @ T_rest[t]                         # apply to target rest world
        pb = tgt_arm.pose.bones[t]
        parent_world3 = (tgt_arm.matrix_world.to_3x3() if not pb.parent
                         else (tgt_arm.matrix_world @ pb.parent.matrix).to_3x3())
        rest_rel = rest_parent_rel3(tgt_arm, t)
        basis3 = rest_rel.inverted() @ parent_world3.inverted() @ desired_world
        pb.matrix_basis = basis3.to_4x4()
        bpy.context.view_layer.update()
    for t in order:
        tgt_arm.pose.bones[t].keyframe_insert("rotation_quaternion", frame=f)
print("baked")
# rename baked clip -> Gongshou; drop source armature + stray source action; export only target
for _img in bpy.data.images:
    try:
        if _img.has_data and (_img.size[0] > 1024 or _img.size[1] > 1024):
            _img.scale(min(1024,_img.size[0] or 1024), min(1024,_img.size[1] or 1024)); print("scaled tex", _img.name, _img.size[:])
    except Exception as e: print("scale skip", e)
# 拱手已 bake 进 active(Gongshou)action;Idle 已保留。删源骨架 + 仅留 Idle+Gongshou,两动作都导出。
bpy.ops.object.select_all(action="DESELECT")
src_arm.select_set(True)
for ch in list(src_arm.children): ch.select_set(True)
bpy.context.view_layer.objects.active = src_arm
bpy.ops.object.delete()
for a in list(bpy.data.actions):
    if a.name not in ("Idle", "Gongshou"): bpy.data.actions.remove(a)
bpy.ops.object.select_all(action="DESELECT")
for o in bpy.context.scene.objects: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=out_glb, export_format="GLB", export_animations=True,
    export_animation_mode="ACTIONS", export_yup=True, use_selection=True)
print("exported", out_glb, "actions:", [a.name for a in bpy.data.actions])
