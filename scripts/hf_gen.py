#!/usr/bin/env python3
"""Generate a clean reference image via HF Inference (token from .hf-token).
Resilient to the flaky proxy here (retries on network errors)."""
import sys, os, time, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKEN = os.environ.get("HF_TOKEN") or (ROOT / ".hf-token").read_text().strip()

from huggingface_hub import InferenceClient

PROMPT = (
    "Full body 3D render of a cute chibi boy mascot, standing upright facing forward, "
    "clean symmetric A-pose, arms relaxed and slightly away from the body, both hands empty and open, "
    "legs straight, whole body from head to toe visible and centered. "
    "Big round head, large friendly dark-brown eyes, a tiny red vermilion dot on the forehead, short brown hair. "
    "On his head a tall hat shaped like a Chinese city-gate pavilion roof with curved green glazed tiles, gold trim, "
    "and a small gold plaque. He wears an ornate Chaoshan-style red and green hanfu robe with rich gold embroidery, "
    "a decorative gold belt, green trousers, gold boots. Gentle happy smile. "
    "No props, nothing in hands, no weapons, no ribbons, no text, no background objects. "
    "Plain pure white background, soft even studio lighting, glossy collectible figurine style, very high detail."
)
MODELS = [
    "black-forest-labs/FLUX.1-schnell",
    "stabilityai/stable-diffusion-xl-base-1.0",
]

def gen(out):
    global PROMPT
    PROMPT = os.environ.get("GEN_PROMPT", PROMPT)
    last = None
    for model in MODELS:
        client = InferenceClient(model=model, token=TOKEN)
        for attempt in range(5):
            try:
                img = client.text_to_image(PROMPT, width=832, height=1216)
                pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
                img.save(out)
                print(f"OK {model} -> {out} {img.size}")
                return
            except Exception as e:
                last = f"{model}: {type(e).__name__}: {str(e)[:120]}"
                print("  retry:", last, flush=True)
                time.sleep(5)
    sys.exit(f"all failed; last={last}")

if __name__ == "__main__":
    gen(sys.argv[1] if len(sys.argv) > 1 else "public/ar/magnets/_src/jyx-apose.png")
