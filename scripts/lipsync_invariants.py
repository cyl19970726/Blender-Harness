#!/usr/bin/env python3
"""Tier A —— 口型【确定性不变量闸】(信号半 + 合并绑骨半)。

把"运行时 amplitude->jaw 管线"离线复刻(必须和
src/components/ar/{ArMagnetExperience,ArImageTrackingScene}.tsx 的常数一致),
从 narration.mp3 算出 jaw(t),再把每条可机检判据评成 pass/fail + 【该拧哪个旋钮】。
另可合并 Blender 产出的 rig_report.json(scripts/bl_lipsync_rig_eval.py)得到绑骨半。

每条不变量都来自一个真实踩过的坑(脸歪/脸抖/糊脸/嘴不动…),只增不减。

用法:
  python lipsync_invariants.py <narration.mp3> [rig_report.json] [out_prefix=/tmp/lipsync]
产出:
  <out>_curve.png   jaw(t) 曲线(锯齿=抖)
  <out>_curve.json  {fps, deg:[...]}  给 filmstrip 渲染用
  <out>_report.json 全部不变量 + 总闸 + 旋钮建议
退出码 0=全绿,1=有 fail(供 CI/driver 用)。
"""
import sys, json, subprocess, math
import numpy as np
from PIL import Image, ImageDraw

# ---- 运行时参数(与 TSX 保持一致;改 TSX 必须同步改这里)----
SR = 44100; WIN = 512; FPS = 60
FLOOR, CEIL, GATE, EMA = 0.018, 0.14, 0.08, 0.20      # React 端
ATK, REL, MAXOPEN_RAD = 0.35, 0.22, 0.17              # 组件端 (~10deg)
MAXOPEN_DEG = math.degrees(MAXOPEN_RAD)

# ---- 信号不变量阈值(每条=一个踩过的坑)----
THRESH = {
    "jitter_reversals_per_sec": ("<=", 8.0, "EMA↑ / MAXOPEN↓", "嘴抖/buzz:方向反转太频繁"),
    "jitter_max_delta_deg":     ("<=", 1.3, "EMA↑",            "单帧跳变过大=抖"),
    "open_max_deg":             ("<=", MAXOPEN_DEG + 0.5, "MAXOPEN↓", "张口超上限"),
    "open_visible_deg":         (">=", 4.5, "CEIL↓ / MAXOPEN↑", "嘴基本不动(看不出说话)"),
    "dyn_range_mean_deg":       ("between", (1.3, 5.5), "CEIL / MAXOPEN", "动态范围(平均开口)不合适"),
    "silence_closed":           ("==", True, "GATE↑ / FLOOR↑", "静音段没闭嘴"),
    # —— 一致性不变量(口型↔配音):Tier B 双模型逮到后固化进来 ——
    "sync_lag_frames":          ("<=", 3.0, "EMA↓ / REL↓", "jaw 滞后/领先音频包络太多=音画不同步(一致性核心判据)"),
    "fall_rise_ratio":          ("<=", 2.2, "REL↑", "开快关慢的懒闭合长尾(嘴拖着不收)"),
}


def decode(mp3):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", mp3, "-ac", "1",
                          "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def jaw_curve(x):
    """复刻运行时:返回 jaw_deg(t) @ FPS + 每帧 gate 后的 raw amp。"""
    dur = len(x) / SR; nf = int(dur * FPS)
    amp_s = 0.0; comp = 0.0; deg = []; rawamp = []
    for i in range(nf):
        s = int(i / FPS * SR); w = x[s:s + WIN]
        rms = float(np.sqrt(np.mean(w * w))) if len(w) else 0.0
        a = (rms - FLOOR) / (CEIL - FLOOR)
        a = 0.0 if a < 0 else 1.0 if a > 1 else a
        if a < GATE: a = 0.0
        amp_s += (a - amp_s) * EMA
        tgt = amp_s if amp_s >= 0.01 else 0.0
        rawamp.append(tgt)
        comp += (tgt - comp) * (ATK if tgt > comp else REL)
        deg.append(math.degrees(comp * MAXOPEN_RAD))
    return np.array(deg), np.array(rawamp), dur


