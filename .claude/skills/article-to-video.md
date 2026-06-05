---
name: article-to-video
description: 完整流水线：文本 → RunningHub数字人+音频+字幕 → 用字幕生成PPT幻灯片 → 视频合成。默认包含数字人开头+音频+字幕，无需询问。
---

# article-to-video

从纯文本文件生成完整视频，默认包含 AI 数字人开头 + TTS配音 + PPT内容。

**默认行为（无需询问用户）**：
1. 自动使用 RunningHub 生成数字人口播视频 + TTS音频 + SRT字幕
2. 用 SRT 字幕时间信息生成 PPT 幻灯片（带精确时间同步）
3. 合成最终视频

## 流水线总览

```
┌─────────────┐     ┌──────────────────────────────┐     ┌──────────────┐
│  纯文本      │ ──▶ │  RunningHub 数字人+音频+字幕   │ ──▶ │  数字人视频   │
│  (文案输入)  │     │  (AI数字人口播+SRT字幕)         │     │  (intro.mp4) │
└─────────────┘     └──────────────────────────────┘     │  数字人音频   │
                                                          │  (音频.flac)  │
                                                          │  字幕文件     │
                                                          │  (.srt)       │
                                                          └──────────────┘
                                                                 │
                                                                 ▼
                                                   ┌──────────────┐
                                                   │  用字幕生成   │
                                                   │  PPT HTML    │
                                                   │  (带时间同步) │
                                                   └──────────────┘
                                                                 │
                                                                 ▼
┌─────────────┐     ┌────────────────────────┐     ┌──────────────┐
│  最终成片    │ ◀── │  音频合成 (ffmpeg)       │ ◀── │  PPT 视频    │
│  (成片.mp4) │     │  (intro + ppt + audio)  │     │  (ppt.mp4)   │
└─────────────┘     └────────────────────────┘     └──────────────┘
                            ▲
                            │
                     ┌──────┴───────┐
                     │  视频拼接     │
                     │  ffmpeg concat│
                     └──────────────┘
```

## 视频结构

| 时间段 | 内容 |
|--------|------|
| 0s - N秒 | 数字人开头（AI数字人口播，时长由RunningHub决定） |
| N秒后 | PPT内容（HTML 演示文稿渲染的视频，与字幕时间同步） |

## 前置检查

### 检查 API Key 配置

在开始之前，请先检查 RunningHub API Key 是否已配置：

```bash
# 检查配置文件是否存在
ls -la scripts/.runninghub_config.json

# 检查 API Key 是否已配置（非 YOUR_API_KEY_HERE）
grep "api_key" scripts/.runninghub_config.json
```

如果配置文件不存在或 API Key 未配置，请先完成配置：

### 1. RunningHub API Key 配置

复制配置文件模板：

```bash
cp scripts/.runninghub_config.json.example scripts/.runninghub_config.json
```

编辑 `scripts/.runninghub_config.json`，填入你的 API Key：

```json
{
  "api_key": "你的API Key",
  "api_url": "https://www.runninghub.ai/openapi/v2/run/ai-app/{workflow_id}",
  "query_url": "https://www.runninghub.ai/openapi/v2/run/query",
  "workflow_id": "2059642920948559873",
  "instance_type": "default",
  "use_personal_queue": false,
  "poll": true,
  "poll_interval": 15,
  "max_wait": 600
}
```

