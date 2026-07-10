# 运动渲染器(filmstrip 版)—— Blender 跑(blender_cmd.py exec)。
# 读 /tmp/lipsync_curve.json(真实音频信号驱动的 jaw_deg(t)),挑一段说话活跃窗口里
# 张合差异最大的 N 帧,逐帧把 jaw 摆到该角度、渲头部特写(正面)→ /tmp/film_*.png。
# 由 driver 用 sharp 拼成一排。看这排静帧:对称吗?张合幅度自然吗?(动态/抖看曲线图)
import bpy, math, json
from mathutils import Vector

ARM = "Armature"; JAW = "mixamorig:Jaw"; N = 8
cur = json.load(open("/tmp/lipsync_curve.json")); deg = cur["deg"]; fps = cur["fps"]

# 选说话活跃窗口:找连续 ~6s 里平均开口最大的起点
win = int(6 * fps)
best = max(range(0, max(1, len(deg) - win), fps),
          key=lambda s: sum(deg[s:s + win]) / win) if len(deg) > win else 0
seg = deg[best:best + win]
# 在窗口里均匀取 N 帧(覆盖闭/半/张)
idx = [best + int(i * (len(seg) - 1) / (N - 1)) for i in range(N)]

arm = bpy.data.objects[ARM]; sc = bpy.context.scene
hb = arm.pose.bones['mixamorig:Head']; hw = arm.matrix_world @ hb.head
face = Vector((hw.x, hw.y, hw.z + 0.06))
cam = bpy.data.objects.get('JawCam')
if not cam:
    cd = bpy.data.cameras.new('JawCam'); cam = bpy.data.objects.new('JawCam', cd); sc.collection.objects.link(cam)
cam.data.lens = 45; sc.camera = cam
sc.render.resolution_x = 360; sc.render.resolution_y = 360
d = (face - cam.location)
cam.location = Vector((face.x + 0.7, face.y, face.z + 0.08))
cam.rotation_euler = (face - cam.location).to_track_quat('-Z', 'Y').to_euler()

bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='POSE')
jb = arm.pose.bones[JAW]; jb.rotation_mode = 'XYZ'
out = []
for k, fi in enumerate(idx):
    for b in arm.pose.bones:
        b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0)
    jb.rotation_euler = (math.radians(deg[fi]), 0, 0)
    bpy.context.view_layer.update()
    p = "/tmp/film_%02d.png" % k
    sc.render.filepath = p; bpy.ops.render.render(write_still=True)
    out.append({"k": k, "frame": fi, "t": round(fi / fps, 2), "deg": round(deg[fi], 1)})
for b in arm.pose.bones:
    b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0)
bpy.ops.object.mode_set(mode='OBJECT')
json.dump(out, open("/tmp/film_meta.json", "w"))
print("FILMSTRIP DONE N=%d window_t=%.1f-%.1f" % (N, best / fps, (best + win) / fps))
print("degs:", [o["deg"] for o in out])
