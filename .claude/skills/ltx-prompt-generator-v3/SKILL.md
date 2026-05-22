---
name: ltx-prompt-generator-v3
description: Use when generating LTX 2.3 / ComfyUI image-to-video prompts from a reference image, full spoken text, audio duration, segment count, FPS, or lip-sync requirements for Chinese talking-head videos.
---

# LTX Prompt Generator V3

## Overview

Generate copy-ready prompts for LTX 2.3 / WAN / Kling talking-head image-to-video workflows. The input is a reference image, full Chinese spoken text, total voice length, desired segment count, FPS, and whether lip-sync will be replaced later.

The output must be practical for ComfyUI Prompt Relay Encode: `global_prompt`, `local_prompts`, `segment_lengths`, recommended parameters, and `negative_prompt`.

## Required Inputs

Ask for any missing required input before generating:

- Reference image: the only source for person, clothing, background, and lighting.
- Full spoken text: the complete narration or script.
- Audio duration: accepts `00:01:06.860`, `01:06.860`, or `66.86 秒`.
- Segment count: the exact number of local prompt segments to generate.
- FPS: default to `30` if omitted.
- Post lip-sync: `是` or `否`; default to `否` if omitted.

## Core Rules

- Describe the person, outfit, background, and lighting strictly from the reference image. Do not invent unseen features, props, or scene details.
- Split the full spoken text into exactly the requested number of segments.
- Prefer semantic boundaries: paragraphs, punctuation, transitions, argument structure, and sentence endings.
- Do not cut a sentence awkwardly just to equalize length.
- Estimate segment duration from text proportion; if segments are similar length, distribute duration evenly.
- Compute each segment frame count as `segment_seconds * FPS`, rounded to integers.
- Ensure `segment_lengths` count equals the requested segment count.
- Ensure total segment frames approximately equal `audio_duration_seconds * FPS`; put any rounding correction into the final segment.
- Keep `global_prompt` and every `local_prompt` as single-line English.
- Do not repeat Chinese narration inside `local_prompts`; describe motion, expression, gesture, head movement, and continuity only.

## Duration Parsing

- `HH:MM:SS.mmm`: `hours * 3600 + minutes * 60 + seconds`.
- `MM:SS.mmm`: `minutes * 60 + seconds`.
- `66.86 秒`: `66.86`.
- Total frames: `round(total_seconds * FPS)`.

Example: `66.86 秒`, `FPS 30`, `3` segments means total frames are `round(66.86 * 30) = 2006`. If evenly distributed, output `669,669,668`.

## Text Segmentation

Use the spoken text to create a short Chinese segmentation preview before the final prompts:

```text
1. [核心意思] / [估算时长] / [估算帧数]
2. [核心意思] / [估算时长] / [估算帧数]
3. [核心意思] / [估算时长] / [估算帧数]
```

For more than 4 segments, map the emotional rhythm as:

```text
开场 → 铺垫 → 解释 → 转折 → 总结
```

Keep movement changes small and continuous across all segments.

## global_prompt Requirements

The `global_prompt` must be a single continuous English paragraph with no line breaks. Include:

- Age range, facial features, skin texture, makeup, hairstyle.
- Clothing and visible accessories.
- At least 4 real background details from the image.
- Lighting: soft ring light or soft balanced warm indoor lighting, natural pupil catchlights, reduced brightness, controlled highlights, realistic skin shading.
- Camera: locked-off camera with slight handheld drift.
- Quality: warm tone, shallow depth of field, realistic smartphone livestream aesthetic, vertical 9:16.

Prefer these phrases:

```text
soft balanced warm indoor lighting, reduced brightness, controlled highlights, natural skin texture, realistic skin shading, subtle ring light catchlights, shallow depth of field, realistic smartphone livestream aesthetic
```

Avoid these phrases:

```text
bright cinematic lighting, flawless skin, glowing skin, sparkling eyes, overexposed lighting, beauty filter
```

## local_prompts Requirements

Generate exactly one English single-line local prompt per segment, joined by ` | `.

Each segment must include all 5 elements:

- Body action.
- Facial expression.
- Hand gesture.
- Head movement.
- Fine details such as blinking, eye contact, loose hair, shoulder movement, or small posture changes.

Use restrained talking-head motion:

- Opening: calm conversational posture, lightly positive, natural communication.
- Explanation: professional, focused, restrained gestures.
- Turning point: more attentive gaze, slightly tighter expression, fewer gestures.
- Closing: steady, confident, persuasive, movements settle.

Prefer these phrases:

```text
calm conversational posture, relaxed friendly expression, subtle genuine smile, restrained professional gestures, natural blinking, gentle head movement, attentive eye contact, smooth explanatory hand gestures, subtle shoulder movement, steady gaze
```

Avoid these phrases and behaviors:

```text
excited, enthusiastic, hyper energetic, sparkling eyes, dramatic gesture, speaking animatedly, big smile, exaggerated smile, overacting, excessive eyebrow movement, wide mouth opening, sudden camera movement, scene change
```

If post lip-sync is `是`, weaken mouth descriptions:

- Replace `mouth opening wide` with `lips parted`.
- Replace `speaking animatedly` with `expressive but natural face`.
- Replace `exaggerated lip movement` with `subtle natural mouth movement`.

## Output Format

Always return a single fenced code block in this exact structure:

```text
## 输出 1:global_prompt
[single-line English global prompt]

---

## 输出 2:文本分段说明
1. [核心意思] / [估算时长] / [估算帧数]
2. [核心意思] / [估算时长] / [估算帧数]
3. [核心意思] / [估算时长] / [估算帧数]

---

## 输出 3:local_prompts
[segment 1 English motion prompt] | [segment 2 English motion prompt] | [segment 3 English motion prompt]

---

## 输出 4:segment_lengths
帧数1,帧数2,帧数3

---

## 输出 5:推荐参数
epsilon: 0.5
resolution: 704×1216
CFG: 3.2
sampling_steps: 28

---

## 输出 6:negative_prompt
worst quality, inconsistent motion, blurry, jittery, distorted face, deformed face, ugly, aged skin, wrinkles, asymmetric eyes, extra fingers, mutated hands, bad anatomy, static image, frozen, oversaturated, cartoon, anime, plastic skin, beauty filter, overexposed face, harsh lighting, blown highlights, exaggerated smile, unnatural facial expression, excessive eyebrow movement, wide mouth opening, motion smear, transition cuts, scene change, sudden camera movement, text overlay, watermark
```

## Recommended Parameters

- `epsilon: 0.5` for continuous talking-head videos.
- `epsilon: 0.7` for softer transitions.
- `epsilon: 0.001` only for hard cuts.
- `resolution: 704×1216` by default, or `768×1280` if the workflow can handle it.
- `CFG: 3.0-3.5`, usually `3.2`.
- `sampling_steps: 25-30`, usually `28`.

## Final Checklist

Before answering, verify:

- Reference-image details are not invented.
- Text was split into exactly the requested segment count.
- `local_prompts` count equals segment count.
- `segment_lengths` count equals segment count.
- Segment frame total matches total audio frames after rounding correction.
- Each local prompt contains body action, expression, gesture, head movement, and fine details.
- Movement is natural and restrained, with no AI-anchor exaggeration.
- Lip motion is weakened if post lip-sync is enabled.
- `local_prompts` are single-line and separated only by ` | `.
