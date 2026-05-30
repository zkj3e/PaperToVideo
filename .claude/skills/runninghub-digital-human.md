---
name: runninghub-digital-human
description: 调用 RunningHub 数字人口播 API，提交任务后轮询等待完成，返回视频/音频/字幕结果
---

# runninghub-digital-human

使用 RunningHub 数字人口播工作流生成 AI 数字人视频，支持文本配音、视频合成、实时进度显示。

## 前置要求

1. **API Key**: 需要有效的 RunningHub API Key
2. **配置文件**: `scripts/.runninghub_config.json`

配置文件格式：
```json
{
    "api_key": "your_api_key_here",
    "workflow_id": "2059642920948559873",
    "query_url": "https://www.runninghub.ai/openapi/v2/query",
    "poll_interval": 15,
    "max_wait": 600,
    "output": "digital_human_result.json"
}
```

## 输入

| 参数 | 说明 | 必填 |
|------|------|------|
| --text / -t | 口播文本内容 | 是（与 --input 二选一） |
| --input / -i | 文本文件路径 | 是（与 --text 二选一） |
| --duration / -d | 视频时长 (mm:ss)，默认 00:05 | 否 |
| --image | 人物形象图片 ID 或路径 | 否 |
| --output / -o | 结果输出文件路径 | 否，默认 digital_human_result.json |
| --poll-interval | 轮询间隔（秒），默认 15 | 否 |
| --max-wait | 最大等待时间（秒），默认 600 | 否 |
| --config / -c | 配置文件路径 | 否 |

## 执行命令

```bash
# 基本用法 - 直接输入文本
python3 scripts/runninghub_digital_human_complete.py --text "你好，欢迎观看" --duration "00:05"

# 从文件读取文本
python3 scripts/runninghub_digital_human_complete.py --input "script.txt" --duration "00:30"

# 指定人物形象
python3 scripts/runninghub_digital_human_complete.py --text "口播文本" --image "image_id.png" --duration "00:10"

# 自定义轮询间隔
python3 scripts/runninghub_digital_human_complete.py --text "文本" --duration "00:05" --poll-interval 20 --max-wait 900
```

## 流水线总览

```
┌─────────────┐     ┌──────────────────────┐     ┌─────────────┐     ┌──────────┐
│  提交任务    │ ──▶ │  轮询查询状态 (每15秒)  │ ──▶ │  任务完成   │ ──▶ │ 返回结果  │
│  /run/ai-app│     │  /query               │     │  SUCCESS    │     │ mp4/flac │
└─────────────┘     └──────────────────────┘     └─────────────┘     └──────────┘
```

## 输出结果

任务完成后返回 JSON，包含：

| 字段 | 说明 |
|------|------|
| taskId | 任务 ID |
| status | 任务状态 (SUCCESS / FAILED / RUNNING) |
| results | 生成结果列表 |
| results[].url | 文件下载 URL（有效期 24 小时） |
| results[].outputType | 文件类型 (mp4/flac/txt) |
| usage | 消耗信息 |
| usage.consumeCoins | 消耗 RH 币数量 |
| usage.taskCostTime | 任务耗时（秒） |

## 进度显示示例

```
============================================================
🚀 RunningHub 数字人口播生成器
============================================================
📝 文本长度: 128 字符
⏱️  目标时长: 00:05
============================================================

📤 正在提交任务...
✅ 任务已提交，任务ID: 2060365215668858881
🔄 等待任务完成（轮询间隔: 15秒）...

⠏ [██████████████░░░░░░] 63% | 已用时: 1分32秒 | 预计剩余: 53秒 | 🔥 渲染中...

============================================================
🎉 任务完成!
============================================================
📋 任务ID: 2060365215668858881
⏱️  总耗时: 2分25秒
💰 消耗信息: {"consumeCoins": "39", "taskCostTime": "191"}
🎬 视频地址: https://rh-images-xxx.cos.ap-beijing.myqcloud.com/xxx.mp4
============================================================
```

## 错误处理

| 错误码 | 说明 | 处理方式 |
|--------|------|----------|
| 1001 | Invalid URL | 检查 query_url 配置 |
| 1004 | Task not found | 检查 taskId 是否正确 |
| 805 | 工作流运行失败 | 检查输入参数是否正确 |
| 412 | TOKEN_INVALID | 检查 API Key 是否有效 |

## 注意事项

1. **视频链接有效期**: 生成结果的 URL 有效期仅为 24 小时，请及时下载
2. **轮询频率**: 默认 15 秒轮询一次，减少 API 调用频率
3. **超时设置**: 默认最大等待 600 秒（10 分钟），长视频可适当增加
4. **结果保存**: 任务完成后结果会自动保存到 output 指定的文件