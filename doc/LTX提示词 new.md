# 我的输入

## 1. 参考图片
[在这里上传一张图片,作为人物外貌、服装、场景、光线的参考]

---

## 2. 话术内容(带时间线)

请按以下格式填写:

1
00:00:00,000 --> 00:00:28,100
[这一段说什么]

2
00:00:28,760 --> 00:00:57,980
[这一段说什么]

3
00:00:57,980 --> 00:01:06,860
[这一段说什么]

...

---

## 3. 视频参数

- 总时长:[X 秒]
- FPS:[默认 30]
- 是否后期对口型:[是 / 否]

(如果选"是",输出时弱化嘴部动作描述,方便后期 LatentSync 替换)

---

# 你需要输出的内容

请严格按以下格式输出,并使用代码块包裹,方便直接复制到 LTX / WAN / Kling 等视频模型:

---

## 输出 1:global_prompt

要求:

- 单段连贯英文
- 无任何换行符
- 必须严格基于上传图片描述人物
- 不允许凭空添加图片中不存在的元素
- 包含以下内容:
  - 人物外貌:
    年龄、五官、肤质、妆容、发型
  - 服装与配饰
  - 背景环境(至少4个细节)
  - 光线:
    柔和环形灯、自然瞳孔反光、不过曝、保留皮肤真实阴影
  - 镜头:
    静止机位 + 轻微手持漂移
  - 画质:
    暖色调、浅景深、手机直播质感、9:16

- 整体风格要求:
  - 偏真实真人口播
  - 避免 AI 主播感
  - 避免过度美颜
  - 避免塑料皮肤
  - 避免高曝光直播间感

- 优先使用这些描述词:
  soft balanced warm indoor lighting, reduced brightness, controlled highlights, natural skin texture, realistic skin shading, subtle ring light catchlights, shallow depth of field, realistic smartphone livestream aesthetic

- 避免使用这些描述词:
  bright cinematic lighting, flawless skin, glowing skin, sparkling eyes, overexposed lighting, beauty filter

字段格式:

[global_prompt 输出在这里]

---

## 输出 2:local_prompts

要求:

- 根据话术时间线自动分段
- 每段对应一个时间区间
- 段与段之间使用:
  | 
  分隔(竖线两边保留空格)

- 每段必须包含完整 5 个要素:
  1. 主体动作
  2. 面部表情
  3. 手势
  4. 头部动作
  5. 细节(碎发/眼神/眨眼等)

- 情绪节奏要求:
  - 开场:
    轻微积极、自然交流感
    不要夸张兴奋
  - 中段:
    专业、认真、克制
  - 结尾:
    稳定、自信、有说服力

- 必须避免:
  - exaggerated smile
  - overacting
  - excessive eyebrow movement
  -主播式夸张动作
  - 高频点头
  - 大幅挥手
  - wide mouth opening

- 优先使用这些动作词:
  calm conversational posture, relaxed friendly expression, subtle genuine smile, restrained professional gestures, natural blinking, gentle head movement, attentive eye contact, smooth explanatory hand gestures

- 避免使用这些词:
  excited, enthusiastic, hyper energetic, sparkling eyes, dramatic gesture, speaking animatedly, big smile

- 单段英文
- 不允许内部换行

- 如果"后期对口型 = 是":
  自动将:
  mouth opening wide
  / speaking animatedly

  替换成:

  lips parted
  / expressive but natural face

字段格式:

[段1] | [段2] | [段3] | ...

---

## 输出 3:segment_lengths

要求:

- 根据字幕时间轴自动计算帧数
- 计算公式:
  秒数 × FPS

- 使用英文逗号分隔
- 不允许空格

字段格式:

帧数1,帧数2,帧数3,...

---

## 输出 4:推荐参数

要求:

根据视频类型自动推荐:

- epsilon
  - 连续口播默认:
    0.5
  - 更柔和过渡:
    0.7
  - 强切镜:
    0.001

- 推荐分辨率:
  - 704×1216
  - 或 768×1280

- CFG:
  LTX 2.3 推荐 3.0-3.5

- sampling steps:
  推荐 25-30

字段格式:

epsilon: X
resolution: XXX
CFG: X
sampling_steps: XX

---

## 输出 5:negative_prompt

固定输出以下内容(允许根据场景微调):

worst quality, inconsistent motion, blurry, jittery, distorted face, deformed face, ugly, aged skin, wrinkles, asymmetric eyes, extra fingers, mutated hands, bad anatomy, static image, frozen, oversaturated, cartoon, anime, plastic skin, beauty filter, overexposed face, harsh lighting, blown highlights, exaggerated smile, unnatural facial expression, excessive eyebrow movement, wide mouth opening, motion smear, transition cuts, scene change, text overlay, watermark

---

# 输出前自检清单

在输出前请确认:

- [ ] global_prompt 中所有人物特征都来自参考图片
- [ ] 没有凭空添加图片不存在的元素
- [ ] local_prompts 段数 = 时间线段数
- [ ] segment_lengths 总和 = 总时长 × FPS
- [ ] 每段 local_prompt 都包含完整 5 要素
- [ ] 情绪递进:
      开场 → 讲解 → 收尾
- [ ] 动作变化自然
- [ ] 没有 AI 主播感
- [ ] 没有过曝打光
- [ ] 没有塑料皮肤
- [ ] 全部输出为单段格式
- [ ] 无内部换行(LTX 敏感)