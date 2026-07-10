#!/usr/bin/env python3
"""Generate via the Z-Image-Turbo HF Space using gradio_client + token (ZeroGPU quota)."""
import sys, os, time, pathlib, shutil
ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKEN = os.environ.get("HF_TOKEN") or (ROOT / ".hf-token").read_text().strip()
from gradio_client import Client

SPACE = "mcp-tools/Z-Image-Turbo"
PROMPT = (
    "Full body 3D render of a cute chibi boy mascot, standing upright facing forward, "
    "clean symmetric A-pose, arms relaxed slightly away from the body, both hands empty and open, "
    "legs straight, whole body head to toe visible and centered. "
    "Big round head, large friendly dark-brown eyes, a tiny red vermilion dot on the forehead, short brown hair. "
    "On his head a tall hat shaped like a Chinese city-gate pavilion roof with curved green glazed tiles, gold trim, "
    "small gold plaque. Ornate Chaoshan-style red and green hanfu robe with rich gold embroidery, gold belt, "
    "green trousers, gold boots. Gentle happy smile. "
    "No props, nothing in hands, no weapons, no ribbons, no text, no background objects. "
    "Plain pure white background, soft even studio lighting, glossy collectible figurine style, very high detail."
)

def connect():
    for i in range(6):
        try:
            return Client(SPACE, hf_token=TOKEN, verbose=False)
        except Exception as e:
            print("  connect retry", type(e).__name__, str(e)[:80], flush=True); time.sleep(5)
    sys.exit("connect failed")

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "public/ar/magnets/_src/jyx-apose.png"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    c = connect()
    if "--api" in sys.argv:
        c.view_api(); sys.exit(0)
    last = None
    for i in range(6):
        try:
            r = c.predict(
                prompt=PROMPT, random_seed=False, resolution="832x1248 ( 2:3 )",
                seed=seed, shift=3, steps=8, api_name="/generate",
            )
            print("raw result type:", type(r))
            gallery = r[0] if isinstance(r, (list, tuple)) else r
            # gallery is a list of dicts {'image': path} or path strings
            item = gallery[0] if isinstance(gallery, list) else gallery
            path = item.get("image") if isinstance(item, dict) else item
            if isinstance(path, dict):
                path = path.get("path") or path.get("url")
            pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(path, out)
            print("OK ->", out)
            break
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:160]}"
            print("  gen retry:", last, flush=True); time.sleep(6)
    else:
        sys.exit(f"gen failed; last={last}")
