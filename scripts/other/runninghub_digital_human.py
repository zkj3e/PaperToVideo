#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RunningHub 数字人口播 API 调用脚本

用法:
    python3 scripts/runninghub_digital_human.py --text "口播文本" --duration "00:05"

    # 指定人物形象图片
    python3 scripts/runninghub_digital_human.py --text "文本" --image "image.png" --duration "00:05"

    # 使用配置文件
    python3 scripts/runninghub_digital_human.py --text "文本" --duration "00:05" --poll

配置文件格式 (JSON):
{
    "api_key": "your_api_key_here",
    "api_url": "https://www.runninghub.ai/call-api/api-detail/{workflow_id}",
    "query_url": "https://www.runninghub.ai/call-api/task/query",
    "workflow_id": "your_workflow_id",
    "instance_type": "default",
    "use_personal_queue": false,
    "image": "人物形象图片路径或ID",
    "poll_interval": 5,
    "max_wait": 300,
    "output": "result.json"
}

配置文件查找顺序:
1. --config 参数指定的路径
2. 当前目录下的 .runninghub_config.json
3. 脚本所在目录下的 .runninghub_config.json
4. 用户主目录下的 .runninghub_config.json

配置优先级: 命令行参数 > 配置文件 > 环境变量 > 默认值

依赖: requests (pip install requests)
"""

import argparse
import json
import os
import sys
import time
import requests
from pathlib import Path
from typing import Optional


DEFAULT_WORKFLOW_ID = "2059642920948559873"
DEFAULT_API_URL = "https://www.runninghub.ai/openapi/v2/run/ai-app/{workflow_id}"
DEFAULT_QUERY_URL = "https://www.runninghub.ai/openapi/v2/run/query"
DEFAULT_CONFIG_FILE = ".runninghub_config.json"


def load_config(config_path: Optional[str] = None) -> dict:
    """加载配置文件，支持 JSON 格式"""
    search_paths = []
    if config_path:
        search_paths.append(Path(config_path))
    search_paths.extend([
        Path.cwd() / DEFAULT_CONFIG_FILE,
        Path(__file__).parent / DEFAULT_CONFIG_FILE,
        Path.home() / DEFAULT_CONFIG_FILE,
    ])

    for path in search_paths:
        if path.exists() and path.is_file():
            try:
                config = json.loads(path.read_text(encoding="utf-8"))
                print(f"已加载配置文件: {path}")
                return config
            except json.JSONDecodeError as e:
                print(f"配置文件解析失败 {path}: {e}", file=sys.stderr)

    return {}


def merge_config(config: dict, args: argparse.Namespace) -> dict:
    """合并配置：命令行参数 > 配置文件 > 默认值"""
    workflow_id = args.workflow_id or config.get("workflow_id", DEFAULT_WORKFLOW_ID)
    api_url = config.get("api_url", DEFAULT_API_URL).format(workflow_id=workflow_id)
    query_url = config.get("query_url", DEFAULT_QUERY_URL)

    return {
        "api_key": args.api_key or config.get("api_key", "") or os.environ.get("RUNNINGHUB_API_KEY", ""),
        "api_url": args.api_url or api_url,
        "query_url": args.query_url or config.get("query_url", DEFAULT_QUERY_URL),
        "workflow_id": workflow_id,
        "instance_type": args.instance_type or config.get("instance_type", "default"),
        "use_personal_queue": args.use_personal_queue or config.get("use_personal_queue", False),
        "image": args.image or config.get("image", ""),
        "poll": args.poll or config.get("poll", True),
        "poll_interval": args.poll_interval or config.get("poll_interval", 5),
        "max_wait": args.max_wait or config.get("max_wait", 300),
        "output": args.output or config.get("output", "digital_human_result.json"),
    }


class RunningHubAPI:
    def __init__(self, api_url: str, query_url: str, api_key: str, instance_type: str = "default",
                 use_personal_queue: bool = False):
        self.api_url = api_url
        self.query_url = query_url
        self.api_key = api_key
        self.instance_type = instance_type
        self.use_personal_queue = use_personal_queue

    def call_workflow(self, text: str, duration: str, image: str = "") -> dict:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        node_info_list = [
            {
                "nodeId": "195",
                "fieldName": "text",
                "fieldValue": text,
                "description": "Spoken script"
            },
            {
                "nodeId": "41",
                "fieldName": "end_time",
                "fieldValue": duration,
                "description": "Video duration (mm:ss)"
            }
        ]

        if image:
            node_info_list.insert(1, {
                "nodeId": "14",
                "fieldName": "image",
                "fieldValue": image,
                "description": "Host image"
            })

        payload = {
            "nodeInfoList": node_info_list,
            "instanceType": self.instance_type,
            "usePersonalQueue": str(self.use_personal_queue).lower()
        }

        print(f"请求 URL: {self.api_url}")
        print(f"请求 Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")

        response = requests.post(
            self.api_url,
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text[:500] if response.text else '(empty)'}")

        try:
            return response.json()
        except json.JSONDecodeError:
            return {"error": "非 JSON 响应", "text": response.text}

    def query_task(self, task_id: str) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {"taskId": task_id}

        response = requests.post(
            self.query_url,
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def wait_for_result(self, task_id: str, poll_interval: int = 5, max_wait: int = 300) -> dict:
        start_time = time.time()
        while time.time() - start_time < max_wait:
            result = self.query_task(task_id)
            status = result.get("status")

            print(f"[{int(time.time() - start_time)}s] 状态: {status}")

            if status == "SUCCESS":
                print(f"任务完成，耗时 {time.time() - start_time:.1f} 秒")
                return result
            elif status in ("RUNNING", "QUEUED", "PROCESSING"):
                time.sleep(poll_interval)
            else:
                error_msg = result.get("errorMessage", "未知错误")
                raise RuntimeError(f"任务失败: {error_msg}")

        raise TimeoutError(f"任务超时（等待 {max_wait} 秒）")


def main():
    parser = argparse.ArgumentParser(description="RunningHub 数字人口播 API 调用")
    parser.add_argument("--text", "-t", type=str, help="口播文本")
    parser.add_argument("--input", "-i", type=str, help="输入文件路径（文本文件）")
    parser.add_argument("--output", "-o", type=str, default="", help="输出文件路径")
    parser.add_argument("--duration", "-d", type=str, default="00:05", help="视频时长 (mm:ss)，默认 00:05")
    parser.add_argument("--image", type=str, default="", help="人物形象图片路径或 ID")
    parser.add_argument("--workflow-id", "-w", type=str, default="", help="RunningHub 工作流 ID")
    parser.add_argument("--api-key", "-k", type=str, default="", help="RunningHub API Key")
    parser.add_argument("--api-url", type=str, default="", help="API 调用 URL")
    parser.add_argument("--query-url", type=str, default="", help="任务查询 URL")
    parser.add_argument("--instance-type", type=str, default="", choices=["default", "plus"],
                        help="实例类型: default (24G) 或 plus (48G)")
    parser.add_argument("--use-personal-queue", action="store_true", help="使用个人独占队列")
    parser.add_argument("--config", "-c", type=str, default="", help="配置文件路径")
    parser.add_argument("--poll", action="store_true", default=None, help="轮询等待任务完成")
    parser.add_argument("--no-poll", action="store_true", help="不轮询，直接返回任务 ID")
    parser.add_argument("--poll-interval", type=int, default=0, help="轮询间隔（秒）")
    parser.add_argument("--max-wait", type=int, default=0, help="最大等待时间（秒）")

    args = parser.parse_args()

    if not args.text and not args.input:
        parser.error("必须提供 --text 或 --input 参数")

    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"错误: 输入文件不存在: {input_path}", file=sys.stderr)
            sys.exit(1)
        text = input_path.read_text(encoding="utf-8")
    else:
        text = args.text

    text = text.strip()
    if not text:
        print("错误: 输入文本为空", file=sys.stderr)
        sys.exit(1)

    config = load_config(args.config) if args.config else load_config()
    cfg = merge_config(config, args)

    if cfg["poll"] is None:
        cfg["poll"] = True

    api = RunningHubAPI(
        api_url=cfg["api_url"],
        query_url=cfg["query_url"],
        api_key=cfg["api_key"],
        instance_type=cfg["instance_type"],
        use_personal_queue=cfg["use_personal_queue"]
    )

    print(f"正在调用 RunningHub 工作流: {cfg['workflow_id']}")
    print(f"文本长度: {len(text)} 字符")
    print(f"视频时长: {args.duration}")

    try:
        result = api.call_workflow(text, args.duration, cfg["image"])

        if result.get("error"):
            print(f"请求错误: {result.get('error')}", file=sys.stderr)
            if result.get("text"):
                print(f"响应详情: {result['text']}", file=sys.stderr)
            sys.exit(1)

        task_id = result.get("taskId")
        if not task_id:
            print(f"未获取到任务ID，响应: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
            sys.exit(1)

        print(f"任务提交成功，Task ID: {task_id}")

        if cfg["poll"]:
            print("正在等待任务完成...")
            result = api.wait_for_result(task_id, cfg["poll_interval"], cfg["max_wait"])

        output_path = Path(cfg["output"])
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"结果已保存到: {output_path}")

        if result.get("results") and len(result["results"]) > 0:
            output_url = result["results"][0].get("url", "")
            print(f"输出地址: {output_url}")

        return result

    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
