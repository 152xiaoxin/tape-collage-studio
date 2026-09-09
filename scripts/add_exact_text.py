#!/usr/bin/env python3
"""Add exact Chinese-friendly text to an existing raster image."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont


POSITIONS = (
    "upper-left",
    "upper-center",
    "upper-right",
    "center",
    "lower-left",
    "lower-center",
    "lower-right",
)


def unit_fraction(value: str) -> float:
    number = float(value)
    if not 0 <= number <= 1:
        raise argparse.ArgumentTypeError("数值必须在 0 到 1 之间")
    return number


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="在图片上确定性叠加精确中文或英文文字。")
    parser.add_argument("--image", type=Path, required=True, help="输入图片")
    parser.add_argument("--output", type=Path, required=True, help="输出 PNG")
    parser.add_argument("--text", required=True, help=r"精确文字；用 \n 显式换行")
    parser.add_argument("--font", type=Path, help="自定义 TTF/OTF/TTC 字体")
    parser.add_argument(
        "--position", choices=POSITIONS, default="lower-left", help="预设位置"
    )
    parser.add_argument("--x", type=unit_fraction, help="自定义左上角 x 比例")
    parser.add_argument("--y", type=unit_fraction, help="自定义左上角 y 比例")
    parser.add_argument(
        "--size-ratio",
        type=unit_fraction,
        default=0.045,
        help="字号占画布短边比例，默认 0.045",
    )
    parser.add_argument(
        "--margin-ratio",
        type=unit_fraction,
        default=0.08,
        help="安全边距占画布短边比例，默认 0.08",
    )
    parser.add_argument("--color", default="#514b45", help="文字颜色")
    parser.add_argument(
        "--line-spacing",
        type=float,
        default=0.30,
        help="行距占字号比例，默认 0.30",
    )
    parser.add_argument(
        "--stroke-width",
        type=int,
        default=0,
        help="可选描边像素；胶带拼贴默认 0",
    )
    parser.add_argument("--stroke-color", default="#faf8f3")
    return parser.parse_args()


def load_font(custom: Path | None, size: int) -> ImageFont.FreeTypeFont:
    root = Path(__file__).resolve().parent.parent
    candidates = [
        custom,
        root / "assets/fonts/ZCOOLXiaoWei-Regular.ttf",
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    raise FileNotFoundError("未找到可用字体；请通过 --font 指定中文 TTF/OTF/TTC 字体")


def choose_position(
    preset: str,
    canvas: tuple[int, int],
    text_box: tuple[int, int],
    margin: int,
) -> tuple[int, int]:
    width, height = canvas
    text_width, text_height = text_box
    horizontal = "center"
    if preset.endswith("left"):
        horizontal = "left"
    elif preset.endswith("right"):
        horizontal = "right"
    vertical = "center"
    if preset.startswith("upper"):
        vertical = "upper"
    elif preset.startswith("lower"):
        vertical = "lower"

    if horizontal == "left":
        x = margin
    elif horizontal == "right":
        x = width - margin - text_width
    else:
        x = (width - text_width) // 2

    if vertical == "upper":
        y = margin
    elif vertical == "lower":
        y = height - margin - text_height
    else:
        y = (height - text_height) // 2
    return x, y


def main() -> None:
    args = parse_args()
    image = Image.open(args.image).convert("RGBA")
    width, height = image.size
    short_edge = min(width, height)
    font_size = max(10, round(short_edge * args.size_ratio))
    margin = max(4, round(short_edge * args.margin_ratio))
    spacing = max(0, round(font_size * args.line_spacing))
    font = load_font(args.font, font_size)
    text = args.text.replace(r"\n", "\n")

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    bbox = draw.multiline_textbbox(
        (0, 0),
        text,
        font=font,
        spacing=spacing,
        align="left",
        stroke_width=args.stroke_width,
    )
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    if text_width > width - 2 * margin or text_height > height - 2 * margin:
        raise ValueError("文字超出安全区；请减小 --size-ratio 或手动换行")

    if (args.x is None) != (args.y is None):
        raise ValueError("--x 与 --y 必须同时提供")
    if args.x is not None and args.y is not None:
        x = round(width * args.x)
        y = round(height * args.y)
    else:
        x, y = choose_position(
            args.position, image.size, (text_width, text_height), margin
        )
    x = min(max(margin, x), width - margin - text_width)
    y = min(max(margin, y), height - margin - text_height)

    draw.multiline_text(
        (x - bbox[0], y - bbox[1]),
        text,
        font=font,
        fill=ImageColor.getrgb(args.color) + (255,),
        spacing=spacing,
        align="left",
        stroke_width=args.stroke_width,
        stroke_fill=ImageColor.getrgb(args.stroke_color) + (255,),
    )
    output = Image.alpha_composite(image, overlay)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.save(args.output, format="PNG", optimize=True)
    print(f"OUTPUT={args.output}")
    print(f"TEXT={args.text!r}")
    print(f"FONT={getattr(font, 'path', 'unknown')}")
    print(f"FONT_SIZE={font_size}")
    print(f"TEXT_BOX={(x, y, x + text_width, y + text_height)}")


if __name__ == "__main__":
    main()
