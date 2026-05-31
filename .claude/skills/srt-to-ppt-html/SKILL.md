---
name: srt-to-ppt-html
description: >-
  Parse SRT subtitle files and generate PPT-style HTML presentations using
  templates from html模版/ (newspaper or cyberpunk style). Use when the user
  wants to convert subtitles/transcripts into visual slides, 字幕转PPT,
  SRT转HTML幻灯片, or 知识主播配图幻灯片.
---

# SRT → PPT HTML 生成

将 .srt 字幕文件解析为可播放的 PPT 风格 HTML 演示文稿，提供键盘翻页和点击翻页。**每页幻灯片记录对应字幕的时间范围**，用于与视频/音频同步。

## 输入（向用户确认或从上下文推断）

| 参数 | 必填 | 说明 |
|------|------|------|
| `srt_path` | 是 | .srt 字幕文件路径 |
| `theme` | 否 | `cyberpunk`（赛博朋克风）或 `newspaper`（报纸风）；**未给时默认赛博朋克风** |
| `num_slides` | 否 | 目标页数；未给则根据内容自动分组（通常 6–15 页） |
| `title` | 否 | 演示总标题；未给则从字幕文件名或正文提炼 |
| `output_path` | 否 | 输出 .html 路径；默认与字幕同名、同目录，后缀 `-ppt.html` |

若用户只给文件路径未给主题，**默认使用赛博朋克风**；若页数也不明确，自动判断即可。

## 输出

1. **主交付物**：一个自包含的 HTML 文件（仅依赖 Google Fonts CDN），支持：
   - 键盘 ← → ↑ ↓ Space 翻页
   - 点击画面左半区上一页，右半区下一页
   - 响应式缩放适应窗口
   - 每页幻灯片标注对应字幕的时间范围（`data-time-start` / `data-time-end`），页脚显示时间区间
2. **元信息**：文件保存后告知用户页数、每页时间范围、保存路径。

## 模板参考

两个模板文件位于 [html模版/](../../../html模版/)：

### 报纸风 ([报纸风.html](../../../html模版/报纸风.html))
- 尺寸：1920×1080
- 配色：米黄底 `#f4efe6`，深墨文字，红色强调 `#c62828`
- 字体：Noto Serif SC（衬线）+ Noto Sans SC（无衬线）
- 布局：12 列网格系统，支持 `.col-12`/`.col-8`/`.col-6`/`.col-4`
- 组件：kicker、display、headline、title、body、hairline、stat-card、stat-number、stat-label、quote、card、tag-row、tag/tag.red
- 动画：`.reveal` + `.d1–d5` 延迟逐行淡入
- 页脚：footer 显示来源 + 页码

### 赛博朋克风 ([赛博朋克风.html](../../../html模版/赛博朋克风.html))

#### 基础规格
- **尺寸**：1280×720（16:9 比例）
- **背景**：深蓝黑渐变 `radial-gradient(circle at 10% 20%, #03050b, #000000)`
- **网格纹理**：`.cyber-bg` 创建 50px 赛博网格线（青色 `#0af`，透明度12%）
- **光效**：`.glow-gradient` 径向渐变发光（青色+紫色）

#### 配色系统（CSS 变量）
```css
--bg: #060816;        /* 主背景：深邃蓝黑 */
--bg-light: #0a0f1e;  /* 浅色面板背景 */
--cyan: #00e5ff;      /* 霓虹青 */
--pink: #ff2ea6;      /* 霓虹粉 */
--purple: #8b5cf6;    /* 紫色 */
--gold: #f0a500;      /* 金色（用于盈利数据） */
--ink: #d8e7ff;       /* 主文字：冷白 */
--muted: #6e7ea8;     /* 次要文字 */
--success: #0f0;      /* 成功绿 */
--error: #ff3366;     /* 错误红 */
```

#### 字体系统
- **英文标题**：Orbitron（科幻感，等宽显示）
- **中文正文**：Noto Sans SC（无衬线，清晰易读）
- **代码/终端**：Fira Code / monospace

#### 核心组件详解

