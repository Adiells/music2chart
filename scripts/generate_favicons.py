#!/usr/bin/env python3
"""Generate multi-resolution favicons and app icons for music2chart."""

from pathlib import Path

from PIL import Image, ImageDraw

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "public"


def render_master(dim: int = 1024) -> Image.Image:
    """Render high-resolution master icon."""
    img = Image.new("RGB", (dim, dim), (20, 22, 27))  # #14161B
    draw = ImageDraw.Draw(img)

    # Chassis border
    border_w = max(1, int(dim * (1.0 / 48.0)))
    draw.rectangle([0, 0, dim - 1, dim - 1], outline=(42, 46, 57), width=border_w)

    colors = [
        (0, 230, 118),  # Green #00E676
        (255, 23, 68),  # Red #FF1744
        (255, 234, 0),  # Yellow #FFEA00
        (41, 121, 255),  # Blue #2979FF
        (255, 145, 0),  # Orange #FF9100
    ]

    factor = dim / 48.0
    bar_w = 4.0 * factor
    bar_h = 24.0 * factor
    top_y = 12.0 * factor
    bottom_y = top_y + bar_h
    corner_r = int(2.0 * factor)

    for i, col in enumerate(colors):
        left_x = (6.0 + i * 8.0) * factor
        right_x = left_x + bar_w
        draw.rounded_rectangle(
            [left_x, top_y, right_x, bottom_y],
            radius=max(1, corner_r),
            fill=col,
        )
    return img


def main() -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    master = render_master(1024)

    # 1. Standard PNG sizes for Google Search, desktop browsers, Android, and PWAs
    sizes = {
        "favicon-48x48.png": 48,
        "favicon-96x96.png": 96,
        "apple-touch-icon.png": 180,
        "favicon-192x192.png": 192,
        "favicon-512x512.png": 512,
    }

    for filename, sz in sizes.items():
        out_path = PUBLIC_DIR / filename
        icon = master.resize((sz, sz), Image.Resampling.LANCZOS)
        icon.save(out_path, format="PNG", optimize=True)
        print(f"Generated {out_path} ({sz}x{sz})")

    # 2. Multi-resolution favicon.ico containing 16x16, 32x32, and 48x48
    ico_path = PUBLIC_DIR / "favicon.ico"
    master_48 = master.resize((48, 48), Image.Resampling.LANCZOS)
    master_48.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    print(f"Generated {ico_path} (multi-res 16, 32, 48)")


if __name__ == "__main__":
    main()
