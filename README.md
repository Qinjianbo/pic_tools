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
- 核心阈值：起始质量 90，每轮递减 5 直至 `--min-quality`（默认 40）或 60 轮；若仍超标再按 `resize-step`=0.9 等比缩放，短边不低于 `--min-side`（默认 320）。`--max-width/--max-height` 在循环前就先行裁到上限。
- 透明 PNG / Alpha：源为 `RGBA` 时默认改存 WebP；保存 JPEG/WebP 会先按 `--bg-color` 铺底，当前会丢失 Alpha。若强制 `--format png`，只受 `compress_level=9` 影响，质量参数和尺寸搜索不会生效。
- 调色板 / P 模式：输出 JPEG/WebP 前会自动 `convert('RGB')`，调色板被展开，体积可能放大；PNG 路径保留 palette，但仅能调压缩级别，无法通过质量迭代获得更小体积。
- 超大图：先套用 `max-width/height`，再跑质量→尺寸循环；当尺寸约束已把体积压到目标附近时（如 5200x3200 → 2000x1230，质量保持 90，~70 KB），后续循环不会降质，保证清晰度但需留意是否过早停在高质量。
- 搜索/缩放的风险与监控（支撑“提升压缩效果与鲁棒性”）：
  - 透明：需要验证“保留 alpha 的 WebP”分支 vs 现有铺底方案；当用户强制 PNG 且不可达目标时，应提前提示“PNG 无损，质量/尺寸参数无法生效”。
  - 调色板：可选 palette 量化或 lossless WebP 的实验；记录 palette→RGB 后的体积增幅与色块失真，必要时提供 `--quantize` 或“保持 palette”开关。
  - 超大图：在极低 `--target-kb` 下，5% 质量步长 + 0.9 尺寸步长是否收敛过慢；建议加入耗时日志、`--max-iter` 或根据目标 KB 自动收紧 `min_side` 的试验。
  - 搜索策略：评估二分/自适应步长对收敛速度与最终观感的影响，保持默认步长稳定但记录可调参数用于后续 A/B。

### 触发阈值与提示表（透明 / 调色板 / 超大图）
| 场景 (Scenario) | 默认/强制格式与透明处理 | 质量搜索 → 尺寸递减的触发点 | 提示与退出码 |
| --- | --- | --- | --- |
| 透明 PNG（RGBA/LA） | 默认自动改存 WEBP；保存 JPEG/WebP 时按 `--bg-color` 铺底，当前会丢失 alpha；强制 `--format png` 时保留透明但仅受 `compress_level=9` 影响 | 质量从 `--quality` 开始每次减 5 直到 `--min-quality`（默认 90 → 40）；仍超标则每轮尺寸 × `resize_step`（默认 0.9），短边不低于 `min_side`=320；设置 `max-width/height` 会在循环前一次性缩放 | 达标无额外提示；不可达打印 `Warning: target ...` 并退出码 1；透明被铺底无内建提示（在回归说明中标注风险） |
| 调色板 PNG（P，含/不含透明索引） | 默认走 JPEG（palette 会被展开为 RGB）；强制 `png` 保留 palette/transparency；强制 WebP/JPEG 时 palette → RGB | PNG 路径：质量参数无效，首轮超标后直接进入 0.9 缩放直至 `min_side`；JPEG/WebP 路径按质量阶梯，超标后才缩放 | palette → RGB、透明索引丢失时无额外提示；目标过低时同样以 Warning + 退出码 1 告知不可达 |
| 超大图（任意模式） | 格式按默认/显式；透明规则同上 | 循环前先套 `max-width/height` 约束；若首轮已 ≤ 目标则停在较高质量（常为 90）；若目标极低则质量降到 `min-quality` 后进入 0.9 缩放到 `min_side` | 达不到目标时 Warning + 退出码 1；建议在日志中记录“裁剪前后尺寸/质量”用于诊断（待实现） |

## Tips for tiny files that stay clear
- Prefer `--format webp` for photographic or text-heavy banners.
- Set a realistic target: most 1920px-wide banners look good between 60-120 KB as WebP.
- Avoid shrinking below `--min-side` unless absolutely necessary to preserve readability.

## Example result from this repo
- `banner.png` (1.6 MB, 2540x965) -> `banner_compressed.webp` (~61 KB，2540x965) using `python compress.py banner.png --target-kb 80 --format webp`.