**获取 API Key**: [RunningHub API 密钥页面](https://www.runninghub.ai/enterprise-api/consumerApi) → 创建 API Key

### 2. 系统依赖

```bash
# macOS
brew install ffmpeg

# Python 依赖
pip install Pillow
```

### 3. 输入文件准备

将以下文件放入工作目录（如 `workspace/文章1/`）：

| 文件 | 说明 |
|------|------|
| `xxx.txt` | 文案文件（用于 RunningHub 生成数字人+音频+字幕） |

**流程说明**：先用文案调用 RunningHub 生成数字人口播视频、TTS音频和SRT字幕；然后用 SRT 字幕的时间信息来生成 PPT，每页幻灯片的时间范围与字幕时间同步。

## 执行流程

### 第一步：生成 RunningHub 数字人开头 + TTS音频 + SRT字幕

使用完整文案生成数字人口播视频、TTS配音和SRT字幕：

```bash
python3 scripts/runninghub_digital_human_complete.py \
  --text "$(cat workspace/文章2/1.txt)" \
  --duration "00:15" \
  --output "workspace/文章2/intro_result.json"
```

**参数说明**：
- `--text`: 数字人口播的文案（使用完整文案或前N秒）
- `--duration`: 目标时长，建议 10-15 秒
- `--output`: 结果 JSON 文件路径

脚本会自动：
1. 调用 RunningHub 数字人API生成口播视频
2. 调用 RunningHub TTS生成完整音频
3. 调用 RunningHub 生成 SRT 字幕文件
4. 轮询任务状态直到完成

### 第三步：下载数字人视频、音频和字幕

任务完成后，从结果 JSON 获取视频、音频和字幕 URL 并下载：

**从 JSON 提取 URL**

```bash
python3 -c "
import json
with open('workspace/文章2/intro_result.json') as f:
    data = json.load(f)
    results = data.get('results', [])
    if results:
        print('Video URL:', results[0].get('url', 'No URL found'))
        # 检查是否有音频
        if len(results) > 1:
            print('Audio URL:', results[1].get('url', 'No Audio found'))
        # 检查是否有字幕
        if len(results) > 2:
            print('Subtitle URL:', results[2].get('url', 'No Subtitle found'))
    else:
        print('No results yet, check task status')
"
```

**下载视频、音频和字幕**
1. 打开 [RunningHub 控制台](https://www.runninghub.ai)
2. 进入「调用记录」查看任务
3. 下载数字人口播视频、TTS音频和SRT字幕文件

**文件命名**：
- 数字人口播视频：`workspace/文章2/数字人开头.mp4`
- TTS配音音频：`workspace/文章2/数字人音频.flac`
- SRT字幕文件：`workspace/文章2/字幕.srt`

### 第四步：用 SRT 字幕生成 PPT 幻灯片

使用 `srt-to-ppt-html` skill 将 SRT 字幕转换为 PPT 风格的 HTML 演示文稿：

1. 解析 SRT 字幕文件，按语义分组为多页幻灯片
2. 每页幻灯片使用字幕的时间范围（`data-time-start` / `data-time-end`）
3. 默认使用主题风格：`cyberpunk`（赛博朋克风）

**示例**：把 `workspace/文章2/字幕.srt` 做成赛博朋克风 PPT，生成约 10 页。

输出：`workspace/文章2/字幕-ppt.html`

### 第五步：将 HTML PPT 转换为视频

使用 Playwright 浏览器渲染 HTML 为高质量视频片段：

```bash
python3 scripts/render_slides_browser.py "workspace/文章2/字幕-ppt.html" "workspace/文章2/ppt_frames_browser"
```

输出：`workspace/文章2/ppt_frames_browser/slide_01.png` 等图片序列

### 第五步：合成最终视频

```bash
cd workspace/文章2

# 1. 合并数字人开头 + PPT 视频
ffmpeg -hide_banner -y \
  -i "数字人开头.mp4" \
  -i "ppt_video/ppt_body_raw.mp4" \
  -filter_complex "[0:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[v0];[1:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[v1];[v0][v1]concat=n=2:v=1:a=0[out]" \
  -map "[out]" \
  -c:v libx264 -preset fast -crf 20 \
  "成片_无音频.mp4"

# 2. 添加音频
ffmpeg -hide_banner -y \
  -i "成片_无音频.mp4" \
  -i "数字人音频.flac" \
  -map 0:v:0 -map 1:a:0 \
  -c:v copy -c:a aac -b:a 192k \
  -shortest \
  "最终成片.mp4"

# 3. 可选：烧录字幕
ffmpeg -hide_banner -y \
  -i "最终成片.mp4" \
  -i "字幕.srt" \
  -c copy -c:s ass \
  "最终成片_带字幕.mp4"
```

## 输出规格

| 属性 | 值 |
|------|-----|
| 分辨率 | 1280×720 |
| 帧率 | 30 fps |
| 视频编码 | H.264 (libx264) |
| 音频编码 | AAC |
| 音频采样率 | 22050 Hz |

## 目录结构示例

```
workspace/文章2/
├── 1.txt                                    # 原始文案文件
├── 数字人开头.mp4                          # 数字人视频
├── 数字人音频.flac                          # TTS完整音频
├── 字幕.srt                                # SRT字幕文件（由RunningHub生成）
├── intro_result.json                        # RunningHub 结果
├── 字幕-ppt.html                           # PPT HTML 演示文稿（用字幕时间生成）
├── ppt_frames_browser/                      # PPT 幻灯片图片（浏览器渲染）
│   └── slide_01.png
├── ppt_video/                              # PPT 视频
│   └── ppt_body_raw.mp4
├── 成片_无音频.mp4                         # 合并后无音频视频
└── 最终成片.mp4                            # 最终成片
```

## 故障排除

### RunningHub API 错误

**错误码 1001 (Invalid URL)**
- 检查 `scripts/.runninghub_config.json` 中的 `query_url`
- 正确值：`https://www.runninghub.ai/openapi/v2/query`

**任务状态未更新**
- 使用 `--poll_interval 5` 缩短轮询间隔
- 手动在 RunningHub 控制台检查任务状态

### 视频合成问题

**分辨率不匹配**
- 使用 `scale` 和 `pad` 滤镜统一分辨率

**音视频不同步**
- 确保使用 `-shortest` 参数

## 相关脚本

| 脚本 | 用途 |
|------|------|
| `scripts/runninghub_digital_human_complete.py` | RunningHub 数字人视频生成 |
| `scripts/srt_to_text.py` | SRT 转纯文本 |
| `scripts/render_slides_browser.py` | HTML PPT 渲染为 PNG 幻灯片（Playwright 浏览器） |

## 相关 Skill

| Skill | 用途 |
|-------|------|
| `srt-to-ppt-html` | SRT 字幕转换为 PPT 风格 HTML 演示文稿 |