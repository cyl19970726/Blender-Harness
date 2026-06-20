#!/usr/bin/env python3
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image


OUT_DIR = Path("/Users/hhh0x/ai-luodi/jieyanggucheng-spot/public/ar/spots/jinxianmen/fx")
AMBER = (0xFF, 0xCF, 0x7A)
MOON = (0xFF, 0xF6, 0xE0)
SKY_TOP = (0x0B, 0x1F, 0x4A)
SKY_BOTTOM = (0x3A, 0x2A, 0x44)


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge0 == edge1:
        return 1.0 if x >= edge1 else 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def mix(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def make_glow(size: tuple[int, int], radius_x: float, radius_y: float, peak_alpha: float) -> Image.Image:
    width, height = size
    cx = (width - 1) / 2.0
    cy = (height - 1) / 2.0
    pixels: list[tuple[int, int, int, int]] = []

    for y in range(height):
        ny = (y - cy) / radius_y
        for x in range(width):
            nx = (x - cx) / radius_x
            r = math.sqrt(nx * nx + ny * ny)
            if r >= 1.0:
                alpha = 0.0
            else:
                # Gaussian-like falloff, normalized to hit exactly peak_alpha at center.
                alpha = peak_alpha * math.exp(-4.2 * r * r) * (1.0 - smoothstep(0.82, 1.0, r))
            pixels.append((*AMBER, round(255 * alpha)))

    image = Image.new("RGBA", size)
    image.putdata(pixels)
    return image


def make_moon(size: tuple[int, int] = (512, 512)) -> Image.Image:
    width, height = size
    cx = (width - 1) / 2.0
    cy = (height - 1) / 2.0
    disk_radius = 0.34 * min(width, height)
    halo_radius = 0.50 * min(width, height)
    pixels: list[tuple[int, int, int, int]] = []

    for y in range(height):
        for x in range(width):
            dx = x - cx
            dy = y - cy
            r = math.sqrt(dx * dx + dy * dy)

            disk = 1.0 - smoothstep(disk_radius * 0.78, disk_radius, r)
            halo = 1.0 - smoothstep(disk_radius * 0.92, halo_radius, r)
            alpha = min(0.90, 0.90 * disk + 0.22 * halo * (1.0 - disk))

            # Keep the disk warm-white, with a subtle gold tint only in the feathered halo.
            halo_t = max(0.0, min(1.0, (r - disk_radius * 0.72) / (halo_radius - disk_radius * 0.72)))
            red = mix(MOON[0], AMBER[0], 0.16 * halo_t)
            green = mix(MOON[1], AMBER[1], 0.16 * halo_t)
            blue = mix(MOON[2], AMBER[2], 0.16 * halo_t)
            pixels.append((red, green, blue, round(255 * alpha)))

    image = Image.new("RGBA", size)
    image.putdata(pixels)
    return image


def make_night_sky(size: tuple[int, int] = (1024, 512), seed: int = 20260617) -> Image.Image:
    width, height = size
    rng = random.Random(seed)
    pixels: list[tuple[int, int, int, int]] = []
    fade_start = height * (2.0 / 3.0)

    for y in range(height):
        t = y / (height - 1)
        red = mix(SKY_TOP[0], SKY_BOTTOM[0], t)
        green = mix(SKY_TOP[1], SKY_BOTTOM[1], t)
        blue = mix(SKY_TOP[2], SKY_BOTTOM[2], t)
        alpha = 1.0 - smoothstep(fade_start, height - 1, y)
        a = round(255 * alpha)
        for _ in range(width):
            pixels.append((red, green, blue, a))

    image = Image.new("RGBA", size)
    image.putdata(pixels)

    # Low-alpha star points live only in the upper two thirds and stay subtle.
    data = image.load()
    for _ in range(74):
        x = rng.randrange(0, width)
        y = rng.randrange(8, int(height * 0.66))
        star_alpha = rng.randrange(28, 78)
        radius = 1 if rng.random() < 0.88 else 2
        for yy in range(y - radius, y + radius + 1):
            for xx in range(x - radius, x + radius + 1):
                if 0 <= xx < width and 0 <= yy < height:
                    d = math.sqrt((xx - x) ** 2 + (yy - y) ** 2)
                    if d <= radius:
                        base = data[xx, yy]
                        weight = max(0.0, 1.0 - d / (radius + 0.35))
                        a = min(255, base[3] + round(star_alpha * weight))
                        data[xx, yy] = (245, 232, 190, a)

    return image


def save_all() -> dict[str, Image.Image]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    images = {
        "glow-round.png": make_glow((512, 512), 255.5, 255.5, 0.85),
        "glow-wide.png": make_glow((1024, 384), 511.5, 153.5, 0.85),
        "glow-tall.png": make_glow((384, 768), 153.5, 383.5, 0.85),
        "moon.png": make_moon(),
        "night-sky.png": make_night_sky(),
    }
    for name, image in images.items():
        image.save(OUT_DIR / name)
    return images


def report(images: dict[str, Image.Image]) -> None:
    for name, image in images.items():
        cx = image.width // 2
        cy = image.height // 2
        center = image.getpixel((cx, cy))
        max_alpha = max(pixel[3] for pixel in image.getdata())
        has_pure_white_rgb = any(pixel[:3] == (255, 255, 255) and pixel[3] > 0 for pixel in image.getdata())
        print(
            f"{name}: {image.width}x{image.height}, "
            f"center RGBA={center}, center alpha={center[3] / 255:.3f}, "
            f"max alpha={max_alpha / 255:.3f}, pure-white-rgb={has_pure_white_rgb}"
        )


if __name__ == "__main__":
    report(save_all())
