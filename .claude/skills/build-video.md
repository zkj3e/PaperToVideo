---
name: compose-video
description: 将 SRT 字幕 + 音频 + PPT HTML 合成为带字幕的视频
---

# compose-video

将 SRT 字幕、音频文件、PPT HTML（或幻灯片图片）合成为带烧录字幕的 MP4 视频。

脚本位置: `剧本/scripts/compose_video.py`

## 用法

```bash
cd 剧本/<项目目录> && ../.venv/bin/python3 ../scripts/compose_video.py \
  "字幕.srt" \
  "音频.flac" \
  "演示文稿.html" \
  -o 成片.mp4
```

## 输入

| 参数 | 说明 | 必填 |
|------|------|------|
| `srt` | SRT 字幕文件 | 是 |
| `audio` | 音频文件 (flac/mp3/wav 等) | 是 |
| `ppt_html` | PPT HTML 文件，需包含 `.slide` class 的 div | 否* |

\* `ppt_html` 与 `--slide-images` 二选一。

## 选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `-r, --resolution WxH` | 视频分辨率 | 1280x720 |
| `-o, --output` | 输出路径 | output.mp4 |
| `--slide-durations` | 手动指定每页秒数，逗号分隔 | 自动分配 |
| `--no-render` | 跳过 HTML 渲染 | 否 |
| `--slide-images` | 已有图片 glob pattern | 无 |
| `--subtitle-style` | ffmpeg force_style 覆盖 | 内置样式 |

## 幻灯片时间分配

**自动模式（默认）**：优先在 SRT 字幕的自然停顿处（>=0.5s 间隔）换页，停顿不足时均匀分配。

**手动模式**：用 `--slide-durations` 精确控制，例如 8 页幻灯片：
```bash
--slide-durations 7.8,9.7,9.1,22.0,22.5,31.4,26.5,16.7
```

## 工作流程

1. 解析 SRT -> 提取字幕时间轴
2. headless Chromium 渲染 HTML -> 每页截图为 PNG
3. 分配幻灯片时间轴
4. ffmpeg 三步合成：PNG->mp4 片段 -> 拼接 -> 加音频+烧录字幕

## 依赖

Python 3 (venv: `剧本/.venv`), ffmpeg, playwright + chromium

## 常见场景

**已有截图，快速合成**：
```bash
../.venv/bin/python3 ../scripts/compose_video.py \
  "字幕.srt" 音频.flac \
  --slide-images "ppt/*.png" --no-render \
  -o 成片.mp4
```

**手动控制每页停留时间**：
```bash
../.venv/bin/python3 ../scripts/compose_video.py \
  "字幕.srt" 音频.flac 演示文稿.html \
  --slide-durations 7.8,9.7,9.1,22.0,22.5,31.4,26.5,16.7 \
  -o 成片.mp4
```

**指定分辨率和字幕样式**：
```bash
../.venv/bin/python3 ../scripts/compose_video.py \
  "字幕.srt" 音频.flac 演示文稿.html \
  -r 1920x1080 \
  --subtitle-style "FontSize=28,PrimaryColour=&H00FFFFFF,Outline=2" \
  -o 成片.mp4
```
