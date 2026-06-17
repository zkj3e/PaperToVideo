---
name: "ppt-video-troubleshooting"
description: "Troubleshoots PPT video generation issues including duplicate slides, resolution mismatch, and HTML parsing errors. Invoke when user reports PPT problems or video synthesis failures."
---

# PPT Video Troubleshooting Guide

## 常见问题与解决方案

### 1. 幻灯片内容重复（所有PPT都是同一张）

**症状**: `ppt_frames` 目录下所有 `slide_*.png` 文件内容完全相同

**根本原因**: `render_slides.py` 中 HTML 解析逻辑存在缺陷：
- `parse_html_for_newspaper_slides` 使用正则表达式 `r'<(?:div|section)\b[^>]*\bclass\s*=\s*"[^"]*\bslide\b(?!-)[^"]*"[^>]*>(.*?)</(?:div|section)>'` 
- 非贪婪匹配 `(.*?)` 遇到嵌套的第一个 `</div>` 时提前终止
- 导致只提取到幻灯片的第一个元素（如 kicker）

**解决方案**:
1. 使用 BeautifulSoup 替代正则表达式解析 HTML：
```python
def parse_html_for_cyberpunk_slides(html_path: Path):
    content = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(content, 'html.parser')
    slides = []
    for slide_elem in soup.find_all('div', class_=lambda x: x and 'slide' in x and 'slide-' not in x):
        # BeautifulSoup 自动处理嵌套标签
        ...
```

2. 修改 HTML 结构，将 `<section>` 替换为 `<div>`，避免嵌套问题

**验证方法**:
```bash
# 运行 render_slides.py 后检查 MD5
md5 *.png | uniq -d  # 如果有输出说明有重复
```

### 2. 视频分辨率不一致

**症状**: FFmpeg 报错 `Input link in0:v0 parameters do not match`

**常见场景**:
- 数字人视频: 1280x704
- PPT 视频: 1280x720

**解决方案**: 在合成前统一缩放所有视频到目标分辨率（推荐 1280x720）

```bash
ffmpeg -y -i "视频1.mp4" -i "视频2.mp4" -i "音频.flac" \
  -filter_complex "[0:v]scale=1280:720,setsar=1[v0];[1:v]scale=1280:720,setsar=1[v1];[v0][v1]concat=n=2:v=1:a=0[out]" \
  -map "[out]" -map 2:a:0 -c:v libx264 -c:a aac -shortest "输出.mp4"
```

### 3. 幻灯片时长不正确

**症状**: 幻灯片切换太快或太慢

**原因**: `data-time-start` 和 `data-time-end` 属性未正确读取，或 PNG 序列帧率设置不当

**解决方案**:
1. 确保 HTML 中每个 slide 都有正确的时间属性：
```html
<div class="slide active" data-time-start="00:00" data-time-end="00:18">
```

2. 生成视频时根据时长设置每张幻灯片的持续时间

### 4. FFmpeg 音视频同步问题

**症状**: 音频和视频不同步，或出现 ` Unable to find a suitable output format`

**常见原因**:
- 输出文件名末尾有 `~` 字符（Shell 自动补全问题）
- 音频采样率不匹配

**解决方案**:
```bash
# 使用绝对路径，避免特殊字符问题
ffmpeg -y -i "/full/path/to/视频.mp4" -i "/full/path/to/音频.flac" ...
```

## 验证流程

### 生成 PPT 后必做检查

1. **PNG 唯一性验证**:
```bash
cd /path/to/ppt_frames
# 方法1: 使用 MD5
md5 *.png | sort | uniq -d  # 无输出=无重复
# 方法2: 使用 render_slides.py 内置验证（已添加）
python3 scripts/render_slides.py <html> <output_dir>
```

2. **分辨率验证**:
```bash
for f in *.png; do identify "$f"; done | sort -u
# 应输出单一分辨率如 1280x720
```

3. **视频片段时长验证**:
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 video.mp4
```

### 完整流水线检查清单

- [ ] HTML 文件语法正确
- [ ] 每个 slide 元素有独立的内容（kicker/headline/display 等）
- [ ] PNG 文件 MD5 唯一
- [ ] 所有视频分辨率统一为 1280x720
- [ ] 音视频时长匹配
- [ ] FFmpeg concat 滤镜正确配置

## 相关文件

- `/scripts/render_slides.py` - HTML PPT 渲染为 PNG 序列
- `/scripts/runninghub_digital_human_complete.py` - 数字人视频和 TTS 生成
- `workspace/<文章>/ppt_frames/` - PNG 幻灯片输出目录
- `workspace/<文章>/ppt_video/` - PPT 视频输出目录
