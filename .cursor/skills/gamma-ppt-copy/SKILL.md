---
name: gamma-ppt-copy
description: >-
  Generates Gamma.app-ready presentation copy from source text and a target
  slide count. Outputs markdown with --- card breaks for Paste mode or API
  inputTextBreaks. Use when the user asks for Gamma PPT文案, Gamma slides,
  presentation outline from script, or 知识主播配图幻灯片.
---

# Gamma PPT 文案生成

将口播稿、文章片段或任意文本，结构化为 **Gamma 可直接粘贴/API 调用** 的多页演示文案。

## 输入（向用户确认或从上下文推断）

| 参数 | 必填 | 说明 |
|------|------|------|
| `source_text` | 是 | 原始文本（文件路径、粘贴内容、选区） |
| `num_slides` | 是 | 目标页数 / card 数（正整数，通常 6–15） |
| `title` | 否 | 演示总标题；未给则从正文提炼 |
| `language` | 否 | 默认与原文一致（多为 zh-CN） |
| `audience` | 否 | 如「职场新人」「管理者」；影响措辞力度 |
| `tone` | 否 | 默认：口语化、有观点、适合短视频口播转幻灯 |

若用户只给文本未给页数，**先问页数**再生成；不要擅自猜 10 页。

## 输出

1. **主交付物**：完整 Gamma 文案（纯文本/Markdown），可直接复制到 Gamma「Paste」或作为 API `inputText`。
2. **元信息**（简短，放在文案前或后）：
   - 总标题
   - 实际 card 数（必须等于 `num_slides`）
   - 分隔符数量（`num_slides - 1` 个 `---`）
3. **可选**：同目录保存为 `{标题}-gamma-{N}slides.md`（用户要求保存时再做）

不要输出 Gamma 无法消费的冗长说明；说明与正文分开。

## Gamma 格式契约（必须遵守）

- **分页**：卡片之间用单独一行的 `---`（前后各一空行更清晰）。
- **页数**：`num_slides` 张 card ⇒ 恰好 `num_slides - 1` 个 `---`。
- **每页结构**：
  ```markdown
  # 本页标题（≤14 字，有信息量）

  * 要点 1（一句话，宜带数字或对比）
  * 要点 2
  * 要点 3（每页 2–5 条，单条 ≤40 字为宜）
  ```
- **禁止**：不要把 `---` 写在列表项里；不要一页塞超过 6 条要点；不要保留过长段落（口播长句要拆成要点）。
- **API 对齐**（用户要走 API 时提醒）：
  - `format`: `presentation`
  - `cardSplit`: `inputTextBreaks`
  - `textMode`: `preserve`（保留文案）或 `condense`（原文远长于页数容量时）
  - `numCards` 在 `inputTextBreaks` 下会被忽略，以 `---` 为准

## 生成流程

### 1. 读原文并提炼骨架

- 找出：核心概念、2–4 个关键数据、1 个故事/案例、结论/行动建议。
- 标记可删的重复、过渡句（「比如说」「那么」等口播填充）。

### 2. 按页数分配叙事（默认模板）

按 `num_slides` 选用结构；页数不足时合并相邻段，页数有余时拆数据页或加「小结」页。

| 页序 | 角色 | 内容要点 |
|------|------|----------|
| 1 | 封面 | 主标题 + 1 句副标题/钩子 |
| 2 | 问题/背景 | 为什么现在要讲 |
| 3–4 | 核心概念 + 证据 | 定义、对比、关键数字 |
| 5–6 | 冲击/案例 | 报告数据、个人经历、行业画像 |
| 7–8 | 趋势/警示 | 年轻人、职业结构等 |
| 末页 | 收束 | 怎么办 + 一句态度/金句 |

页数 &lt; 6：合并「背景+概念」「数据+案例」；页数 &gt; 12：增加「分职业清单」「能力清单」等独立页。

### 3. 写每一页

- 标题用结论式，不用「第三部分」这类空标题。
- 数字、比例、人名、机构名从原文**忠实保留**，不编造数据。
- 口播中的英文术语可保留（如 Observed Exposure、high agency），必要时括号中文释义。
- 封面页可只有标题 + 一句副标题，不必强行 3 条要点。

### 4. 自检（生成后必做）

- [ ] `---` 分隔符数量 === `num_slides - 1`
- [ ] 以 `---` 分割后的块数 === `num_slides`
- [ ] 每块以 `#` 标题开头
- [ ] 无单页超过 80 字正文（封面除外）
- [ ] 未引入原文没有的事实或数据

## 与知识主播工作流

- 输入常为 `剧本/**/**-zh-cn.txt` 口播稿：保留观点与数据，**压缩**为幻灯要点，不逐句照搬。
- 生成后用户可在 Gamma 选 Paste → 粘贴全文；或在 Generate 模式把 `numCards` 设为相同页数且 `cardSplit: auto`（但精确分页仍推荐 `---` + Paste/API `inputTextBreaks`）。

## 示例 invocation

用户：「把这段口播做成 8 页 Gamma 文案」  
→ 读取文本 + `num_slides=8` → 输出 7 个 `---` 分隔的 8 页 Markdown。

更完整示例见 [examples.md](examples.md)。

## API 快速参考（可选）

```bash
curl -X POST https://public-api.gamma.app/v1.0/generations \
  -H "X-API-KEY: $GAMMA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputText": "<粘贴生成的全文>",
    "format": "presentation",
    "textMode": "preserve",
    "cardSplit": "inputTextBreaks",
    "title": "<演示标题>"
  }'
```

轮询 `GET /v1.0/generations/{generationId}` 直至 `completed`，从响应取 `gammaUrl`。
