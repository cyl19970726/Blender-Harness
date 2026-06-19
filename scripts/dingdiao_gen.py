#!/usr/bin/env python3
"""Generate one 定调图 from a prompt via the Z-Image-Turbo HF Space (token = more quota).

Usage:
  printf '%s' "<prompt>" | python3 scripts/dingdiao_gen.py <out.png> [seed] [resolution]

Reads the prompt from STDIN (avoids shell-quoting long CJK prompts). Token from
$HF_TOKEN or the first readable .hf-token among the candidate paths below.
"""
import sys, os, time, pathlib, shutil

CANDIDATE_TOKENS = [
    os.environ.get("HF_TOKEN"),
    str(pathlib.Path(__file__).resolve().parent.parent / ".hf-token"),
    os.path.expanduser("~/ai-luodi/jieyanggucheng-jyx3d/.hf-token"),
    os.path.expanduser("~/.hf-token"),
]

def load_token():
    for c in CANDIDATE_TOKENS:
        if not c:
            continue
        if c.startswith("hf_"):
            return c
        try:
            return pathlib.Path(c).read_text().strip()
        except Exception:
            continue
    sys.exit("no HF token (set HF_TOKEN or place a .hf-token)")

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/dingdiao.png"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    res = sys.argv[3] if len(sys.argv) > 3 else "1024x1536 ( 2:3 )"
    prompt = sys.stdin.read().strip()
    if not prompt:
        sys.exit("empty prompt on stdin")
    from gradio_client import Client
    tok = load_token()
    c = None
    for i in range(6):
        try:
            c = Client("mcp-tools/Z-Image-Turbo", token=tok, verbose=False)
            break
        except Exception as e:
            print("connect retry", type(e).__name__, str(e)[:80], flush=True); time.sleep(5)
    if c is None:
        sys.exit("connect failed")
    last = None
    for i in range(6):
        try:
            r = c.predict(prompt=prompt, random_seed=False, resolution=res,
                          seed=seed, shift=3, steps=8, api_name="/generate")
            g = r[0] if isinstance(r, (list, tuple)) else r
            it = g[0] if isinstance(g, list) else g
            p = it.get("image") if isinstance(it, dict) else it
            if isinstance(p, dict):
                p = p.get("path") or p.get("url")
            pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(p, out)
            print("OK ->", out)
            return
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:160]}"
            print("gen retry:", last, flush=True); time.sleep(6)
    sys.exit(f"gen failed; last={last}")

if __name__ == "__main__":
    main()
