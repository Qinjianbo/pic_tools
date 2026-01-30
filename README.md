# Image Compressor CLI

Tiny Python script to shrink images to a target file size (in KB) without cropping while keeping them as sharp as possible. Works well for banners like `banner.png` (1.6 MB -> ~70-80 KB as WebP with default settings).

## Requirements
- Python 3.8+
- Pillow: `pip install pillow`

## Quick start
```bash
# Compress to ~80 KB, keep size, choose best format automatically
python compress.py banner.png --target-kb 80

# Force WebP (usually smallest) and custom output path
python compress.py banner.png --target-kb 60 --format webp -o banner_compressed.webp

# Cap dimensions while keeping aspect ratio
python compress.py banner.png --target-kb 90 --max-width 1600
```

The tool creates `<name>_compressed.<ext>` when `-o/--output` is not provided.

## Key options
- `--target-kb` (int, default 90): Desired maximum size in KB.
- `--format` (`jpeg|jpg|png|webp`): Override output format. Defaults to JPEG unless the source has alpha, then WebP.
- `--max-width` / `--max-height`: Optional bounds; aspect ratio is preserved, never cropped.
- `--quality` / `--min-quality`: Starting and minimum quality for iterative compression.
- `--resize-step` (default 0.9) & `--min-side` (default 320): Gradually shrink dimensions only if quality tweaks cannot meet the target.
- `--bg-color` (default `white`): Background color for flattening transparency when saving JPEG/WebP. Accepts hex (`#fff`, `#ffffff`) or names (`white`, `black`, `gray`, `red`).

## How it works
1) Optionally downsizes to fit the max width/height.  
2) Tries saving at decreasing quality until the target size is hit.  
3) If quality bottoms out, gently rescales using `resize-step` until the target or `min-side` is reached.

## Tips for tiny files that stay clear
- Prefer `--format webp` for photographic or text-heavy banners.
- Set a realistic target: most 1920px-wide banners look good between 60-120 KB as WebP.
- Avoid shrinking below `--min-side` unless absolutely necessary to preserve readability.

## Example result from this repo
`banner.png` (1.6 MB) -> `banner_compressed.webp` (~77 KB) using `python compress.py banner.png --target-kb 80 --format webp`.
