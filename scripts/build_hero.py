#!/usr/bin/env python3
"""Process generated crystalline-scholar images into matted sprites (alpha=luminance,
face washed into a featureless glow per the 无面 rule), then composite a
"四俊抵门一揖" hero still over the real 进贤门 plate to judge the CONCEPT before animating.
"""
import sys, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageEnhance

ROOT = Path(__file__).resolve().parent.parent
GEN = Path("/tmp/xian_gen")
PORT = ROOT / "public/ar/spots/jinxianmen/portal"
PLATE = ROOT / "public/ar/spots/jinxianmen/user.png"


def matte(img: Image.Image) -> Image.Image:
    """Pure-black bg → alpha from luminance; trim to the figure bbox."""
    img = img.convert("RGB")
    lum = img.convert("L")
    # lift faint particles, crush the near-black bg to transparent
    lum = lum.point(lambda v: 0 if v < 10 else min(255, int((v - 10) * 1.15)))
    out = img.convert("RGBA")
    out.putalpha(lum)
    bbox = lum.point(lambda v: 255 if v > 14 else 0).getbbox()
    if bbox:
        out = out.crop(bbox)
    return out


def deface(sprite: Image.Image) -> Image.Image:
    """Wash the head region into a smooth featureless glow (无面)."""
    w, h = sprite.size
    # head ≈ top-center band of the figure
    hx, hy = w * 0.5, h * 0.13
    hr = w * 0.17
    # heavily blur just the head area, then drop a soft bright core over it
    head_box = (int(hx - hr * 1.5), int(hy - hr * 1.7), int(hx + hr * 1.5), int(hy + hr * 1.7))
    head_box = (max(0, head_box[0]), max(0, head_box[1]), min(w, head_box[2]), min(h, head_box[3]))
    region = sprite.crop(head_box).filter(ImageFilter.GaussianBlur(7))
    sprite.paste(region, head_box)
    # soft glow core to erase any residual features
    glow = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r, a in ((hr * 1.25, 60), (hr * 0.8, 90), (hr * 0.45, 120)):
        gd.ellipse([hx - r, hy - r, hx + r, hy + r], fill=(190, 235, 240, a))
    glow = glow.filter(ImageFilter.GaussianBlur(5))
    return Image.alpha_composite(sprite, glow)


def tint(sprite: Image.Image, mul) -> Image.Image:
    r, g, b, a = sprite.split()
    r = r.point(lambda v: min(255, int(v * mul[0])))
    g = g.point(lambda v: min(255, int(v * mul[1])))
    b = b.point(lambda v: min(255, int(v * mul[2])))
    return Image.merge("RGBA", (r, g, b, a))


def add_onto(base: Image.Image, sprite: Image.Image, cx, cy, target_h):
    """Additive-composite a sprite centered at (cx,cy) scaled to target_h px tall."""
    sc = target_h / sprite.height
    s = sprite.resize((max(1, int(sprite.width * sc)), int(target_h)), Image.LANCZOS)
    ox, oy = int(cx - s.width / 2), int(cy - s.height / 2)
    bw, bh = base.size
    x0, y0 = max(0, ox), max(0, oy)
    x1, y1 = min(bw, ox + s.width), min(bh, oy + s.height)
    if x1 <= x0 or y1 <= y0:
        return
    reg = base.crop((x0, y0, x1, y1)).convert("RGBA")
    sp = s.crop((x0 - ox, y0 - oy, x1 - ox, y1 - oy))
    rp, pp = reg.load(), sp.load()
    for j in range(reg.height):
        for i in range(reg.width):
            pr, pg, pb, pa = pp[i, j]
            if pa == 0:
                continue
            k = pa / 255.0
            br, bg, bb, ba = rp[i, j]
            rp[i, j] = (min(255, int(br + pr * k)), min(255, int(bg + pg * k)), min(255, int(bb + pb * k)), 255)
    base.paste(reg, (x0, y0))


def main():
    # 1) process & save sprites — near=gold(bow), far=cyan(stand)
    goldbow = deface(matte(Image.open(GEN / "goldbow-31.png")))
    goldbow2 = deface(matte(Image.open(GEN / "goldbow-7.png")))
    stand = deface(matte(Image.open(GEN / "stand-7.png")))
    goldbow.save(PORT / "xian-bow.png")        # 近端鎏金四俊(拱手)
    stand.save(PORT / "xian-stand.png")        # 远端青瓷贤士(行进)
    print("saved sprites", goldbow.size, stand.size)

    # 2) hero still over the real plate
    plate = Image.open(PLATE).convert("RGBA")
    plate = ImageEnhance.Brightness(plate).enhance(0.92)  # slight night dim
    W, H = plate.size
    GOLD = (1.18, 0.96, 0.55)
    GOLDW = (1.25, 1.05, 0.7)
    CYAN = (0.5, 0.95, 1.05)
    CYAND = (0.4, 0.85, 1.0)

    # 匾额 gold flare (where 拓字 condenses into 进贤) — soft warm glow near the plaque
    flare = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(flare)
    px, py = W * 0.5, H * 0.46
    for r, a in ((W * 0.16, 70), (W * 0.10, 95), (W * 0.06, 120)):
        fd.ellipse([px - r, py - r * 0.7, px + r, py + r * 0.7], fill=(255, 210, 120, a))
    flare = flare.filter(ImageFilter.GaussianBlur(18))
    plate = Image.alpha_composite(plate, flare)

    # far procession (cyan, small, mid-path)
    add_onto(plate, tint(stand, CYAND), W * 0.40, H * 0.555, H * 0.16)
    add_onto(plate, tint(stand, CYAND), W * 0.60, H * 0.555, H * 0.16)
    add_onto(plate, tint(stand, CYAN), W * 0.32, H * 0.60, H * 0.20)
    add_onto(plate, tint(stand, CYAN), W * 0.69, H * 0.60, H * 0.20)

    # 拓字 on the path (load the gold glyphs)
    for i, (gx, gy, gw) in enumerate([(0.46, 0.63, 0.07), (0.55, 0.69, 0.085), (0.43, 0.76, 0.1), (0.57, 0.84, 0.12)]):
        gp = PORT / f"glyph-{i}.png"
        if gp.exists():
            g = Image.open(gp).convert("RGBA")
            add_onto(plate, g, W * gx, H * gy, H * gw)

    # 四俊 (gold, big, foreground row, bowing) — sprite already gold; only a gentle lift
    heroes = [goldbow2, goldbow, goldbow, goldbow2]
    LIFT = (1.05, 1.0, 0.92)
    for k, (hx, hh) in enumerate([(0.255, 0.34), (0.42, 0.41), (0.585, 0.41), (0.75, 0.34)]):
        add_onto(plate, tint(heroes[k], LIFT), W * hx, H * 0.79, H * hh)

    out = Path("/tmp/hero_frame.png")
    plate.convert("RGB").save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
