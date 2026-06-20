#!/usr/bin/env python3
"""晶莹流光贤士 — render a figure as fine GOLD LINE-LIGHT (robe folds + 拱手 contour) +
sparse glowing PARTICLES, NOT a photo fill.

The panel bracketed it: a photo-render z-image figure reads either as a solid 塑像/神像
(red-line) or, when made transparent, as 金雾鬼影 (foggy ghost). Neither is "晶莹光粒".
Target (panel FIX1): "成千条细鎏金流光线(线描勾衣纹/拱手)+ 月白冷青粒子(填体积), 内部留空透气
(晶莹=有空隙的光), 半透可见身后真砖; 绝不实体烟雾/motion-blur/块面阴影".

Method: take the generated figure as a SHAPE GUIDE only — extract its interior edges
(robe folds) + silhouette contour → thin bright lines with a faint glow; scatter sparse
glowing dots inside for volume. Output is neutral white-gold on black (additive); code
tints far=青瓷 / near=鎏金. Lines have gaps → see-through without fog.
"""
import math
from pathlib import Path
from PIL import Image, ImageFilter, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
GEN = Path("/tmp/xian_gen")
PORT = ROOT / "public/ar/spots/jinxianmen/portal"


class R:
    def __init__(s, x): s.s = x
    def f(s):
        s.s = (s.s * 1103515245 + 12345) & 0x7fffffff
        return s.s / 0x7fffffff


def make(src: str, out: str, seed: int = 1):
    rng = R(seed)
    im = Image.open(GEN / src).convert("RGB")
    lum = im.convert("L").point(lambda v: 0 if v < 12 else min(255, int((v - 12) * 1.15)))
    bbox = lum.point(lambda v: 255 if v > 16 else 0).getbbox()
    if bbox:
        lum = lum.crop(bbox)
    W, H = lum.size
    mask = lum.point(lambda v: 255 if v > 26 else 0)

    # interior edges = robe folds / 衣纹 (the figure's own gradient lines)
    edges = lum.filter(ImageFilter.GaussianBlur(1)).filter(ImageFilter.FIND_EDGES)
    edges = edges.point(lambda v: min(255, int(v * 3.0)))
    edges = ImageChops.multiply(edges, mask)                      # keep inside silhouette
    # contour line = silhouette boundary, BOLD + bright (main shape reader)
    contour = mask.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(5))
    contour = contour.point(lambda v: 255 if v > 30 else 0)
    lines = ImageChops.add(edges, contour).point(lambda v: min(255, int(v * 1.5)))
    # luminous line-light: tight glow + wider soft halo along the strokes (透气=gaps remain)
    glow1 = lines.filter(ImageFilter.GaussianBlur(4)).point(lambda v: int(v * 0.95))
    glow2 = lines.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.45))
    line_a = ImageChops.add(ImageChops.add(lines, glow1), glow2)

    # neutral warm-white line colour (code tints later)
    canvas = Image.merge("RGB", [
        line_a.point(lambda v: min(255, int(v * 1.0))),
        line_a.point(lambda v: min(255, int(v * 0.97))),
        line_a.point(lambda v: min(255, int(v * 0.86))),
    ])

    # sparse glowing particles filling the body (volume), brightest at the clasped-hands core
    cpx, cpy = W * 0.5, H * 0.45
    def dot(r, peak):
        s = int(r * 2) + 3
        d = Image.new("RGB", (s, s), (0, 0, 0)); p = d.load(); c = (s - 1) / 2
        for j in range(s):
            for i in range(s):
                dd = math.hypot(i - c, j - c) / r
                if dd <= 1:
                    a = (1 - dd) ** 1.7 * peak; v = int(255 * a); p[i, j] = (v, v, v)
        return d
    dots = [dot(r, 1.0) for r in (1.5, 2.1, 2.9)]
    mp = mask.load(); cp = canvas.load()
    placed = 0; tries = 0
    while placed < 760 and tries < 36000:
        tries += 1
        x = rng.f() * W; y = rng.f() * H
        if mp[int(x), int(y)] < 60:
            continue
        cf = max(0.12, 1 - math.hypot((x - cpx) / (W * 0.5), (y - cpy) / (H * 0.55)))
        if rng.f() > 0.4 + 0.55 * cf:
            continue
        d = dots[min(2, int(rng.f() * 3))]; dw = d.size[0]; dp = d.load()
        ox, oy = int(x - dw / 2), int(y - dw / 2)
        b = 0.85 + 0.6 * cf
        for j in range(dw):
            for i in range(dw):
                yy, xx = oy + j, ox + i
                if 0 <= xx < W and 0 <= yy < H:
                    r0, g0, bl = dp[i, j]
                    if r0:
                        br, bg, bb = cp[xx, yy]
                        cp[xx, yy] = (min(255, br + int(r0 * b)), min(255, bg + int(g0 * b * 0.97)), min(255, bb + int(bl * b * 0.82)))
        placed += 1

    # bright clasped-hands core (the 拱手 focal glow)
    core = Image.new("RGB", (W, H), (0, 0, 0)); cd = ImageDraw.Draw(core)
    for rr, a in ((W * 0.14, 70), (W * 0.09, 110), (W * 0.05, 150)):
        cd.ellipse([cpx - rr, cpy - rr * 0.85, cpx + rr, cpy + rr * 0.85], fill=(int(255), int(245), int(205)))
    core = core.filter(ImageFilter.GaussianBlur(6))
    canvas = ImageChops.add(canvas, ImageChops.multiply(core, Image.new("RGB", (W, H), (90, 86, 70))))

    out_img = canvas.convert("RGBA")
    out_img.putalpha(canvas.convert("L"))
    out_img.save(PORT / out)
    print("wrote", out, out_img.size, "particles", placed)


if __name__ == "__main__":
    make("goldbow-31.png", "xian-bow.png", 3)
    make("goldbow-7.png", "xian-bow2.png", 7)
    make("stand-7.png", "xian-stand.png", 11)
    Image.open(PORT / "xian-stand.png").transpose(Image.FLIP_LEFT_RIGHT).save(PORT / "xian-stand2.png")
    make("goldstand-7.png", "xian-stand-gold.png", 5)
    print("done")
