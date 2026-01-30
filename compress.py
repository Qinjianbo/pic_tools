#!/usr/bin/env python3
"""
Simple CLI to compress images to a target file size without cropping.

Usage examples:
  python compress.py banner.png --target-kb 80
  python compress.py banner.png -o banner.webp --target-kb 60 --format webp
  python compress.py banner.png --max-width 1600 --target-kb 100
"""

import argparse
import io
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image


def parse_color(value: str) -> Tuple[int, int, int]:
    """Convert common color strings into an RGB tuple."""
    value = value.strip().lower()
    if value.startswith("#"):
        value = value.lstrip("#")
        if len(value) == 3:
            value = "".join(ch * 2 for ch in value)
        if len(value) != 6:
            raise argparse.ArgumentTypeError("Hex color must be 3 or 6 characters.")
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))
    named = {
        "white": (255, 255, 255),
        "black": (0, 0, 0),
        "gray": (245, 245, 245),
        "red": (255, 0, 0),
    }
    if value in named:
        return named[value]
    raise argparse.ArgumentTypeError(f"Unsupported color '{value}'. Use hex or a basic name.")


def flatten_transparency(img: Image.Image, bg_color: Tuple[int, int, int]) -> Image.Image:
    """Remove alpha channel so JPEG/WebP saves cleanly."""
    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, bg_color)
        background.paste(img, mask=img.split()[-1])
        return background
    if img.mode == "P":
        return img.convert("RGB")
    return img


def downscale_to_bounds(img: Image.Image, max_w: Optional[int], max_h: Optional[int]) -> Image.Image:
    """Resize to fit within max width/height while keeping aspect ratio."""
    if not max_w and not max_h:
        return img
    w, h = img.size
    max_w = max_w or w
    max_h = max_h or h
    scale = min(max_w / w, max_h / h, 1.0)
    if scale == 1.0:
        return img
    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    return img.resize(new_size, Image.LANCZOS)


def encode(img: Image.Image, fmt: str, quality: int, bg_color: Tuple[int, int, int]) -> bytes:
    """Save image into bytes using the requested format and quality."""
    fmt = fmt.upper()
    work_img = flatten_transparency(img, bg_color) if fmt in ("JPEG", "WEBP") else img

    buffer = io.BytesIO()
    save_kwargs = {}
    if fmt in ("JPEG", "WEBP"):
        save_kwargs["quality"] = quality
        save_kwargs["optimize"] = True
    if fmt == "WEBP":
        save_kwargs.setdefault("method", 6)
    if fmt == "PNG":
        save_kwargs["compress_level"] = 9
    work_img.save(buffer, format=fmt, **save_kwargs)
    return buffer.getvalue()


def compress_image(
    input_path: Path,
    output_path: Optional[Path],
    target_kb: int,
    max_width: Optional[int],
    max_height: Optional[int],
    fmt: Optional[str],
    start_quality: int,
    min_quality: int,
    resize_step: float,
    min_side: int,
    bg_color: Tuple[int, int, int],
) -> Tuple[Path, int, Tuple[int, int], str, int]:
    """Iteratively reduce quality and, if needed, dimensions to reach target size."""
    img = Image.open(input_path)
    fmt = (fmt or ("JPEG" if img.mode != "RGBA" else "WEBP")).upper()
    working = downscale_to_bounds(img, max_width, max_height)

    quality = start_quality
    best_blob = None
    best_size = None
    best_quality = quality
    best_dims = working.size

    for _ in range(60):
        blob = encode(working, fmt, quality, bg_color)
        size_kb = int(len(blob) / 1024)

        if best_blob is None or size_kb <= target_kb or size_kb < best_size:
            best_blob = blob
            best_size = size_kb
            best_quality = quality
            best_dims = working.size

        if size_kb <= target_kb:
            break

        if quality > min_quality:
            quality = max(min_quality, quality - 5)
            continue

        new_w = max(min_side, int(working.width * resize_step))
        new_h = max(min_side, int(working.height * resize_step))
        if (new_w, new_h) == working.size:
            break
        working = working.resize((new_w, new_h), Image.LANCZOS)

    if output_path is None:
        suffix = fmt.lower()
        output_path = input_path.with_stem(input_path.stem + "_compressed").with_suffix(f".{suffix}")

    output_path.write_bytes(best_blob)
    return output_path, best_size, best_dims, fmt, best_quality


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compress an image to a target size (KB) while keeping aspect ratio."
    )
    parser.add_argument("input", type=Path, help="Input image path.")
    parser.add_argument("-o", "--output", type=Path, help="Output path. Defaults to *_compressed.<ext>.")
    parser.add_argument("--target-kb", type=int, default=90, help="Desired max size in KB. Default: 90.")
    parser.add_argument(
        "--format",
        choices=["jpeg", "jpg", "png", "webp"],
        help="Force output format. Defaults to JPEG unless source has alpha, then WEBP.",
    )
    parser.add_argument("--max-width", type=int, help="Optional max width. Keeps aspect ratio.")
    parser.add_argument("--max-height", type=int, help="Optional max height. Keeps aspect ratio.")
    parser.add_argument("--quality", type=int, default=90, help="Starting quality (1-100). Default: 90.")
    parser.add_argument("--min-quality", type=int, default=40, help="Lowest quality to try. Default: 40.")
    parser.add_argument(
        "--resize-step",
        type=float,
        default=0.9,
        help="Scale factor applied when quality alone cannot reach target. Default: 0.9.",
    )
    parser.add_argument(
        "--min-side",
        type=int,
        default=320,
        help="Do not shrink below this shorter side length. Default: 320 px.",
    )
    parser.add_argument(
        "--bg-color",
        type=parse_color,
        default="white",
        help="Background color for flattening transparency. Accepts hex (#fff) or names (white, black, gray, red).",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output_path, size_kb, dims, fmt, quality = compress_image(
        input_path=args.input,
        output_path=args.output,
        target_kb=args.target_kb,
        max_width=args.max_width,
        max_height=args.max_height,
        fmt=args.format,
        start_quality=args.quality,
        min_quality=args.min_quality,
        resize_step=args.resize_step,
        min_side=args.min_side,
        bg_color=args.bg_color,
    )
    print(
        f"Saved {output_path} | {size_kb} KB | {dims[0]}x{dims[1]} | format={fmt} | quality={quality}"
    )


if __name__ == "__main__":
    main()