## 手动回归清单（最小覆盖）
> 资产复现：无需下载额外素材，运行以下一次性脚本生成 6 张样例图（需 Pillow 已安装）：
>
> ```bash
> source .venv/bin/activate 2>/dev/null || true
> python - <<'PY'
> from pathlib import Path
> from PIL import Image, ImageDraw
> root = Path('samples'); root.mkdir(exist_ok=True)
> # 透明 UI
> w,h = 1280,720; img = Image.new('RGBA',(w,h),(0,0,0,0)); d=ImageDraw.Draw(img)
> for i in range(0,h,10): d.rectangle([0,i,w,i+10], fill=(30,144,255,int(255*i/h)))
> d.rounded_rectangle([200,150,1080,570],40,(255,255,255,160),(0,0,0,120),4)
> d.text((240,320),'Transparent UI',fill=(0,0,0,200)); img.save(root/'transparent.png')
> # 插画/文字
> w,h = 1500,2000; img = Image.new('RGB',(w,h),(248,244,237)); d=ImageDraw.Draw(img)
> colors=[(239,112,96),(58,134,255),(95,207,128),(255,201,71)]
> for i,c in enumerate(colors):
>     d.rectangle([100,150+i*200,w-100,300+i*200],fill=c)
>     d.text((140,180+i*200),f'Layer {i+1} text',fill=(30,30,30))
> d.text((400,1700),'Poster/Text Stress',fill=(60,60,60)); img.save(root/'poster.png',quality=95)
> # 超大渐变
> w,h=5200,3200; x=Image.linear_gradient('L').resize((w,h)); y=Image.linear_gradient('L').rotate(90,expand=True).resize((w,h))
> Image.merge('RGB',(x,y,x.transpose(Image.FLIP_LEFT_RIGHT))).save(root/'huge.jpg',quality=95)
> # 调色板图标
> img=Image.new('P',(640,640)); palette=[]; colors=[(0,0,0),(255,255,255),(255,99,71),(46,134,222),(106,190,48),(255,209,102),(140,104,255),(30,30,30)]
> [palette.extend(c) for c in colors]; palette += [0,0,0]*(256-len(colors)); img.putpalette(palette)
> d=ImageDraw.Draw(img); d.rectangle([40,40,600,600],fill=3,outline=0,width=6); d.rectangle([120,120,520,520],fill=2,outline=0,width=4); d.text((180,300),'ICON',fill=1)
> img.save(root/'icon.png')
> # 调色板 + 透明索引（P + tRNS）
> img=Image.new('P',(640,640)); palette=[]; colors=[(0,0,0),(255,255,255),(46,134,222),(255,99,71),(106,190,48),(255,209,102),(140,104,255),(30,30,30)]
> [palette.extend(c) for c in colors]; palette += [0,0,0]*(256-len(colors)); img.putpalette(palette)
> img.info['transparency'] = 0  # index 0 设为透明
> d=ImageDraw.Draw(img); d.rectangle([50,50,590,590],fill=2,outline=7,width=5); d.rectangle([140,140,500,500],fill=3,outline=1,width=4); d.text((170,300),'P+ALPHA',fill=4)
> img.save(root/'icon_alpha.png')
> print('Samples ready in ./samples')
> PY
> ```

- 横幅照片：`python compress.py banner.png --target-kb 80` → 期望 60–90 KB，保持 2540x965，输出 WebP，退出码 0。
- 透明 UI：`python compress.py samples/transparent.png --target-kb 60 --format webp` → 约 5–8 KB，尺寸不变；目前会铺底丢失透明（缺口记录），无警告，退出码 0。
- 插画/文字：`python compress.py samples/poster.png --target-kb 100 --min-quality 60` → 40–80 KB，保持 1500x2000，质量不低于 60，退出码 0。
- 超大原图：`python compress.py samples/huge.jpg --target-kb 200 --max-width 2000` → 先缩到 ≤2000 宽后约 60–120 KB（质量通常停在 90），退出码 0；若目标极低可能在 `--min-side` 触顶并返回 1。
- 强制 PNG：`python compress.py samples/icon.png --target-kb 80 --format png` → 体积通常 ≥2 KB，尺寸 640x640；若目标过低会打印“不可达”警告并退出码 1，用于提示 PNG 无损限制。
- 调色板 + 透明：`python compress.py samples/icon_alpha.png --target-kb 40 --format png` → palette 与透明索引保留，质量参数不生效；若目标继续压到 <30 KB 会进入 0.9 等比缩放，尺寸触达 `min_side` 后仍超标则 Warning + 退出码 1。若强制 `--format webp/jpeg` 透明会被铺底并放大体积（预期 3–8 KB）。

## 批量处理分层与命名/冲突指南
- 单图（已实现）：输入文件 → `<stem>_compressed.<ext>`；显式 `-o` 完全覆盖命名/路径，原文件不被覆盖。示例：`python compress.py banner.png --target-kb 80 -o out/banner.webp`。
- 多图/目录（计划）：
  - 输入可为目录或通配符（如 `assets/**/*.png`），输出默认复刻相对路径并在文件名追加 `_compressed`，写入 `--output-dir`（默认与输入同目录）。
  - 命名冲突处理（仅计划）：
    - 默认：若目标文件已存在则跳过并在日志中标记 `SKIP (exists)`。
    - `--overwrite`: 允许覆盖已存在输出。
    - `--versioned`: 在文件名后追加 `_v2`, `_v3` 递增后缀，避免覆盖。
  - 示例 1：`python compress.py assets/ --target-kb 90 --output-dir dist/ --overwrite` → `assets/hero.png` 写到 `dist/assets/hero_compressed.png`；若 dist 已有同名则覆盖并在日志中标记 `OVERWRITE`.
  - 示例 2：`python compress.py assets/**/*.png --target-kb 120 --output-dir dist/ --versioned` → 默认跳过已存在；若启用 `--versioned` 则生成 `*_compressed_v2` 并在日志中标记 `NEW (v2)`；未传覆盖/版本化则打印 `SKIP (exists)`。
