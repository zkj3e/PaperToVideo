---
name: srt-to-video
description: 从 SRT 字幕一键生成带配音的 PPT 视频，串起 srt-to-ppt-html → render-slides 完整流水线
---

# srt-to-video

从 SRT 字幕文件到最终 MP4 视频的端到端流水线。

自动串联三个子步骤：字幕解析 → HTML PPT 生成 → 视频合成。

## 输入

| 参数 | 说明 | 必填 |
|------|------|------|
| SRT 文件 | `.srt` 字幕文件路径 | 是 |
| 音频文件 | `.flac` / `.mp3` / `.wav` 对齐音频 | 是 |
| 风格 | `newspaper`（报纸风，1920×1080）或 `cyberpunk`（赛博朋克风，1280×720） | 是 |
| 页数 | 目标幻灯片页数（建议 6–15） | 否，自动判定 |
| 标题 | 演示标题 | 否，自动提炼 |
| 输出路径 | 最终 `.mp4` 路径 | 否，默认为 `<html名>.mp4` |
| 分辨率 | WxH 格式 | 否，报纸风 `1920x1080`，赛博 `1280x720` |

## 流水线总览

```
┌──────────┐     ┌──────────────────┐     ┌───────────────────┐     ┌──────────┐
│ .srt 字幕 │ ──▶ │ srt-to-ppt-html  │ ──▶ │ render_slides.py   │ ──▶ │  .mp4    │
│          │     │ 生成带 data-time  │     │ 截图 + ffmpeg 合成  │     │  成片    │
│ .flac 音频│     │ 属性的 .html     │     │ + 烧录字幕         │     │          │
└──────────┘     └──────────────────┘     └───────────────────┘     └──────────┘
```

## 执行流程

### 第一步：确认参数

若用户未指定风格或页数，**先询问再动手**（遵循 [[ppt-confirm-style]]）：

- 给出风格选项（赛博朋克 / 报纸风）
- 给出页数建议（根据 SRT 时长和内容密度估算）
- 确认标题

### 第二步：生成 PPT HTML

调用 `srt-to-ppt-html` 的能力：

- 读取 SRT，解析为字幕块
- 按语义分组为 N 页幻灯片
- 每页写入 `data-time-start` / `data-time-end` 属性
- 生成 HTML 并保存到 SRT 同级目录

**关键约束**（来自 [[cyber-ppt-no-nav]]）：
- 赛博风不添加可见导航按钮
- 鼠标点击 + 键盘 ← → 翻页
- `overflow: hidden; height: 100vh` 单页全屏

### 第三步：渲染视频

调用 `scripts/render_slides.py`（即 `ppt-html-to-video` / `render-slides` 的视频模式）：

```bash
python scripts/render_slides.py <html路径> <页数> \
  --audio=<音频路径> \
  --srt=<字幕路径> \
  --output-video=<输出路径> \
  [--width=W] [--height=H] [--scale=SCALE]
```

这一步自动：
1. 从 HTML 解析 `data-time-*` → 每页秒数
2. Pillow 逐页渲染生成 PNG 图片
3. ffmpeg 合成视频 + 音频 + 烧录字幕

### 第四步：验证

- 在浏览器打开 HTML 确认翻页和时间标注正确
- 视频输出后确认时长与音频一致

## 使用示例

### 赛博朋克风（默认 1280×720 @2x）

```
用户：「把这个 srt 转成赛博朋克风的视频，音频用 语音.flac」

→ 确认页数
→ srt-to-ppt-html 生成 HTML（赛博风模板）
→ render_slides.py 渲染视频
→ 输出 .mp4
```

### 报纸风（1920×1080 @1x，适合横屏）

```
用户：「把字幕做成报纸风视频，1920x1080」

→ 确认页数
→ srt-to-ppt-html 生成 HTML（报纸风模板）
→ render_slides.py --width=1920 --height=1080 --scale=1
→ 输出 .mp4
```

### 竖屏短视频（1080×1920 @1x）

```bash
python scripts/render_slides.py ppt.html 10 \
  --audio=音频.flac --srt=字幕.srt \
  --output-video=竖屏.mp4 \
  --width=1080 --height=1920 --scale=1
```

## 时间分配说明

- 时间信息由 `srt-to-ppt-html` 写入 HTML 的 `data-time-start` / `data-time-end`
- `render_slides.py` 解析这些属性，精确按字幕时间分配每页展示时长
- 若 HTML 无时间属性，则用音频总时长均匀分配

## 依赖

- Python 3 + Pillow（`pip install Pillow`）
- ffmpeg

## 项目脚本索引

| 脚本 | 位置 | 用途 |
|------|------|------|
| `srt_to_text.py` | `scripts/srt_to_text.py` | SRT 解析（文本提取） |
| `render_slides.py` | `scripts/render_slides.py` | HTML→PNG→视频 |

## 模板索引

| 模板 | 位置 | 尺寸 | 风格 |
|------|------|------|------|
| 赛博朋克风 | `html模版/赛博朋克风.html` | 1280×720 | 深蓝黑底，青紫霓虹，扫描线 |
| 报纸风 | `html模版/报纸风.html` | 1920×1080 | 米黄底，衬线字体，12列网格 |

## 快速开始（当前项目）

```bash
cd /Volumes/zkj/personal/comfyui/知识主播

python scripts/render_slides.py \
  "剧本/今年的趋势已经打明牌了 时代变太快/今年的趋势已经打明牌了.html" 10 \
  --audio="剧本/今年的趋势已经打明牌了 时代变太快/语音.flac" \
  --srt="剧本/今年的趋势已经打明牌了 时代变太快/语音-flac-encoded.mp3 (3).srt" \
  --output-video="剧本/今年的趋势已经打明牌了 时代变太快/成片.mp4"
```
