#!/usr/bin/env python3
"""光粒贤士 sprite — a 拱手作揖 scholar silhouette built from DENSE small glowing dots.

The panel's verdict on the old xian-walk.png: "白线描鬼影/垂直拉丝毛刺 (扫把精/裹尸布)" —
a line-drawn robe with seaweed tendrils that turns to fog when stacked additively.

Fix (panel FIX2): a volumetric crystalline figure — cyan-white small round dots
(r 1.5-3px) densely packed into a clear human silhouette holding a 拱手 bow,
brighter at the chest core, a sparse 流光尾迹 trailing off the hem. No lines,
no solid fill block, no face. Saved on black for ADDITIVE compositing; code tints
per-figure (far=青瓷 / near=鎏金) so we keep ONE neutral bright sprite here.
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops

OUT = Path(__file__).resolve().parent.parent / "public/ar/spots/jinxianmen/portal/xian-crystal.png"
W, H = 384, 560

# deterministic LCG so the sprite is reproducible (no Math.random in the pipeline ethos)
class R:
    def __init__(self, s): self.s = s
    def f(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7fffffff
        return self.s / 0x7fffffff
rng = R(0xC0FFEE)


def build_silhouette() -> Image.Image:
    """A front-facing scholar with a slight forward bow, hands clasped (拱手) at chest."""
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    cx = W * 0.5
    lean = 14  # px the upper body leans forward (the bow)

    # robe: A-line trapezoid, shoulders narrow, hem wide
    sh_y, sh_w = H * 0.30, W * 0.30
    hem_y, hem_w = H * 0.95, W * 0.56
    d.polygon([
        (cx - sh_w/2 + lean, sh_y), (cx + sh_w/2 + lean, sh_y),
        (cx + hem_w/2, hem_y), (cx - hem_w/2, hem_y),
    ], fill=255)
    # neck/shoulder yoke fill so head joins the robe
    d.polygon([
        (cx - sh_w*0.34 + lean, sh_y - H*0.04), (cx + sh_w*0.34 + lean, sh_y - H*0.04),
        (cx + sh_w/2 + lean, sh_y), (cx - sh_w/2 + lean, sh_y),
    ], fill=255)

    # bowed head (tilted forward, slightly small) + scholar cap hint
    hx, hy, hr = cx + lean*1.4, H * 0.19, W * 0.105
    d.ellipse([hx - hr, hy - hr*1.15, hx + hr, hy + hr*0.95], fill=255)
    # 幞头/cap: a soft cap above the head
    d.ellipse([hx - hr*1.05, hy - hr*1.7, hx + hr*1.05, hy - hr*0.2], fill=255)

    # 拱手: clasped sleeves form a rounded bump at chest center, in front
    bx, by = cx + lean*0.5, H * 0.46
    d.ellipse([bx - W*0.16, by - H*0.075, bx + W*0.16, by + H*0.085], fill=255)
    # sleeves draping down from the clasp
    d.polygon([
        (bx - W*0.16, by), (bx + W*0.16, by),
        (cx + W*0.14, hem_y*0.99), (cx - W*0.14, hem_y*0.99),
    ], fill=255)

    return m.filter(ImageFilter.GaussianBlur(3))


def core_field(x: float, y: float) -> float:
    """Brightness weight: brightest at the chest core, fading to the hem & edges."""
    cx, ccy = W * 0.5, H * 0.46
    dx, dy = (x - cx) / (W * 0.5), (y - ccy) / (H * 0.55)
    r = math.sqrt(dx*dx + dy*dy)
    base = max(0.18, 1.0 - r * 0.95)
    # a touch more glow up the central spine
    spine = math.exp(-((x - cx) / (W * 0.16))**2) * 0.35
    return min(1.0, base + spine)


def make_dot(radius: float, peak: float):
    s = int(radius * 2) + 3
    img = Image.new("RGB", (s, s), (0, 0, 0))
    px = img.load()
    c = (s - 1) / 2
    for j in range(s):
        for i in range(s):
            dd = math.hypot(i - c, j - c) / radius
            if dd > 1.0:
                continue
            a = (1.0 - dd) ** 1.8 * peak
            v = int(255 * a)
            px[i, j] = (v, v, v)
    return img


def add_paste(base, dot, x, y, tint):
    bw, bh = base.size
    dw, dh = dot.size
    ox, oy = int(x - dw/2), int(y - dh/2)
    bp, dp = base.load(), dot.load()
    for j in range(dh):
        yy = oy + j
        if yy < 0 or yy >= bh:
            continue
        for i in range(dw):
            xx = ox + i
            if xx < 0 or xx >= bw:
                continue
            r, g, b = dp[i, j]
            if r == 0:
                continue
            br, bg, bb = bp[xx, yy]
            bp[xx, yy] = (
                min(255, br + int(r * tint[0])),
                min(255, bg + int(g * tint[1])),
                min(255, bb + int(b * tint[2])),
            )


def main():
    mask = build_silhouette()
    mp = mask.load()
    canvas = Image.new("RGB", (W, H), (0, 0, 0))

    # soft luminous body aura UNDER the dots — gives the figure volume so it reads as a
    # glowing body over a lit scene (not invisible sparse dots). Low peak = no fog.
    aura_a = mask.filter(ImageFilter.GaussianBlur(11)).point(lambda v: int(v * 0.40))
    aura_rgb = Image.merge("RGB", [
        aura_a.point(lambda v: int(v * 0.50)),   # R (cool)
        aura_a.point(lambda v: int(v * 0.80)),   # G
        aura_a.point(lambda v: int(v * 0.92)),   # B → 青瓷月白
    ])
    canvas = ImageChops.add(canvas, aura_rgb)

    # neutral cool-white dots; code tints warmer near the viewer.
    # a faint warm bias at the chest core so a "金核" survives even before tinting.
    cool = (0.62, 0.90, 1.00)   # 青瓷月白
    warm = (1.00, 0.92, 0.66)   # 鎏金 core
    dots = [make_dot(r, 1.0) for r in (1.6, 2.1, 2.7, 3.2)]

    # body fill: ~2400 dots, density follows the silhouette mask & core field
    placed = 0
    tries = 0
    while placed < 2800 and tries < 80000:
        tries += 1
        x = rng.f() * W
        y = rng.f() * H
        mv = mp[int(x), int(y)] / 255.0
        if mv < 0.25:
            continue
        cf = core_field(x, y)
        if rng.f() > mv * (0.45 + 0.55 * cf):
            continue
        dot = dots[min(3, int(rng.f() * 4))]
        # warm core blends toward chest, cool toward edges/hem
        warmth = max(0.0, cf - 0.45) * 1.3
        tint = tuple(cool[k] + (warm[k] - cool[k]) * min(1.0, warmth) for k in range(3))
        bright = 0.72 + 0.55 * cf
        add_paste(canvas, dot, x, y, tuple(t * bright for t in tint))
        # ~9% get an ultra-bright pinpoint = 晶莹 jewel sparkle
        if rng.f() < 0.09:
            add_paste(canvas, dots[0], x, y, tuple(min(1.4, t * 1.5) for t in tint))
        placed += 1

    # 流光尾迹: sparse trailing sparks drifting down/out from the hem
    for _ in range(260):
        x = W * 0.5 + (rng.f() - 0.5) * W * 0.62
        y = H * (0.82 + rng.f() * 0.20)
        if rng.f() > 0.6:
            continue
        dot = dots[min(2, int(rng.f() * 3))]
        b = 0.18 + 0.30 * rng.f()
        add_paste(canvas, dot, x, y, tuple(c * b for c in cool))

    # build alpha from luminance so edges stay clean over the camera feed
    lum = canvas.convert("L")
    out = canvas.convert("RGBA")
    out.putalpha(lum)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT)
    print("wrote", OUT, "placed", placed)


if __name__ == "__main__":
    main()
