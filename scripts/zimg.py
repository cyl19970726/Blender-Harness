#!/usr/bin/env python3
"""Parametrized Z-Image-Turbo generator (token from .hf-token for ZeroGPU quota).

usage: python3 scripts/zimg.py OUT.png "PROMPT" [seed] [resolution]
"""
import sys, os, time, pathlib, shutil
ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKEN = os.environ.get("HF_TOKEN") or (ROOT / ".hf-token").read_text().strip()
from gradio_client import Client

SPACE = "mcp-tools/Z-Image-Turbo"


def connect():
    for i in range(6):
        try:
            return Client(SPACE, token=TOKEN, verbose=False)
        except Exception as e:
            print("  connect retry", type(e).__name__, str(e)[:80], flush=True); time.sleep(5)
    sys.exit("connect failed")


def main():
    out = sys.argv[1]
    prompt = sys.argv[2]
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    res = sys.argv[4] if len(sys.argv) > 4 else "1024x1536 ( 2:3 )"
    c = connect()
    last = None
    for i in range(6):
        try:
            r = c.predict(prompt=prompt, random_seed=False, resolution=res,
                          seed=seed, shift=3, steps=10, api_name="/generate")
            gallery = r[0] if isinstance(r, (list, tuple)) else r
            item = gallery[0] if isinstance(gallery, list) else gallery
            path = item.get("image") if isinstance(item, dict) else item
            if isinstance(path, dict):
                path = path.get("path") or path.get("url")
            pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(path, out)
            print("OK ->", out)
            return
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:160]}"
            print("  gen retry:", last, flush=True); time.sleep(6)
    sys.exit(f"gen failed; last={last}")


if __name__ == "__main__":
    main()
