#!/usr/bin/env python3
"""Reprocess generated scholars into TRANSLUCENT 光体 (not solid 塑像/神像).

Panel red-line: the gold figures read as opaque 庙堂塑像 with visible faces — forbidden.
Fix: (a) light blur to dissolve robe/face detail into a light-form; (b) HARD de-face —
erase the head region's alpha and replace with a smooth featureless glow orb (guarantee no
eyes/nose/mouth); (c) translucency cap + vertical gradient so the real building/path is
visible STRAIGHT THROUGH the body = 晶莹 see-through, never a solid idol; (d) keep the bright
chest/hands core + sparkle so it still reads as a figure, not fog.
"""
import math
from pathlib import Path
from PIL import Image, ImageFilter, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
GEN = Path("/tmp/xian_gen")
PORT = ROOT / "public/ar/spots/jinxianmen/portal"


def reprocess(src: str, out: str, translucency: float, blur: float = 2.6):
    im = Image.open(GEN / src).convert("RGB")
    lum = im.convert("L").point(lambda v: 0 if v < 10 else min(255, int((v - 10) * 1.1)))
    rgba = im.convert("RGBA")
    rgba.putalpha(lum)
    bbox = lum.point(lambda v: 255 if v > 14 else 0).getbbox()
    if bbox:
        rgba = rgba.crop(bbox)
    W, H = rgba.size
    # (a) dissolve solid-statue/face detail into a light-form
    rgba = rgba.filter(ImageFilter.GaussianBlur(blur))

    # (b) HARD de-face: erase head-region alpha, then drop a smooth glow orb
    a = rgba.getchannel("A")
    ap = a.load()
    hx, hy, hr = W * 0.5, H * 0.12, W * 0.17
    for y in range(max(0, int(hy - hr * 1.7)), min(H, int(hy + hr * 1.5))):
        for x in range(max(0, int(hx - hr * 1.5)), min(W, int(hx + hr * 1.5))):
            d = math.hypot((x - hx) / (hr * 1.35), (y - hy) / (hr * 1.55))
            if d < 1.0:
                ap[x, y] = int(ap[x, y] * min(1.0, d * 0.28))  # center fully erased
    rgba.putalpha(a)
    orb = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(orb)
    for rr, aa in ((hr * 1.05, 70), (hr * 0.68, 100), (hr * 0.4, 130)):
        od.ellipse([hx - rr, hy - rr, hx + rr, hy + rr], fill=(205, 236, 242, aa))
    rgba = Image.alpha_composite(rgba, orb.filter(ImageFilter.GaussianBlur(4)))

    # (c) translucency cap + vertical gradient (lower body more see-through)
    a = rgba.getchannel("A")
    ap = a.load()
    for y in range(H):
        vy = y / H
        kf = translucency * (1.0 - 0.4 * max(0.0, (vy - 0.4) / 0.6))
        for x in range(W):
            ap[x, y] = int(ap[x, y] * kf)
    rgba.putalpha(a)
    rgba.save(PORT / out)
    print("reprocessed", out, rgba.size)


if __name__ == "__main__":
    # near gold (more translucent so it stops reading as a solid gold idol)
    reprocess("goldbow-31.png", "xian-bow.png", 0.60)
    reprocess("goldbow-7.png", "xian-bow2.png", 0.60)
    reprocess("goldstand-7.png", "xian-stand-gold.png", 0.56)
    # far cyan (already half-transparent in panel's eyes; keep airy)
    s = "stand-7.png"
    reprocess(s, "xian-stand.png", 0.52)
    im = Image.open(PORT / "xian-stand.png").transpose(Image.FLIP_LEFT_RIGHT)
    im.save(PORT / "xian-stand2.png")
    print("done")
