---
name: render-slides
description: 将 HTML PPT 渲染为 PNG 幻灯片序列图，可选根据 HTML 中的时间信息自动合成视频
---

# render-slides

将 HTML PPT 的每一页渲染为独立的 PNG 图片（1280x720 @2x），输出到 HTML 同级目录下的 `<文件名>_frame/`。

**当 HTML 包含 `data-time-start` / `data-time-end` 属性且提供音频文件时**，自动进一步合成带时间对齐的视频。

脚本位置: `scripts/render_slides.py`

## 用法

### 仅渲染 PNG

```bash
python scripts/render_slides.py <html文件> [幻灯片数量] [选项]
```

### 渲染 + 自动合成视频

```bash
python scripts/render_slides.py <html文件> <幻灯片数量> \
  --audio=<音频.flac> \
  [--srt=<字幕.srt>] \
  [--output-video=<成片.mp4>]
```

## 参数

| 参数 | 说明 | 必填 |
|------|------|------|
| `html文件` | PPT HTML 文件路径 | 是 |
| `幻灯片数量` | 总页数 | 否，默认 8 |

## 选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--width=N` | 视口宽度 | 1280 |
| `--height=N` | 视口高度 | 720 |
| `--scale=N` | 设备缩放因子 | 2 |
| `--slides=N` | 幻灯片数量（同位置参数） | 8 |
| `--port=N` | HTTP 服务器端口 | 8765 |
| `--audio=<路径>` | **视频模式**：音频文件路径 (flac/mp3/wav) | 无 |
| `--srt=<路径>` | **视频模式**：SRT 字幕文件（用于烧录字幕） | 无 |
| `--output-video=<路径>` | **视频模式**：输出视频路径 | `<html文件名>.mp4` |

## 输出

### 仅渲染模式

```
<html所在目录>/
└── <html文件名>_frame/
    ├── slide_01.png
    ├── slide_02.png
    ├── ...
    └── slide_NN.png
```

### 视频模式

在上述 PNG 输出之外，额外生成：

```
<html所在目录>/
└── <html文件名>.mp4   （或 --output-video 指定路径）
```

## 视频模式工作流程

1. 解析 HTML 中 `.slide` 元素的 `data-time-start` / `data-time-end` 属性（`MM:SS` 格式），转为秒数
2. 启动内置 HTTP 服务器，headless Chromium 逐页截图 PNG（同仅渲染模式）
3. 用 ffmpeg 三步合成：
   - 每页 PNG → 对应时长的 mp4 片段
   - 拼接所有片段
   - 叠加音频 + 可选烧录 SRT 字幕

**时间分配优先级：**
1. HTML 中有 `data-time-start` / `data-time-end` → 按属性值精确分配
2. 无时间属性 → 用音频总时长均匀分配到各页

## 依赖

Python 3, playwright + chromium, ffmpeg

```bash
pip install playwright && playwright install chromium
```

## 示例

**仅渲染 8 页幻灯片**：
```bash
python scripts/render_slides.py "剧本/项目/演示.html" 8
```

**渲染 10 页 + 自动合成视频（HTML 含时间属性）**：
```bash
python scripts/render_slides.py "剧本/项目/演示.html" 10 \
  --audio="剧本/项目/音频.flac" \
  --output-video="剧本/项目/成片.mp4"
```

**渲染 + 视频 + 烧录字幕**：
```bash
python scripts/render_slides.py "剧本/项目/演示.html" 10 \
  --audio="剧本/项目/音频.flac" \
  --srt="剧本/项目/字幕.srt" \
  --output-video="剧本/项目/成片.mp4"
```

**自定义分辨率**：
```bash
python scripts/render_slides.py 演示文稿.html 13 --width=1920 --height=1080 --scale=1
```

## 与 srt-to-ppt-html 的协作

1. `srt-to-ppt-html` 生成 HTML 时会在每个 `.slide` 上写入 `data-time-start="MM:SS"` 和 `data-time-end="MM:SS"` 属性
2. 本 skill 读取这些时间属性，自动分配视频中每页的展示时长
3. 因此无需再手动指定 `--slide-durations`，也无需通过 SRT 重新计算时间分配

这是与 `compose-video`（需要 SRT 文件来计算时间分配）的主要区别 — `render-slides` 的视频模式依赖 HTML 内嵌的时间属性，适合已经通过 `srt-to-ppt-html` 生成好 HTML 的场景。
