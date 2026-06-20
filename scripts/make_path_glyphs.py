#!/usr/bin/env python3
"""贤路拓字 — 鎏金 seal-glow glyphs that light up on the real 甬道 brick under the
worthies' footsteps (灵感A: 贤路即正在书写的科举金榜).

Each glyph is a single virtue character in glowing gold on transparent, additive-ready.
Path lights 「礼·文·才·贤」 sequentially as the procession advances; at the climax they
rush up the real 券门 to the 匾额. Culture grows from the action, not a slapped-on caption.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "public/ar/spots/jinxianmen/portal"
FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
CHARS = ["礼", "文", "才", "贤"]
S = 256
GOLD = (0xFF, 0xD8, 0x82)
GOLD_HI = (0xFF, 0xF3, 0xC8)


def render(ch: str, idx: int):
    # solid mask of the glyph
    mask = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(mask)
    font = ImageFont.truetype(FONT, int(S * 0.82))
    bb = d.textbbox((0, 0), ch, font=font)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((S - w) / 2 - bb[0], (S - h) / 2 - bb[1]), ch, font=font, fill=255)

    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # outer glow: blurred gold halo (a few passes for a soft bloom)
    for blur, alpha, col in ((18, 90, GOLD), (9, 130, GOLD), (4, 200, GOLD_HI)):
        halo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        gm = mask.filter(ImageFilter.GaussianBlur(blur))
        halo.putalpha(gm.point(lambda v: int(v * alpha / 255)))
        solid = Image.new("RGBA", (S, S), col + (0,))
        solid.putalpha(halo.getchannel("A"))
        canvas = Image.alpha_composite(canvas, solid)
    # crisp gold core stroke
    core = Image.new("RGBA", (S, S), GOLD_HI + (0,))
    core.putalpha(mask)
    canvas = Image.alpha_composite(canvas, core)

    p = OUT / f"glyph-{idx}.png"
    canvas.save(p)
    print("wrote", p)


if __name__ == "__main__":
    for i, c in enumerate(CHARS):
        render(c, i)
