# 知识主播视频制作流水线

将 SRT 字幕/口播文本自动化生成包含 AI 数字人开头的完整视频。

## 核心功能

- **AI 数字人开头**：使用 RunningHub 生成数字人口播视频
- **PPT 幻灯片**：自动生成赛博朋克/报纸风格的幻灯片
- **视频合成**：数字人开头 + PPT 内容 + 音频合成完整视频

## 快速开始

### 1. 配置 RunningHub API Key

复制配置文件模板并编辑：

```bash
cp scripts/.runninghub_config.json.example scripts/.runninghub_config.json
```

编辑 `scripts/.runninghub_config.json`，填入你的 API Key 和 workflow_id。

**获取 API Key**: [RunningHub API 密钥页面](https://www.runninghub.ai/enterprise-api/consumerApi)

### 2. 安装依赖

```bash
brew install ffmpeg
pip install -r requirements.txt
```

### 3. 使用 Skill 生成视频

详细流程请查看 [article-to-video skill](.claude/skills/article-to-video.md)：

```bash
# 在 Trae IDE 中使用 @article-to-video skill
# 或查看 skill 文档获取完整流程指引
```

## 视频结构

```
0s ──────── 数字人时长 ──────── PPT开始 ────────────────── 最终时长
│                                   │
│          数字人开头               │         PPT 内容（多页幻灯片）
│        (AI数字人口播)             │         (完整文案)
```

## 流水线

```
┌─────────────┐     ┌────────────────────────┐     ┌──────────────┐
│  SRT 字幕    │ ──▶ │  RunningHub 数字人开头   │ ──▶ │  数字人视频   │
│  (文案输入)  │     │  (AI数字人口播)           │     │  (intro.mp4) │
└─────────────┘     └────────────────────────┘     └──────────────┘
                                                              │
                                                              ▼
┌─────────────┐     ┌────────────────────────┐     ┌──────────────┐
│  最终成片    │ ◀── │  音频合成 (ffmpeg)       │ ◀── │  PPT 视频    │
│  (成片.mp4) │     │  (intro + ppt + audio)  │     │  (ppt.mp4)   │
└─────────────┘     └────────────────────────┘     └──────────────┘
```

## 输出规格

| 属性 | 值 |
|------|-----|
| 分辨率 | 1280×720 |
| 帧率 | 30 fps |
| 视频编码 | H.264 (libx264) |
| 音频编码 | AAC |
| 音频采样率 | 22050 Hz |

## 相关文档

- [article-to-video skill](.claude/skills/article-to-video.md) - 完整的视频生成流程指南
- [runninghub-digital-human skill](.claude/skills/runninghub-digital-human.md) - RunningHub 数字人使用指南
- [srt-to-ppt-html skill](.claude/skills/srt-to-ppt-html/) - SRT 转 PPT HTML 指南
