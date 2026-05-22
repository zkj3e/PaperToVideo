# 知识主播视频制作流水线

将 SRT 字幕/口播文本自动化生成 PPT 风格 HTML 幻灯片，渲染为带字幕和音频对齐的 MP4 视频。同时包含 LTX 2.3 图生视频提示词生成（ComfyUI 数字人口播）。

## 核心流水线

```
SRT 字幕 → PPT HTML → PNG 幻灯片 → MP4 成片
```

### 1. 生成 PPT HTML

解析 SRT，按语义分组为 N 页幻灯片，套用 HTML 模板生成带 `data-time-*` 时间属性的演示文稿。

模板位于 [`html模版/`](html模版/)：
- **赛博朋克风** — 1280×720，霓虹/暗色风格
- **报纸风** — 1920×1080，衬线字体

### 2. 渲染幻灯片

```bash
# 渲染为 PNG（需要 Node.js + puppeteer）
cd 剧本/<项目名> && bash render_slides.sh <html文件> <输出目录> <页数>
```

### 3. 合成视频

```bash
# 方式一：HTML 含 data-time-* 时
python scripts/render_slides.py <html文件> <页数> \
  --audio=<音频.flac> --srt=<字幕.srt> --output-video=<成片.mp4>

# 方式二：从 SRT 自动分配时间
python scripts/compose_video.py 字幕.srt 音频.flac 演示文稿.html -o 成片.mp4

# 方式三：自定义构建脚本（含 intro/outro）
bash 剧本/<项目名>/build_video.sh
```

## 辅助脚本

| 脚本 | 用途 |
|---|---|
| `scripts/srt_to_text.py` | SRT → 纯文本 |
| `scripts/srt_to_qwentts_prompt.py` | SRT → 分段朗读稿（TTS 配音用） |
| `scripts/adjust_audio_speed.py` | 调整语速不变调 |
| `scripts/trim_video.py` | 裁剪视频到指定时长 |

## LTX 提示词生成

输入参考图片 + 口播文本 + 语音时长，输出 ComfyUI Prompt Relay Encode 节点所需的 `global_prompt`、`local_prompts`、`segment_lengths` 等参数。

详见 [`doc/LTX提示词生成器V3.md`](doc/LTX提示词生成器V3.md)。

## 环境

```bash
# Python 虚拟环境
workspace/.venv/bin/pip install playwright
workspace/.venv/bin/playwright install chromium

# 系统依赖
brew install ffmpeg node
```

## 目录结构

```
├── html模版/          # PPT HTML 模板
├── scripts/           # Python 辅助脚本
├── doc/               # LTX 提示词规范文档
├── workspace/         # Python venv + 示例文件
├── 人物形象/           # AI 主播参考图/提示词/音色
└── 剧本/              # 各期视频的 HTML/音频/字幕/成品
```

## 输出规格

- 视频：1280×704（竖屏缩放适配），30fps，H.264 + AAC
- 幻灯片 PNG：1280×720 @2x
