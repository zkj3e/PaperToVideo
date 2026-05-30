---
name: build-video
description: 将幻灯片图片序列 + 音频 + 数字人开头视频合成为完整成片
---

# build-video

将 `render-slides` 输出的 PNG 幻灯片图片序列，拼接为连续视频，再与音频、数字人开头视频合成最终成片。

## 流水线

```
幻灯片图片 (PNG)
  ↓
ffmpeg 渲染为 MP4 片段（每页按时间范围设定时长）
  ↓
ffmpeg concat 拼接所有片段
  ↓
PPT 视频 (ppt_video/ppt_body_raw.mp4)
  ↓
ffmpeg 拼接（数字人开头 + PPT 视频）
  ↓
添加音频 → 最终成片
```

## 用法

### 完整流水线（数字人开头 + PPT + 音频）

```bash
python3 scripts/build_video.py \
  --slides "ppt_frames/slide_%02d.png" \
  --durations "23,27,44,50,70,46,35,31,30" \
  --audio "音频.flac" \
  --intro "数字人开头.mp4" \
  --output "最终成片.mp4"
```

### 仅 PPT 视频（无数字人开头）

```bash
python3 scripts/build_video.py \
  --slides "ppt_frames/slide_%02d.png" \
  --durations "23,27,44,50,70,46,35,31,30" \
  --audio "音频.flac" \
  --output "PPT成片.mp4"
```

### 仅渲染视频片段（不添加音频）

```bash
python3 scripts/build_video.py \
  --slides "ppt_frames/slide_%02d.png" \
  --durations "23,27,44,50,70,46,35,31,30" \
  --output "ppt_video/ppt_body_raw.mp4"
```

## 参数

| 参数 | 说明 | 必填 |
|------|------|------|
| `--slides` | PNG 图片路径 pattern，用 `%02d` 占位 | 是 |
| `--durations` | 每页幻灯片时长（秒），逗号分隔 | 是 |
| `--audio` | 音频文件路径 (flac/mp3/wav) | 否 |
| `--intro` | 数字人开头视频路径 | 否 |
| `--output` | 输出视频路径 | 是 |
| `--srt` | SRT 字幕文件（烧录字幕用） | 否 |
| `--width` | 输出视频宽度 | 默认 1280 |
| `--height` | 输出视频高度 | 默认 720 |
| `--fps` | 帧率 | 默认 30 |
| `--crf` | H.264 质量 (0-51，越低越高清) | 默认 18 |

## 时长计算方法

每页时长由 HTML PPT 中的 `data-time-start` / `data-time-end` 计算：

```
第N页时长 = data-time-end(N) - data-time-start(N)
```

例如：
```
第1页: 00:00 – 00:23 → 23秒
第2页: 00:23 – 00:50 → 27秒
第3页: 00:50 – 01:34 → 44秒
```

## 完整流水线步骤

### 第一步：生成幻灯片图片

使用 `render-slides` skill：
```bash
python3 scripts/render_slides.py "字幕-ppt.html" "ppt_frames"
```

### 第二步：渲染视频片段

```bash
mkdir -p ppt_video
durations=(23 27 44 50 70 46 35 31 30)

for i in $(seq 1 9); do
  idx=$((i-1))
  dur="${durations[$idx]}"
  png=$(printf "ppt_frames/slide_%02d.png" $i)
  ffmpeg -hide_banner -y -loop 1 -i "$png" -t "$dur" \
    -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p" \
    -r 30 -c:v libx264 -preset veryfast -crf 18 -an "ppt_video/slide_${i}.mp4"
done
```

### 第三步：拼接 PPT 视频

```bash
cat > ppt_video/list.txt << 'EOF'
file 'slide_1.mp4'
file 'slide_2.mp4'
...
EOF

ffmpeg -hide_banner -y -f concat -safe 0 -i ppt_video/list.txt \
  -c copy ppt_video/ppt_body_raw.mp4
```

### 第四步：合并数字人开头 + PPT 视频

```bash
ffmpeg -hide_banner -y \
  -i "数字人开头.mp4" \
  -i "ppt_video/ppt_body_raw.mp4" \
  -filter_complex "[0:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[v0];[1:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[v1];[v0][v1]concat=n=2:v=1:a=0[out]" \
  -map "[out]" \
  -c:v libx264 -preset fast -crf 20 \
  "成片_无音频.mp4"
```

### 第五步：添加音频

```bash
ffmpeg -hide_banner -y \
  -i "成片_无音频.mp4" \
  -i "音频.flac" \
  -map 0:v:0 -map 1:a:0 \
  -c:v copy -c:a aac -b:a 192k \
  -shortest \
  "最终成片.mp4"
```

## 依赖

```bash
brew install ffmpeg
pip install Pillow
```

## 输出规格

| 属性 | 值 |
|------|-----|
| 分辨率 | 1280×720（默认） |
| 帧率 | 30 fps |
| 视频编码 | H.264 (libx264) |
| 音频编码 | AAC |
| 音频码率 | 192kbps |