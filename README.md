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

## CLI 输出与退出码（当前实现）
- `--verbose / --quiet`: 尚未实现；当前总是输出一行摘要（stdout），包含保存路径、最终大小 KB、尺寸、格式与质量。
- 输出摘要格式：`Saved <path> | <KB> KB | <WxH> | format=<fmt> | quality=<q>`。警告（如无法达到目标体积）打印到 stderr。
- 退出码：成功为 0；当已尝试到 `--min-quality` 与 `--min-side` 仍超出目标时，保存最佳结果并返回 1；参数错误由 argparse 返回 2；其他异常按 Python 默认非 0 退出。

## How it works
1) Optionally downsizes to fit the max width/height.  
2) Tries saving at decreasing quality until the target size is hit.  
3) If quality bottoms out, gently rescales using `resize-step` until the target or `min-side` is reached.

## 压缩策略与场景梳理
- 质量搜索：起始质量默认为 90，每轮减 5 直到 `--min-quality`（默认 40）或迭代 60 次；只要出现更小的结果就记录为最佳，不做二分搜索。
- 尺寸递减：当质量已到底仍超标时，按 `resize-step`（默认 0.9）等比缩放，最短边不低于 `--min-side`；使用 `LANCZOS` 插值，若缩放后尺寸未变则提前停止。
- 格式与透明：默认 JPEG，只有源图为 `RGBA` 才默认切到 WebP；保存 JPEG/WebP 时统一调用 `flatten_transparency`，因此即便选择 WebP 也会用 `--bg-color` 铺底、丢失透明度。调色板图 (`P`) 在保存 JPEG/WebP 时会被转成 RGB，未保留调色板。
- 超大图：在主循环前先按 `--max-width/--max-height` 收敛到边界，之后再进行质量/尺寸递减。
- 可复现场景：
  - 透明 PNG：`python compress.py transparent.png --target-kb 80` → 默认输出 WebP 但透明被铺成 `--bg-color`；用于验证透明丢失的缺口。
  - 调色板图标：`python compress.py palette.png --target-kb 30 --format jpeg` → 颜色被转为 RGB，无额外量化，文件体积与色彩保真需人工确认。
  - 超大原图：`python compress.py huge.jpg --target-kb 200 --max-width 2000` → 先按 max 边缩，再逐步降质/降尺寸；可观察最短边受 `--min-side` 保护。
  - 强制 PNG：`python compress.py icon.png --target-kb 80 --format png` → 可能无法触达目标，预期输出警告并以 1 退出。
- 已知缺口（对齐“提升压缩效果与鲁棒性”）：未保留透明 WebP（需条件分支跳过铺底）；未对调色板/插画做自适应量化；质量搜索步长固定、未做二分；未检测 Pillow 的 WebP 编解码能力并降级。

## Tips for tiny files that stay clear
- Prefer `--format webp` for photographic or text-heavy banners.
- Set a realistic target: most 1920px-wide banners look good between 60-120 KB as WebP.
- Avoid shrinking below `--min-side` unless absolutely necessary to preserve readability.

## Example result from this repo
- `banner.png` (1.6 MB, 2540x965) -> `banner_compressed.webp` (~61 KB，2540x965) using `python compress.py banner.png --target-kb 80 --format webp`.

## 手动回归清单（最小覆盖）
- 横幅照片（repo 内 banner）：`python compress.py banner.png --target-kb 80` → 期望 60-90 KB，保持 2540x965，退出码 0。
- 透明 UI：`python compress.py transparent.png --target-kb 60 --format webp` → 目前会铺底（缺口记录），输出提示行 + 退出码 0；用于回归透明行为。
- 插画/文字：`python compress.py poster.png --target-kb 100 --min-quality 60` → 期望质量不低于 60、尺寸不低于 `--min-side`，退出码 0。
- 超大原图：`python compress.py huge.jpg --target-kb 200 --max-width 2000` → 期望先缩到 <=2000 宽，再压到 <200 KB 或返回 1（不可达时仍保存最佳）。
- 强制 PNG：`python compress.py icon.png --target-kb 80 --format png` → 若无法达到目标会警告并返回 1；用于提醒 PNG 无损体积限制。

## 批量处理分层草案
- 单图（已实现）：输入文件 → `<stem>_compressed.<ext>`，显式 `-o` 优先；不覆盖原文件。
- 多图/目录（计划）：支持传递目录或通配符，输出默认跟随源目录结构并追加 `_compressed` 后缀；如目标文件已存在可选择跳过/覆盖/写入新后缀（待定）。
- 预设/配置（计划）：允许通过配置文件或命令组复用参数（目标 KB、格式、最短边等），并可在批量模式下逐文件覆盖；命名策略仍以 `_compressed` 为默认，`-o`/配置目录覆盖优先。
- 覆盖策略草案：保持“显式优先”原则（命令行 > 配置 > 默认），批量模式默认不覆盖已存在输出，提供 `--overwrite` 或版本化后缀作为选项。

## 工程化发布准备（草案）
- 关键步骤：定义发布形态（单脚本 or 包）、添加版本号与 changelog 流程、引入基础 CI（lint + 示例命令跑通）、验证 Pillow/WebP 兼容性并给出 fallback、打包/分发指引。
- 今日推进：记录 Pillow/WebP 兼容检查思路——运行时使用 `PIL.features.check("webp")` 探测，缺失时提示并自动退回 JPEG；同时在 README 要求安装 Pillow（当前环境未安装）。
