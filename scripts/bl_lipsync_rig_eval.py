# Tier A 绑骨半 —— 在 Blender 里跑(blender_cmd.py exec)。
# 确定性 scrub:rest vs 张嘴(SCRUB_DEG),算每顶点 world 位移,把"下巴隔离"
# 的可机检不变量评成 pass/fail+旋钮,写 /tmp/rig_report.json。
# 每条判据=一个真实踩过的坑:支点过高→脸歪;上沿渗脸颊→糊脸;左右不对称→歪;
# 支点以上动→糊到眼额帽;弧长过大→显假。
import bpy, math, json
from mathutils import Vector

ARM = "Armature"; JAW = "mixamorig:Jaw"
SCRUB_DEG = 12.0
MOUTH_LINE = 0.62  # rel-height,嘴缝线(本模型实测;换模型需重标)

arm = bpy.data.objects[ARM]
mesh = [o for o in bpy.data.objects if o.type == 'MESH'][0]


def wv():
    ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [mesh.matrix_world @ v.co for v in ev.data.vertices]


bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='POSE')
for b in arm.pose.bones:
    b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0)
bpy.context.view_layer.update()
rest = wv()
zs = [p.z for p in rest]; zmin = min(zs); H = max(zs) - zmin

# roll(edit 模式读)
bpy.ops.object.mode_set(mode='EDIT')
jb_e = arm.data.edit_bones[JAW]; roll_deg = abs(math.degrees(jb_e.roll))
bpy.ops.object.mode_set(mode='POSE')

jb = arm.pose.bones[JAW]; jb.rotation_mode = 'XYZ'; jb.rotation_euler = (math.radians(SCRUB_DEG), 0, 0)
bpy.context.view_layer.update()
opn = wv()

disp = [(opn[i] - rest[i]).length for i in range(len(rest))]
moved = [i for i in range(len(disp)) if disp[i] > 0.001 * H]
pivot_rel = ((arm.matrix_world @ arm.pose.bones[JAW].head).z - zmin) / H
rels = [(rest[i].z - zmin) / H for i in moved]
span_lo, span_hi = (min(rels), max(rels)) if moved else (0, 0)
above_pivot = sum(1 for r in rels if r > pivot_rel + 0.04)
above_pct = 100 * above_pivot / max(len(moved), 1)
moved_pct = 100 * len(moved) / len(disp)
maxdisp_pct = 100 * max(disp) / H
# 左右对称:moved 按 Y 分两半
ymean = sum(rest[i].y for i in moved) / len(moved) if moved else 0
L = [disp[i] for i in moved if rest[i].y > ymean]
R = [disp[i] for i in moved if rest[i].y <= ymean]
mL = sum(L) / len(L) if L else 0; mR = sum(R) / len(R) if R else 0
asym = 100 * abs(mL - mR) / max(mL, mR, 1e-9)

# 顶点位移最大处的高度(应在下巴=低处)
maxi = max(moved, key=lambda i: disp[i]) if moved else 0
maxdisp_rel = (rest[maxi].z - zmin) / H if moved else 0


def chk(name, val, op, ref, knob, why):
    if op == "<=": ok = val <= ref
    elif op == ">=": ok = val >= ref
    elif op == "between": ok = ref[0] <= val <= ref[1]
    else: ok = False
    return {"name": name, "value": round(val, 3) if isinstance(val, float) else val,
            "op": op, "ref": ref, "pass": bool(ok), "knob": knob, "why": why}


checks = [
    chk("rig_pivot_rel", pivot_rel, "between", [MOUTH_LINE - 0.04, MOUTH_LINE + 0.06],
        "pivot.z", "支点高度:过高→张嘴绕高支点大弧斜甩=脸歪"),
    chk("rig_roll_deg", roll_deg, "<=", 3.0, "roll=0", "骨 roll 非0→开合轴歪→张嘴斜"),
    chk("rig_lr_asym_pct", asym, "<=", 5.0, "roll=0 / pivot 居中", "左右不对称→脸歪"),
    chk("rig_span_upper_rel", span_hi, "<=", MOUTH_LINE + 0.05, "权重上边界↓",
        "移动区上沿超嘴线→权重渗脸颊=糊脸"),
    chk("rig_above_pivot_pct", above_pct, "<=", 1.0, "权重/支点", "支点以上有移动→糊到眼/额/帽"),
    chk("rig_moved_pct", moved_pct, "between", [1.5, 8.0], "权重范围", "动太多=带动整脸 / 太少=没张"),
    chk("rig_maxdisp_pctH", maxdisp_pct, "<=", 3.5, "MAXOPEN↓ / pivot", "下巴尖弧长过大→显假"),
    chk("rig_maxdisp_at_chin", maxdisp_rel, "<=", span_lo + 0.06, "pivot/tail 朝向",
        "最大位移应在下巴尖(低处),不在中脸"),
]

# 复位
for b in arm.pose.bones:
    b.rotation_quaternion = (1, 0, 0, 0); b.rotation_euler = (0, 0, 0)
bpy.ops.object.mode_set(mode='OBJECT')

out = {"H": round(H, 3), "scrub_deg": SCRUB_DEG, "mouth_line": MOUTH_LINE,
       "raw": {"pivot_rel": round(pivot_rel, 3), "span": [round(span_lo, 3), round(span_hi, 3)],
               "asym_pct": round(asym, 2), "moved_pct": round(moved_pct, 2),
               "maxdisp_pctH": round(maxdisp_pct, 2)},
       "checks": checks}
json.dump(out, open("/tmp/rig_report.json", "w"), ensure_ascii=False, indent=2)
print("RIG EVAL DONE  fails=%d" % sum(1 for c in checks if not c["pass"]))
for c in checks:
    print("  [%s] %-22s = %s (阈 %s %s)" % ("OK" if c["pass"] else "XX", c["name"], c["value"], c["op"], c["ref"]))
