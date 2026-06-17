---
name: "srt-to-article"
description: "Converts SRT subtitles to article text. Invoke when user wants to extract article/text from SRT files or generate bilingual (CN/EN) articles."
---

# SRT to Article

将 SRT 字幕文件转换为文章文本。

## 功能

- 解析 SRT 字幕文件，提取纯文本内容
- 自动检测语言（中文/英文）
- 输出到 `CN` 或 `EN` 目录的 `article.txt`

## 使用方法

```bash
python3 scripts/srt_to_article.py <srt文件路径>
```

## 示例

```bash
# 处理中文 SRT
python3 scripts/srt_to_article.py data/video/CN/video.srt

# 处理英文 SRT
python3 scripts/srt_to_article.py data/video/EN/video.srt
```

## 输出

- **中文 SRT** → 输出到 `{parent}/CN/article.txt`，段落用 `\n\n` 分隔
- **英文 SRT** → 输出到 `{parent}/EN/article.txt`，自动修复句间空格

## 工作流集成

通常作为视频制作流水线的前置步骤：

```
SRT 字幕 → srt-to-article → article.txt → RunningHub 数字人
```