| 组件 | class 名 | 视觉特征 | 适用场景 |
|------|----------|---------|---------|
| **背景网格** | `.cyber-bg` | 50px 青色网格线，12%透明度，fixed 定位 | 全局背景 |
| **发光层** | `.glow-gradient` | 径向渐变，blur(80px)，pointer-events:none | 氛围光效 |
| **高亮文字** | `.highlight` | 青色 `#0ff`，text-shadow 发光 `0 0 6px cyan` | 强调关键词 |
| **徽章** | `.badge` | 半透明青色背景，backdrop-filter:blur，左侧 2px cyan 边框 | 标签/角标 |
| **主标题** | `.display` | Orbitron 字体，渐变文字（白→青），大字号 | 封面标题 |
| **副标题** | `.subtitle` | 较大字号，冷白色，清晰可读 | 正文/说明 |
| **面板** | `.panel` | 半透明黑底 `rgba(0,0,0,0.5)`，backdrop-filter:blur(12px)，圆角32px，border:1px solid rgba(0,255,255,0.4) | 卡片容器 |
| **统计数字** | `.stat` > `.number` | Orbitron 字体，霓虹青/粉/紫色，大字号 | 数据展示 |
| **统计标签** | `.stat` > `.label` | 较小字号，muted 颜色 | 数据说明 |
| **错误日志** | `.error-log` | 黑底 `#03060e`，橙色文字 `#ff9e6e` | 终端风格 |
| **错误行** | `.error-line` | 左侧 2px 红色边框，橙红色文字 | 错误信息 |
| **成功标签** | `.success-tag` | 绿色文字，上边框分隔 | 状态指示 |
| **评论卡片** | `.comment` | 半透明深蓝底，左侧 5px cyan 边框，圆角28px | 用户评价 |
| **闪烁文字** | `.blink-text` | animation: pulse 1.2s infinite | 动态强调 |

#### 面板布局结构
```
.panel（面板容器）
  └── .stat（统计单元）
       ├── .number（数字，Orbitron）
       └── .label（标签说明）
```

#### 按钮样式
| 按钮 | class | 特征 |
|------|-------|------|
| 主按钮 | `.btn-primary` | 渐变 `#0ac8ff → #b62eff`，圆角40px，box-shadow 发光，hover 放大 |
| 次按钮 | `.btn-secondary` | 半透明深蓝底，1px #3b82f6 边框 |
| 轮廓按钮 | `.btn-outline-light` | 透明背景，1px cyan 边框，圆角40px |

#### 动画效果
- **脉冲动画** `.pulse`：
  ```css
  @keyframes pulse {
    0% { opacity: 1; text-shadow: 0 0 0px cyan; }
    50% { opacity: 0.7; text-shadow: 0 0 6px cyan; }
    100% { opacity: 1; }
  }
  ```
- **悬停效果** `.feature-card:hover`：上浮 6px + 发光边框

#### 赛博朋克风组件映射（详细版）
- 封面主标题 → `.display`（渐变 Orbitron）
- 章节副标题 → `.subtitle`
- 强调词/关键词 → `.highlight`（霓虹青发光）
- 数据展示 → `.panel` > `.stat` > `.number` + `.label`
- 标签/徽章 → `.badge` 或 inline `.tag`
- 终端/代码风格 → `.error-log` > `.error-line`
- 用户评价 → `.comment`（左侧 cyan 边框）
- 盈利数据 → `.profit-badge`（金色渐变）
- 按钮 → `.btn-primary` / `.btn-secondary`

#### 生成赛博朋克风 PPT HTML 的 CSS 结构模板
```css
/* 必选：背景层 */
.cyber-bg {
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background-image: 
    linear-gradient(#0af3 1px, transparent 1px),
    linear-gradient(90deg, #0af3 1px, transparent 1px);
  background-size: 50px 50px;
  opacity: 0.12;
  pointer-events: none;
  z-index: 0;
}
.glow-gradient {
  position: fixed;
  top: -30%; left: -20%;
  width: 140%; height: 140%;
  background: radial-gradient(circle, rgba(0,255,255,0.15), rgba(255,0,255,0) 70%);
  filter: blur(80px);
  pointer-events: none;
  z-index: 0;
}

/* 幻灯片容器 */
.slide {
  position: relative;
  width: 1280px;
  height: 720px;
  background: radial-gradient(circle at 10% 20%, #03050b, #000000);
  color: #d8e7ff;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  overflow: hidden;
}

/* 面板卡片 */
.panel {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(12px);
  border-radius: 32px;
  border: 1px solid rgba(0, 255, 255, 0.4);
  padding: 24px 32px;
  box-shadow: 0 0 15px rgba(0, 180, 255, 0.2);
}

/* 高亮文字 */
.highlight {
  color: #0ff;
  text-shadow: 0 0 6px cyan;
}

/* 统计数字 */
.stat .number {
  font-family: 'Orbitron', monospace;
  font-size: 3rem;
  font-weight: 800;
  color: var(--cyan);
}
.stat .label {
  font-size: 0.9rem;
  color: var(--muted);
  margin-top: 4px;
}

/* 页脚 */
.footer {
  position: absolute;
  bottom: 20px;
  left: 0; right: 0;
  display: flex;
  justify-content: space-between;
  padding: 0 40px;
  font-size: 13px;
  color: var(--muted);
}
.slide-time {
  font-family: monospace;
  color: var(--cyan);
  letter-spacing: 1px;
}
```

