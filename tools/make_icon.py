from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 512
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def build() -> Image.Image:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    center, radius = SIZE / 2, SIZE * 0.47
    hexagon = [(center + radius * math.cos(math.radians(60 * i + 30)), center + radius * math.sin(math.radians(60 * i + 30))) for i in range(6)]
    draw.polygon(hexagon, fill=(52, 40, 110), outline=(214, 175, 70))
    draw.line([*hexagon, hexagon[0]], fill=(214, 175, 70), width=SIZE // 36, joint="curve")
    font = ImageFont.load_default(size=int(SIZE * 0.42))
    draw.text((center, center), "20", fill=(255, 255, 255), font=font, anchor="mm")
    return image


def main(out: str) -> None:
    build().save(out, format="ICO", sizes=SIZES)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1] / "packaging" / "icon.ico"))
