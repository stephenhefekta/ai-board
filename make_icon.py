#!/usr/bin/env python3
"""Generate AI Board.icns — 4 model dots on a dark rounded background."""

import subprocess
import shutil
from pathlib import Path
from PIL import Image, ImageDraw


# One dot per model: Claude, ChatGPT, Gemini, Grok
COLORS = ["#D97706", "#059669", "#2563EB", "#7C3AED"]
BG = "#0f172a"  # dark slate


def make_frame(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded background
    radius = size // 5
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=BG)

    # 2×2 grid of circles
    pad = size * 0.16
    gap = size * 0.08
    cell = (size - 2 * pad - gap) / 2
    cr = cell * 0.42

    positions = [
        (pad,          pad),
        (pad + cell + gap, pad),
        (pad,          pad + cell + gap),
        (pad + cell + gap, pad + cell + gap),
    ]

    for (x, y), color in zip(positions, COLORS):
        cx = x + cell / 2
        cy = y + cell / 2
        draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=color)

    return img


def main():
    iconset = Path("AI Board.iconset")
    iconset.mkdir(exist_ok=True)

    for base, scale in [
        (16, 1), (16, 2),
        (32, 1), (32, 2),
        (128, 1), (128, 2),
        (256, 1), (256, 2),
        (512, 1), (512, 2),
    ]:
        img = make_frame(base * scale)
        suffix = f"@{scale}x" if scale > 1 else ""
        img.save(iconset / f"icon_{base}x{base}{suffix}.png")

    subprocess.run(["iconutil", "-c", "icns", str(iconset)], check=True)
    shutil.rmtree(iconset)
    print("✓ Created AI Board.icns")


if __name__ == "__main__":
    main()