## 生成流程

### 1. 解析 SRT

读取 .srt 文件，按空行分隔字幕块，每块提取：
- 序号（忽略）
- 时间码（起止时间，**必须保留**，用于后续分配到各幻灯片）
- 正文文本（去除 `<b>` `<i>` 等标签）

已有现成的 SRT 解析逻辑可直接复用；也可直接读取文件用正则解析。
可参考 [scripts/srt_to_text.py](../../../scripts/srt_to_text.py) 的解析方式。

**时间保留格式**：内部使用 `HH:MM:SS` 或秒数，最终输出到 HTML 时统一为 `MM:SS` 格式。

### 2. 提取关键信息

从全部字幕正文中标记：
- **核心概念/主题词**：高频名词、机构名、报告中反复出现的概念
- **关键数字/数据**：百分比（如 94%、33%、71%）、倍数、金额、人数
- **对比关系**：A vs B、理论 vs 实际、前 vs 后
- **案例/故事**：公司名 + 做了什么 + 结果
- **金句/结论**：可作 quote 的强观点句
- **分类清单**：职业列表、模式列表、建议列表

### 3. 分组为幻灯片

按以下优先级决定分页断点：

1. **语义转折**：话题切换（如「第一…第二…第三…」）、时间大跳跃
2. **自然段落**：原文有明显分段信号词的位置
3. **信息密度**：每页 2–5 个要点，单页正文不超过 80–100 字
4. **页面角色分配**（按 num_slides 调整）：

**每页时间范围记录**：分组完成后，为每页记录：
- `slide_time_start`：该页第一条字幕的起始时间
- `slide_time_end`：该页最后一条字幕的结束时间
- 格式：`MM:SS`（如 `00:00` → `03:17`）

断点处的字幕时间即为下一页的起始时间。封面页无对应字幕时，时间范围留空或用第一条字幕的时间。

| 角色 | 占比 | 推荐模板组件 |
|------|------|-------------|
| 封面 | 1 页 | display + subtitle/kicker |
| 数据对比 | 1–2 页 | stat-card + stat-number |
| 核心观点 | 2–4 页 | headline + body + quote |
| 案例/清单 | 1–2 页 | card + tag-row / body |
| 警示/趋势 | 1–2 页 | quote + body + stat-card |
| 收束/金句 | 1 页 | display/headline + quote |
| 结尾 | 1 页 | 感谢观看 / 金句 |

若用户指定页数，按上述比例分配；若未指定，按自然分组生成（通常 8–15 页）。

### 4. 选模板组件匹配内容

**报纸风组件映射：**
- 封面主标题 → `.display`
- 章节标题 → `.headline`
- 段落正文 → `.body`
- 关键数字 → `.stat-number` + `.stat-label` 放在 `.stat-card` 里
- 强观点/金句 → `.quote`
- 标签列表 → `.tag-row` 里的 `.tag` / `.tag.red`
- 补充说明 → `.card` + `.small.sans.muted`
- 分隔线 → `.hairline` / `.hairline.thick`
- 来源/页码 → `.footer`

**赛博朋克风组件映射：**
- 封面主标题 → `.display`
- 副标题 → `.subtitle`
- 数据面板 → `.panel` 内 `.stat` > `.number` + `.label`
- 英文术语标注 → 自然使用 Orbitron 字体

### 5. 写 HTML