- 预设/配置（计划）：
  - 通过 `--config preset.yaml` 读取默认 `target_kb/format/min_side` 等参数；命令行显式参数优先于配置，配置优先于内置默认。
  - 批量输出命名仍遵循 `_compressed` 规则，配置可选项允许自定义后缀（例如 `output_suffix: _opt`）。
  - 示例：`python compress.py list.txt --config presets/web.yml --format webp` → 若配置未指定 `format`，以命令行 `webp` 为准；输出文件统一追加 `_compressed` 或配置的后缀。
- 冲突处理原则（适用于多图/配置未来实现）：显式优先（命令行 > 配置 > 默认）；批量默认不覆盖，提供跳过/覆盖/版本化三选项；在冲突时输出决策摘要以便回溯。

## 工程化发布准备（草案）
- 关键步骤：定义发布形态（单脚本 or 包）、添加版本号与 changelog 流程、引入基础 CI（lint + 示例命令跑通）、验证 Pillow/WebP 兼容性并给出 fallback、打包/分发指引。
- WebP 可用性自检流程（建议纳入启动或 CI 前置）：  
  1) `from PIL import features`; 使用 `features.check("webp")` 判定编解码支持（解码/编码可分开检查）。  
  2) 若不支持：  
     - 运行时：回退默认输出格式为 JPEG，并在 stdout 摘要追加 `[webp-disabled]` 标记；当用户显式 `--format webp` 时给出可操作错误/提示“当前环境未启用 WebP，请安装 pillow 带 webp 或编译支持”。  
     - 文档/提示：提示安装 `pip install "pillow[webp]"` 或使用发行版已启用 WebP 的构建。  
  3) 可选深度自检：生成 1x1 RGBA 临时图尝试保存 WebP，捕获异常并打印明确 fallback 文案（例如 `Fallback to JPEG because WebP encoder unavailable`).  
- CI 验证项（建议）：  
  - `python -m compileall compress.py`：语法守护。  
  - README 最小回归命令串行跑通（至少横幅、透明/铺底、强制 PNG 三条），断言退出码、尺寸上限及“不可达”警告出现与否。  
  - 若 CI 环境缺 WebP，可分两路：一组启用 WebP 的 job、另一组禁用后验证 fallback 文案。  
- 退出码契约：不可达目标返回 1 且仍写文件；CI 应检查 stderr 警告存在，stdout 摘要格式稳定。  
- 依赖声明：文档/requirements 注明 Pillow 版本下限与 WebP 可选特性，示例安装命令含 `[webp]` 选项。
- 发布形态调研：对比“单文件脚本 + release asset” vs “pip 包 + entry point”；记录构建/上传步骤与潜在 CI 配置需求（如 GitHub Actions + PyPI token 或 Release 产物上传）。
- WebP 可用性自检的 CI 检查点与提示语（补充）：  
  - `features.check("webp")` / `features.check("webp_anim")` / `features.check_codec("webp", "encoder")` 结果写入日志；缺失时在摘要中追加 `[webp-disabled]`。  
  - 显式 `--format webp` 且不可用时：stderr 打印 `WebP encoder unavailable, fallback to JPEG (install pillow[webp])`，退出码保持 1 以便 CI 发现。  
  - 默认格式从 WebP 回退到 JPEG 时：stdout 摘要后缀 `(fallback=jpeg)`，仍视为成功路径供回归核对。  
  - CI 断言：禁用 WebP 的 job 需检测到上述提示文本；启用 WebP 的 job 需确认无 fallback 标记且能保存 RGBA → WebP（透明不丢失）。
- 入口命令 / 版本兼容验证待办清单：  
  - [ ] 提供 `pic-deal`（或同名）控制台入口包装 `compress.py`，附 `--version` 输出。  
  - [ ] 在 README/INSTALL.md 补充安装与入口示例（pip + 本地脚本双路径）。  
  - [ ] CI 运行最小命令矩阵（Python 3.8/3.10/3.12，含/不含 WebP），验证入口命令可执行、摘要格式稳定。  
  - [ ] 版本号与 CHANGELOG 发布节奏：定义语义化版本规则，打包/发布前需更新 changelog，并运行回归脚本集合。  
  - [ ] 可选：为入口命令添加 `--self-check` 触发 WebP/依赖自检，脚本/文档需说明预期输出与退出码。
