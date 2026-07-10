#!/usr/bin/env python3
"""真楼结构描金 — derive the gate's own structural edges (飞檐/斗拱/匾/立柱/脊) from the
real photo and render them as thin GOLD line-light, so the climax 点楼 lights up the
REAL building along its own contours (additive on the edges only) instead of washing a
glow over it. Panel 维2 root fix: "让真楼自己亮起来，不是在它前面加光柱."

Output is plate-aligned (same framing as user.png) so it overlays the building 1:1.
A vertical band split lets the AR reveal it sequentially 檐角→匾 ("点亮"有时间差, not a flash).
"""
import math
from pathlib import Path
from PIL import Image, ImageFilter, ImageChops, ImageOps

ROOT = Path(__file__).resolve().parent.parent
PORT = ROOT / "public/ar/spots/jinxianmen/portal"
PLATE = ROOT / "public/ar/spots/jinxianmen/user.png"


def main():
    im = Image.open(PLATE).convert("RGB")
    W, H = im.size
    gray = ImageOps.autocontrast(im.convert("L"))
    # structural edges
    edges = gray.filter(ImageFilter.GaussianBlur(0.6)).filter(ImageFilter.FIND_EDGES)
    edges = edges.point(lambda v: 255 if v > 38 else int(v * 2.2))
    edges = edges.filter(ImageFilter.MaxFilter(3))               # thicken to readable lines

    # keep only the BUILDING region (top ~58%), fade out toward the sky top & the foreground path
    mask = Image.new("L", (W, H), 0)
    mp = mask.load()
    top, bot = int(H * 0.04), int(H * 0.60)
    for y in range(H):
        if y < top:
            k = max(0.0, y / max(1, top))
        elif y <= bot:
            k = 1.0
        else:
            k = max(0.0, 1 - (y - bot) / (H * 0.12))
        kv = int(255 * k)
        for x in range(W):
            mp[x, y] = kv
    edges = ImageChops.multiply(edges, mask)

    # gold tint + soft glow so the lines read as luminous gilding
    glow = edges.filter(ImageFilter.GaussianBlur(3)).point(lambda v: int(v * 0.6))
    line_a = ImageChops.add(edges, glow)
    gold = Image.merge("RGB", [
        line_a.point(lambda v: min(255, int(v * 1.0))),
        line_a.point(lambda v: min(255, int(v * 0.82))),
        line_a.point(lambda v: min(255, int(v * 0.42))),
    ])
    out = gold.convert("RGBA")
    out.putalpha(line_a)
    out.save(PORT / "edge-trace.png")
    print("wrote edge-trace.png", out.size)


if __name__ == "__main__":
    main()
