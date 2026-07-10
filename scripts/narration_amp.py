#!/usr/bin/env python3
"""Generate narration.amp.json — the amplitude envelope that drives 揭小贤's mouth.

Usage:
  python narration_amp.py <narration.mp3> [out.amp.json]
  # default out = sibling "<stem>.amp.json"  (narration.mp3 -> narration.amp.json)

Produces:  {"fps": 60, "amp": [a0, a1, ...]}  with a_i in 0..1 (3-decimal).

a_i is the gated + EMA-smoothed normalized RMS of THIS narration at frame i. It is
*exactly* window.__jyxAmp at runtime, so the same 4 SHARED mouth frames
(/ar/shared/jiexiaoxian/mouth/face_0..3.webp) + the mouthOpen morph + jaw open in
time with this clip's loudness. That is the whole per-magnet lip-sync coupling: the
mouth shapes are copy-agnostic; only this envelope is per-magnet. So a new magnet's
mouth syncs to its own copy for free — just regenerate this file from its mp3.

CRITICAL — verifier == runtime (see memory "verifier-must-mirror-runtime"):
  The constants + math below MUST stay identical to
    - the runtime: src/components/ar/{ArMagnetExperience,ArImageTrackingScene}.tsx
    - the gate/verifier: scripts/lipsync_invariants.py (decode + jaw_curve's rawamp half)
  `--check <existing.amp.json>` re-derives the envelope and fails loudly if it drifts
  from a known-good file (we use the already-calibrated gongfucha file as the anchor).
  If you change EMA/FLOOR/CEIL/GATE here, change them in all three places or the
  mouth will look right in tooling and wrong on a real phone.
"""
import sys, os, json, subprocess
import numpy as np

# ---- runtime params — MUST match lipsync_invariants.py + the TSX runtime (React side) ----
SR = 44100
WIN = 512
FPS = 60
FLOOR, CEIL, GATE, EMA = 0.018, 0.14, 0.08, 0.20


def decode(mp3):
    """mp3 -> mono float32 PCM @ SR (identical to lipsync_invariants.decode)."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "quiet", "-i", mp3, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32)


def amp_envelope(x):
    """Return amp[i] (0..1) per 1/FPS s — the React-side rawamp of jaw_curve()."""
    dur = len(x) / SR
    nf = int(dur * FPS)
    amp_s = 0.0
    amp = []
    for i in range(nf):
        s = int(i / FPS * SR)
        w = x[s:s + WIN]
        rms = float(np.sqrt(np.mean(w * w))) if len(w) else 0.0
        a = (rms - FLOOR) / (CEIL - FLOOR)
        a = 0.0 if a < 0 else 1.0 if a > 1 else a
        if a < GATE:
            a = 0.0
        amp_s += (a - amp_s) * EMA
        amp.append(round(amp_s if amp_s >= 0.01 else 0.0, 3))
    return amp


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)

    # --check mode: re-derive from the mp3 next to a known-good amp.json and compare.
    if sys.argv[1] == "--check":
        ref_json = sys.argv[2]
        ref = json.load(open(ref_json))
        mp3 = os.path.join(os.path.dirname(ref_json),
                           os.path.basename(ref_json).replace(".amp.json", ".mp3"))
        got = amp_envelope(decode(mp3))
        a, b = ref["amp"], got
        n = min(len(a), len(b))
        max_d = max((abs(a[i] - b[i]) for i in range(n)), default=0.0)
        mism = sum(1 for i in range(n) if abs(a[i] - b[i]) > 0.002)
        ok = ref["fps"] == FPS and abs(len(a) - len(b)) <= 1 and max_d <= 0.01 and mism <= n * 0.01
        print(f"check {ref_json}: fps {ref['fps']}=={FPS}, frames ref={len(a)} got={len(b)}, "
              f"max|Δ|={max_d:.4f}, frames>0.002={mism}/{n} -> {'PASS' if ok else 'FAIL'}")
        sys.exit(0 if ok else 1)

    mp3 = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(mp3)[0] + ".amp.json"
    amp = amp_envelope(decode(mp3))
    json.dump({"fps": FPS, "amp": amp}, open(out, "w"), separators=(",", ":"))
    print(f"wrote {out}  fps={FPS}  frames={len(amp)} (~{len(amp) / FPS:.1f}s)  max={max(amp):.3f}")


if __name__ == "__main__":
    main()
