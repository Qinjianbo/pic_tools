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
- `--target-kb` (int, default 90): 目标文件大小上限（KB）。算法会先调质量再调尺寸；若已降到 `--min-quality` 且缩到 `--min-side` 仍大于目标，会保存当前最佳结果、打印警告并以非 0 退出码告知不可达。
- `--format` (`jpeg|jpg|png|webp`): 强制输出格式。默认输出 JPEG；若源图含透明通道则默认改为 WebP 以避免强制铺底色。
- `--max-width` / `--max-height`: Optional bounds; aspect ratio is preserved, never cropped.
- `--quality` / `--min-quality`: Starting and minimum quality for iterative compression。
- `--resize-step` (default 0.9) & `--min-side` (default 320): Gradually shrink dimensions only if quality tweaks cannot meet the target。
- `--bg-color` (default `white`): 背景色仅在保存 JPEG/WebP 时用于铺平透明区域；对 PNG 无效。接受 hex (`#fff`, `#ffffff`) 或名称 (`white`, `black`, `gray`, `red`)。

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

## 手动回归清单（常见场景与期望）
- 横幅照型：`python compress.py banner.png --target-kb 80`，预期 ~70-90 KB，格式 JPEG/WebP 按透明度自动挑选。
- 透明 UI 素材：`python compress.py ui.png --target-kb 60 --format webp`，预期保留透明且 ~50-70 KB。
- 插画/文字锐利度：`python compress.py poster.png --target-kb 100 --min-quality 60`，预期不糊字，尺寸不低于 `--min-side`。
- 超大原图：`python compress.py huge.jpg --target-kb 200 --max-width 2000`，预期先按 max 宽限缩，再压到 <200 KB。
- 强制 PNG：`python compress.py icon.png --target-kb 80 --format png`，预期尺寸可能远大于目标；若不可达会提示并返回非 0。

## 批量处理规划笔记
短期聚焦单图稳定与对外契约；后续再扩展多文件/目录入口时，需要先定清输出命名与覆盖策略（如 `_compressed` 后缀或显式 `-o` 优先），避免批量模式破坏现有单图默认行为。
