---
name: ppt-html-to-video
description: 将带时间属性的 PPT HTML 渲染为视频，适用知识主播配图成片场景
---

# ppt-html-to-video

将包含 `data-time-start` / `data-time-end` 时间属性的 PPT HTML 渲染为带音频的视频文件。

脚本位置: `scripts/render_slides.py`（复用 render-slides 的视频模式）

## 前置条件

HTML 的每页 `.slide` 元素必须包含时间属性：

```html
<div class="slide" data-time-start="00:11" data-time-end="00:27">
```

如果没有这些属性，先从 SRT 生成带时间属性的 HTML（用 `srt-to-ppt-html` skill）。

## 输入

| 参数 | 说明 | 必填 |
|------|------|------|
| PPT HTML 路径 | 包含 data-time-start/end 属性的 HTML 文件 | 是 |
| 页数 | 幻灯片总页数 | 是 |
| 音频文件 | flac / mp3 / wav 格式的对齐音频 | 是 |
| SRT 字幕 | 用于烧录字幕 | 否 |

## 用法

```bash
python scripts/render_slides.py <html路径> <页数> \
  --audio=<音频路径> \
  [--srt=<字幕路径>] \
  [--output-video=<输出视频路径>] \
  [--width=1920] [--height=1080] [--scale=1]
```

## 示例

**最小调用**：
```bash
python scripts/render_slides.py \
  "剧本/项目/演示.html" 10 \
  --audio="剧本/项目/音频.flac" \
  --output-video="剧本/项目/成片.mp4"
```

**带字幕烧录**：
```bash
python scripts/render_slides.py \
  "剧本/项目/演示.html" 10 \
  --audio="剧本/项目/音频.flac" \
  --srt="剧本/项目/字幕.srt" \
  --output-video="剧本/项目/成片.mp4"
```

**1080p 竖屏（9:16，适合短视频平台）**：
```bash
python scripts/render_slides.py \
  "剧本/项目/演示.html" 10 \
  --audio="剧本/项目/音频.flac" \
  --srt="剧本/项目/字幕.srt" \
  --output-video="剧本/项目/成片.mp4" \
  --width=1080 --height=1920 --scale=1
```

## 工作流程

1. 解析 HTML 中每页 `.slide` 的 `data-time-start` / `data-time-end` → 秒数
2. Pillow 逐页渲染 → PNG（`<html名>_frame/slide_NN.png`）
3. ffmpeg 三步合成：
   - PNG → 按时长的 mp4 片段
   - 拼接所有片段
   - 叠加音频 + 可选字幕烧录

## 输出

```
<HTML所在目录>/
├── <html名>_frame/
│   ├── slide_01.png
│   └── ...
└── <html名>.mp4  ← 最终视频
```

## 依赖

- Python 3 + Pillow（`pip install Pillow`）
- ffmpeg

## 适用场景

- 知识主播口播视频配图成片
- SRT 字幕 → HTML 幻灯片 → 最终视频的自动化流水线
- 快速批量生成多素材视频

## 时间分配逻辑

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1 | HTML `data-time-*` 属性 | 精确按属性值分配 |
| 2 | 音频总时长均匀分配 | 无时间属性时的兜底 |

## 与 srt-to-ppt-html 的组合

标准流水线：

```
.srt 字幕 → [srt-to-ppt-html] → 带时间的 .html → [ppt-html-to-video] → .mp4
```

两个 skill 间通过 `data-time-start` / `data-time-end` 属性自动传递时间信息，无需人工介入。