def signal_invariants(deg, rawamp, dur):
    d = np.diff(deg)
    sign = np.sign(d); sign[sign == 0] = 1
    reversals = int(np.sum(sign[1:] != sign[:-1]))
    # 静音段闭嘴:只看【持续静音】(rawamp==0 已连续 >=9 帧=150ms),排除 release 衰减尾
    # (修订自踩坑:原来把句末衰减斜坡也算静音→误报;真正要查的是"长停顿里嘴有没有合上")
    run = 0; sustained = []
    for i in range(len(rawamp)):
        run = run + 1 if rawamp[i] <= 0.0 else 0
        if run >= 9:
            sustained.append(deg[i])
    silence_closed = bool(len(sustained) == 0 or max(sustained) < 0.8)

    # —— 一致性:音频包络 env(rawamp) ↔ jaw(deg) 的互相关滞后(帧)——
    # jaw 是 env 经平滑得到的,理想 lag≈平滑引入的几帧;过大=看着不同步。
    env = rawamp - rawamp.mean(); jw = deg - deg.mean()
    lags = range(-10, 11); best_lag, best_c = 0, -1e9
    for L in lags:
        if L >= 0: c = float(np.dot(env[:len(env) - L], jw[L:]))
        else: c = float(np.dot(env[-L:], jw[:len(jw) + L]))
        if c > best_c: best_c, best_lag = c, L
    sync_lag_frames = abs(best_lag)

    # —— 开快关慢:落帧数 / 升帧数(懒闭合长尾)——
    rise = int(np.sum(d > 0.05)); fall = int(np.sum(d < -0.05))
    fall_rise_ratio = round(fall / max(rise, 1), 2)

    return {
        "jitter_reversals_per_sec": round(reversals / dur, 2),
        "jitter_max_delta_deg": round(float(np.abs(d).max()), 3),
        "open_max_deg": round(float(deg.max()), 2),
        "open_visible_deg": round(float(deg.max()), 2),
        "dyn_range_mean_deg": round(float(deg[deg > 0.3].mean()) if (deg > 0.3).any() else 0.0, 2),
        "silence_closed": silence_closed,
        "sync_lag_frames": sync_lag_frames,
        "fall_rise_ratio": fall_rise_ratio,
    }


def judge(name, val):
    op, ref, knob, why = THRESH[name]
    if op == "<=": ok = val <= ref
    elif op == ">=": ok = val >= ref
    elif op == "==": ok = val == ref
    elif op == "between": ok = ref[0] <= val <= ref[1]
    else: ok = True
    return {"name": name, "value": val, "op": op, "ref": ref,
            "pass": bool(ok), "knob": knob, "why": why}


def plot(deg, dur, path):
    W, H = 1200, 300; T = min(8.0, dur); n = int(T * FPS)
    img = Image.new("RGB", (W, H), "white"); dr = ImageDraw.Draw(img)
    dr.line([(0, H - 40), (W, H - 40)], fill="#ccc")
    mx = max(deg[:n].max(), 1.0)
    dr.line([(int(j / n * W), int(H - 40 - (deg[j] / mx) * (H - 60))) for j in range(n)],
            fill="#c0392b", width=2)
    dr.text((8, 6), "jaw open(deg) vs t  max=%.1f" % deg[:n].max(), fill="black")
    img.save(path)


def main():
    mp3 = sys.argv[1]
    rig = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2].endswith(".json") else None
    outp = ([a for a in sys.argv[2:] if not a.endswith(".json")] or ["/tmp/lipsync"])[0]

    x = decode(mp3)
    deg, rawamp, dur = jaw_curve(x)
    plot(deg, dur, outp + "_curve.png")
    json.dump({"fps": FPS, "deg": [round(float(v), 4) for v in deg]}, open(outp + "_curve.json", "w"))

    checks = [judge(n, v) for n, v in signal_invariants(deg, rawamp, dur).items()]
    rig_checks = []
    if rig:
        try: rig_checks = json.load(open(rig)).get("checks", [])
        except Exception as e: print("WARN: rig report unreadable:", e)

    allc = rig_checks + checks
    fails = [c for c in allc if not c["pass"]]
    report = {"params": {"FLOOR": FLOOR, "CEIL": CEIL, "GATE": GATE, "EMA": EMA,
                         "ATK": ATK, "REL": REL, "MAXOPEN_DEG": round(MAXOPEN_DEG, 1)},
              "duration_s": round(dur, 2), "checks": allc,
              "gate": "PASS" if not fails else "FAIL",
              "fix_knobs": [{"why": c["why"], "knob": c["knob"], "value": c["value"], "ref": c["ref"]} for c in fails]}
    json.dump(report, open(outp + "_report.json", "w"), ensure_ascii=False, indent=2)

    print("=== Tier A 不变量闸 (gate=%s) ===" % report["gate"])
    for c in allc:
        print("  [%s] %-28s = %s   (阈 %s %s)%s" % (
            "OK" if c["pass"] else "XX", c["name"], c["value"], c["op"], c["ref"],
            "" if c["pass"] else "  -> 拧: " + c["knob"]))
    print("report:", outp + "_report.json")
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