**必须遵守：**
- 完整复制模板的 `<style>` 块（CSS 变量、基础样式、组件样式、动画），确保视觉效果一致
- 完整复制模板的 `<script>` 块（Presentation 类），确保翻页正常
- 报纸风保留 12 列 grid 布局和 `.reveal` 动画系统
- 赛博朋克风保留扫描线背景和发光效果
- 每页一个 `<section class="slide">`，第一页加 `class="slide active"`
- **每页幻灯片必须添加时间范围属性**：`data-time-start="MM:SS"` 和 `data-time-end="MM:SS"`
- 页脚标注页码为 `当前页 / 总页数`，**并在页码旁显示该页时间范围**（如 `00:12 – 01:33`）
- 不要编造原文没有的数据、人名、公司名

**时间范围 CSS 样式**：在 footer 中添加 `.slide-time` 样式，显示时间区间：

```css
.slide-time {
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--muted);
  letter-spacing: 1px;
}
```

**报纸风特殊规则：**
- 每页结构为 `<section class="slide" data-time-start="..." data-time-end="..."><div class="grid">...</div><div class="footer">...</div></section>`
- grid 内用 `.col-X` 控制列宽
- 给关键元素加 `.reveal .d1` 到 `.d5` 实现逐行动画
- footer 左侧写内容来源/关键词，中间显示时间范围（`.slide-time`），右侧写页码

**赛博朋克风特殊规则：**
- 数据展示优先用 `.panel` 包裹 `.stat` 结构
- 中文正文用 `.subtitle` 样式
- 保持整体风格简洁有力
- 每页 slide 同样需要 `data-time-start` / `data-time-end` 属性，页脚或底部信息栏显示时间范围

**JavaScript 时间范围支持**：在 Presentation 类中增加获取当前页时间范围的方法：

```js
// 在 Presentation 类中增加：
getCurrentTimeRange() {
  const slide = this.slides[this.current];
  return {
    start: slide.dataset.timeStart,
    end: slide.dataset.timeEnd
  };
}
```

并在翻页时更新 URL hash，hash 中包含时间信息便于外部（如 OBS）读取当前页对应的时间段。

### 6. 自检（生成后必做）

- [ ] HTML 可在浏览器直接打开，翻页正常（键盘 + 点击）
- [ ] 窗口缩放时内容等比例适配
- [ ] 所有数字与原字幕一致
- [ ] 页码标注正确
- [ ] **每页时间范围正确**：与 SRT 字幕时间码一致，页脚显示时间区间
- [ ] **data-time-start / data-time-end 属性**存在于每个 slide 元素上
- [ ] 视觉风格与原始模板一致（CSS 完整复制）

## 与知识主播工作流

- 输入常为口播视频的 .srt 字幕文件
- 目标是将字幕内容可视化为 PPT 风格网页，方便视频配图或独立演示
- 生成后可直接用浏览器打开，截图作为视频画面，或嵌入 OBS 作为直播素材
- **时间范围的作用**：
  - 视频剪辑时，根据每页时间范围精确定位需要配图的画面段落
  - OBS 直播时，可通过 `getCurrentTimeRange()` 获取当前页对应的时间段，同步显示进度
  - 支持通过 URL hash（如 `#slide-3`）直接跳转到特定时间段对应的幻灯片

## 示例 invocation

用户：「把 斯坦福重磅实证报告：AI怎么落地？_zh-cn.srt 做成报纸风的 PPT HTML」
→ 读取 SRT → 语义分组（约 12 页）→ 生成报纸风 HTML → 保存并告知路径。

更完整示例见 [examples.md](examples.md)。

## 模板 CSS 快查（报纸风关键变量）

```css
--bg: #f4efe6;
--ink: #191919;
--accent: #c62828;
--muted: #7c7468;
--line: #d7d0c2;
--display: 92px;   /* 封面大标题 */
--headline: 56px;  /* 章节标题 */
--title: 34px;     /* 中标题 */
```

## 赛博朋克风关键变量（速查）

```css
--bg: #060816;        /* 主背景：深邃蓝黑 */
--cyan: #00e5ff;      /* 霓虹青 */
--pink: #ff2ea6;      /* 霓虹粉 */
--purple: #8b5cf6;    /* 紫色 */
--gold: #f0a500;      /* 金色 */
--ink: #d8e7ff;       /* 主文字 */
--muted: #6e7ea8;     /* 次要文字 */
```

> **详细组件说明见上方「赛博朋克风」章节**
