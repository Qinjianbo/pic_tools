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
- 示例（行为与代码一致）：
  - 成功：`python compress.py banner.png --target-kb 80` → stdout 单行摘要，退出码 0。
  - 不可达目标：`python compress.py icon.png --target-kb 5 --format png` → stderr 警告 + stdout 摘要，退出码 1；仍会保存“最佳努力”输出。

## How it works
1) Optionally downsizes to fit the max width/height.  
2) Tries saving at decreasing quality until the target size is hit.  
3) If quality bottoms out, gently rescales using `resize-step` until the target or `min-side` is reached.

## 压缩策略与场景梳理
- 质量搜索：起始质量默认为 90，每轮减 5 直到 `--min-quality`（默认 40）或迭代 60 次；只要出现更小的结果就记录为最佳，不做二分搜索。
- 尺寸递减：当质量已到底仍超标时，按 `resize-step`（默认 0.9）等比缩放，最短边不低于 `--min-side`；使用 `LANCZOS` 插值，若缩放后尺寸未变则提前停止。
- 当前覆盖案例：
  - 透明 PNG/Alpha：源图为 `RGBA` 时默认切换 WebP；透明会被 `--bg-color` 铺底后再编码。
  - 调色板/插画：`P` 模式保存 JPEG/WebP 时自动转 RGB，无额外量化；PNG 输出保留调色板但只调 `compress_level`。
  - 超大图：先应用 `--max-width/--max-height` 再进入质量→尺寸循环，可与 `min_side` 共同约束尺寸底线。
- 未自动化的缺口（“提升压缩效果与鲁棒性”着力点）：
  - 透明保持：缺少“透明 WebP 保留 alpha”的条件分支及对比实验；未覆盖透明/不透明两路自动测试。
  - 调色板优化：未做自适应量化或 palette 优化，RGB 转换可能放大体积或丢色阶；缺少可重复的质量/体积比对脚本。
  - 极端大图：未做分段降采样或内存保护测试；对 >10k 像素输入的耗时/内存缺乏基准。
  - 搜索策略：质量步长固定 5%；未提供二分或自适应跳步模式；`min_side` 仅单一阈值，无法根据目标 KB 自动收紧。
- 可复现场景（含验证点）：
  - 透明 PNG：`python compress.py transparent.png --target-kb 80` → 预期输出 WebP 且透明被铺成 `--bg-color`；验证透明丢失及警告无。
  - 调色板图标：`python compress.py palette.png --target-kb 30 --format jpeg` → 颜色被转为 RGB；需检查色阶丢失、体积变化。
  - 超大原图：`python compress.py huge.jpg --target-kb 200 --max-width 2000` → 先降到 ≤2000 宽，再逐步降质/降尺寸；验证 `min_side` 保护是否生效。
  - 强制 PNG：`python compress.py icon.png --target-kb 80 --format png` → 若无法达到目标，预期 stderr 警告 + 退出码 1；仍会写出最佳结果。

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
- 单图（已实现）：输入文件 → `<stem>_compressed.<ext>`，显式 `-o` 优先；不覆盖原文件。示例：`python compress.py banner.png --target-kb 80 -o out/banner.webp`。
- 多图/目录（计划）：接受目录或通配符输入（如 `assets/*.png`），输出默认复刻目录结构并追加 `_compressed` 后缀；预期提供 `--output-dir` 统一指定根目录。冲突处理建议：默认跳过已存在输出；可选 `--overwrite` 覆盖或 `--versioned` 追加 `_v2` 等后缀。示例：`python compress.py assets/ --target-kb 90 --output-dir dist/ --overwrite`。
- 预设/配置（计划）：支持传入配置文件（如 `--config preset.yaml`）或命令组复用目标 KB、格式、最短边等参数；命名策略沿用 `_compressed`，但允许配置覆盖；批量模式下命令行优先级最高，其次配置文件，最后默认。示例：`python compress.py list.txt --config presets/web.yml --format webp`。
- 覆盖策略原则：显式优先（命令行 > 配置 > 默认）；批量默认不覆盖，提供跳过/覆盖/版本化三选项，并在冲突时输出决策摘要以便回溯。

## 工程化发布准备（草案）
- 关键步骤：定义发布形态（单脚本 or 包）、添加版本号与 changelog 流程、引入基础 CI（lint + 示例命令跑通）、验证 Pillow/WebP 兼容性并给出 fallback、打包/分发指引。
- 今日可做重点与待验证清单：  
  - WebP 可用性自检：启动时 `PIL.features.check(\"webp\")`，不可用时降级 JPEG 并在摘要中提示；需要小样本验证无 WebP 环境的行为。  
  - CI 验证项：在 CI 跑通 README 的最小回归命令（见“手动回归清单”），至少覆盖横幅、强制 PNG、透明 WebP 铺底三个场景；同时添加 `python -m compileall compress.py` 作为快速语法守护。  
  - 退出码契约：对“不可达目标”确保返回 1 且仍写出文件，CI 中断言 stderr 警告存在。  
  - 依赖声明：确认 `requirements.txt`/文档中列出 Pillow 版本下限；评估是否需要 `python -m pip install pillow[webp]` 的说明。  
  - 发布形态调研：比对“单文件脚本 + release asset” vs “pip 包 + entry point”；记录构建/上传步骤与潜在 CI 配置需求。
