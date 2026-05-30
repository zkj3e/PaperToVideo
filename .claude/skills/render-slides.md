---
name: render-slides
description: 使用 Pillow 将 HTML PPT 内容规范渲染为 PNG 幻灯片序列图，支持报纸风和赛博朋克风主题
---

# render-slides

将 HTML PPT 的内容规范（主题、每页文案和时间范围）渲染为独立的 PNG 幻灯片图片（1280×720），使用 Pillow 绘制，支持**报纸风**和**赛博朋克风**两种视觉主题。

脚本位置: `scripts/render_slides.py`

## 用法

```bash
python3 scripts/render_slides.py <html_ppt.html> <输出目录>

# 示例
python3 scripts/render_slides.py "workspace/文章1/字幕-ppt.html" "workspace/文章1/ppt_frames"
```

## 输入

HTML PPT 文件（由 `srt-to-ppt-html` skill 生成），包含：
- `.slide` 元素，每个有 `data-time-start` / `data-time-end` 属性
- 页面内容（文字、标题、数据等）

## 输出

```
<输出目录>/
├── slide_01.png    # 幻灯片图片
├── slide_02.png
├── ...
└── slide_NN.png
```

每页时长根据 HTML 中的 `data-time-start` / `data-time-end` 自动计算，供后续视频合成使用。

## 主题识别

脚本根据 HTML 内容自动识别主题风格：

| 特征 | 主题 | 配色 |
|------|------|------|
| 米黄底 `#f4efe6` | 报纸风 | 深墨 + 红色强调 |
| 深蓝黑底 `#060816` | 赛博朋克风 | 青色 + 粉色发光 |

## 核心渲染逻辑（Pillow）

### 报纸风渲染
- 背景：米黄色 `#f4efe6`，叠加纸张纹理
- 字体：Noto Serif SC（衬线）+ Noto Sans SC（无衬线）
- 组件：kicker、display（92px）、headline（56px）、body（18px）、stat-card、quote、tag
- 布局：12 列网格系统

### 赛博朋克风渲染
- 背景：深蓝黑渐变 + 网格线
- 字体：SFNS / PingFang（中文）+ Orbitron（英文标题）
- 组件：display（72px Orbitron）、headline（40px）、subtitle（24px）、panel、stat、tag
- 特效：青色/粉色发光文字、面板半透明背景、扫描线纹理

### 每页渲染内容
从 HTML 中解析每页的：
- `data-time-start` / `data-time-end` → 时间范围（用于后续视频时间轴）
- 文字内容（kicker、标题、正文、数据、标签等）
- 组件类型和布局位置

## 依赖

```bash
pip install Pillow
```

无需 Playwright 或浏览器。

## 示例

**渲染报纸风 PPT**：
```bash
python3 scripts/render_slides.py "workspace/文章1/字幕-ppt.html" "workspace/文章1/ppt_frames"
```

**渲染赛博朋克风 PPT**：
```bash
python3 scripts/render_slides.py "workspace/文章1/字幕-ppt-cyberpunk.html" "workspace/文章1/cyberpunk_frames"
```

## 生成后操作

渲染完成后，每页时长记录在控制台输出中，例如：
```
第1页: 00:00 – 00:23
第2页: 00:23 – 00:50
...
```

这些时长信息传给 `build-video` skill 用于视频合成。