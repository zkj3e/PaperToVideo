# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

知识主播视频制作流水线 — 将 SRT 字幕/口播文本自动化生成 PPT 风格 HTML 幻灯片，再渲染为带字幕和音频对齐的 MP4 视频。同时包含 LTX 2.3 图生视频提示词生成能力（用于 ComfyUI 数字人口播视频）。

## 核心流水线

```
.srt 字幕 → [srt-to-ppt-html] → 带 data-time-* 属性的 .html → [render_slides.py] → .mp4 成片
```

### 第一步：生成 PPT HTML

由 `srt-to-ppt-html` skill 完成（见 `.claude/skills/srt-to-ppt-html/SKILL.md`）：
- 解析 SRT，语义分组为 N 页幻灯片
- 从 `html模版/` 中选择模板：`报纸风.html`（1920×1080，衬线字体）或 `赛博朋克风.html`（1280×720，霓虹风格）
- 每页 `.slide` 写入 `data-time-start="MM:SS"` / `data-time-end="MM:SS"` 属性
- **必须先确认风格和页数再生成**（用户偏好）

### 第二步：渲染视频

```bash
# 仅渲染 PNG 截图（每页一张）
python scripts/render_slides.py <html文件> <输出目录>
```

### 辅助脚本

| 脚本 | 用途 |
|------|------|
| `scripts/srt_to_text.py` | SRT → 纯文本（支持 `--lines` / `--join`） |
| `scripts/runninghub_digital_human_complete.py` | RunningHub 数字人视频生成 |

## LTX 提示词生成

由 `ltx-prompt-generator-v3` skill 完成（见 `.claude/skills/ltx-prompt-generator-v3/SKILL.md`，详细规范见 `doc/LTX提示词生成器V3.md`）。

输入：参考图片 + 完整口播文本 + 语音时长 + 分段数 + FPS + 是否后期对口型。
输出：`global_prompt`、`local_prompts`（` | ` 分隔）、`segment_lengths`、推荐参数、`negative_prompt` — 均直接复制到 ComfyUI Prompt Relay Encode 节点。

## Python 环境

```bash
# 虚拟环境位置
workspace/.venv  # Python 3.14

# 安装依赖
workspace/.venv/bin/pip install Pillow
```

## 关键约定

- 生成 PPT HTML 前必须先和用户确认风格（赛博朋克/报纸风）和页数
- 赛博朋克风**不添加可见导航按钮**，仅保留键盘翻页和鼠标点击
- 所有脚本硬编码 1280:704 缩放比（竖屏 9:16 场景），修改分辨率时需同步调整 `SCALE_VF`
- 视频默认 30fps，输出 H.264 + AAC
- `workspace/example/` 包含完整示例：音频、字幕、成品视频
- `人物形象/` 包含 AI 主播参考图、提示词、音色样本

## 系统依赖

- Python 3（venv: `workspace/.venv`）
- ffmpeg / ffprobe
- Pillow（HTML 渲染截图）
