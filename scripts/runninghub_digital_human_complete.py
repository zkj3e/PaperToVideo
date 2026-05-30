#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RunningHub 数字人口播完整流程脚本
包含进度显示、状态更新和时间统计

用法:
    python3 scripts/runninghub_digital_human_complete.py --text "口播文本" --duration "00:05"
    python3 scripts/runninghub_digital_human_complete.py --text "文本" --image "image.png" --duration "00:30"
    python3 scripts/runninghub_digital_human_complete.py --input "script.txt" --duration "00:30"
"""

import argparse
import json
import os
import sys
import time
import requests
import threading
from pathlib import Path
from typing import Optional

DEFAULT_WORKFLOW_ID = "2059642920948559873"
DEFAULT_API_URL = "https://www.runninghub.ai/openapi/v2/run/ai-app/{workflow_id}"
DEFAULT_QUERY_URL = "https://www.runninghub.ai/openapi/v2/query"
DEFAULT_CONFIG_FILE = ".runninghub_config.json"


def load_config(config_path: Optional[str] = None) -> dict:
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
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
    return {}


def merge_config(config: dict, args: argparse.Namespace) -> dict:
    workflow_id = args.workflow_id or config.get("workflow_id", DEFAULT_WORKFLOW_ID)
    api_url = config.get("api_url", DEFAULT_API_URL).format(workflow_id=workflow_id)

    return {
        "api_key": args.api_key or config.get("api_key", "") or os.environ.get("RUNNINGHUB_API_KEY", ""),
        "api_url": args.api_url or api_url,
        "query_url": args.query_url or config.get("query_url", DEFAULT_QUERY_URL),
        "workflow_id": workflow_id,
        "instance_type": args.instance_type or config.get("instance_type", "plus"),
        "use_personal_queue": args.use_personal_queue or config.get("use_personal_queue", True),
        "image": args.image or config.get("image", ""),
        "poll_interval": args.poll_interval or config.get("poll_interval", 15),
        "max_wait": args.max_wait or config.get("max_wait", 600),
        "output": args.output or config.get("output", "digital_human_result.json"),
    }


class ProgressDisplay:
    def __init__(self, max_wait: int):
        self.max_wait = max_wait
        self.start_time = time.time()
        self.current_status = ""
        self.progress = 0
        self.running = True
        self.lock = threading.Lock()

    def update(self, status: str, progress: int = None):
        with self.lock:
            self.current_status = status
            if progress is not None:
                self.progress = progress

    def get_elapsed_time(self) -> float:
        return time.time() - self.start_time

    def format_time(self, seconds: float) -> str:
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}分{secs}秒"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}小时{mins}分"

    def display_loop(self):
        while self.running:
            elapsed = self.get_elapsed_time()
            elapsed_str = self.format_time(elapsed)

            if self.progress > 0:
                progress_bar = "█" * (self.progress // 5) + "░" * (20 - self.progress // 5)
                print(f"\r[{progress_bar}] {self.progress}% | 已用时: {elapsed_str} | {self.current_status}", end="", flush=True)
            else:
                print(f"\r等待中... | 已用时: {elapsed_str} | {self.current_status}", end="", flush=True)

            time.sleep(0.5)

    def stop(self):
        self.running = False


class RunningHubComplete:
    def __init__(self, api_url: str, query_url: str, api_key: str,
                 instance_type: str = "default", use_personal_queue: bool = False):
        self.api_url = api_url
        self.query_url = query_url
        self.api_key = api_key
        self.instance_type = instance_type
        self.use_personal_queue = use_personal_queue

    def submit_task(self, text: str, duration: str, image: str = "") -> Optional[str]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        node_info_list = [
            {"nodeId": "195", "fieldName": "text", "fieldValue": text},
            {"nodeId": "41", "fieldName": "end_time", "fieldValue": duration}
        ]

        if image:
            node_info_list.insert(1, {"nodeId": "14", "fieldName": "image", "fieldValue": image})

        payload = {
            "nodeInfoList": node_info_list,
            "instanceType": self.instance_type,
            "usePersonalQueue": str(self.use_personal_queue).lower()
        }

        try:
            response = requests.post(self.api_url, headers=headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0 or "taskId" in result:
                return result.get("taskId") or result.get("data", {}).get("taskId")
            else:
                print(f"\n❌ 任务提交失败: {result.get('msg', '未知错误')}", file=sys.stderr)
                return None
        except requests.exceptions.RequestException as e:
            print(f"\n❌ 网络请求失败: {e}", file=sys.stderr)
            return None

    def query_task(self, task_id: str) -> Optional[dict]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {"taskId": task_id}

        try:
            response = requests.post(self.query_url, headers=headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None

    def wait_for_result(self, task_id: str, poll_interval: int = 3,
                        max_wait: int = 600, output_file: str = None) -> dict:
        progress = ProgressDisplay(max_wait)
        progress_thread = threading.Thread(target=progress.display_loop, daemon=True)
        progress_thread.start()

        start_time = time.time()
        status_history = {}
        check_count = 0

        try:
            while time.time() - start_time < max_wait:
                result = self.query_task(task_id)

                if result:
                    status = result.get("status", "")
                    error_code = result.get("errorCode", "")
                    error_message = result.get("errorMessage", "")
                    check_count += 1

                    if error_code and error_code != "0":
                        print(f"\n\n❌ 查询错误: {error_message} (错误码: {error_code})")
                        print(f"📋 任务ID: {task_id}")
                        progress.stop()
                        return {"status": "ERROR", "errorCode": error_code, "errorMessage": error_message, "taskId": task_id}

                    progress.update(f"状态: {status if status else '处理中'}", min(check_count * 3, 95))

                    if status == "SUCCESS":
                        elapsed = time.time() - start_time
                        progress.update("✅ 任务完成!", 100)

                        print(f"\n\n{'='*60}")
                        print(f"🎉 任务完成!")
                        print(f"{'='*60}")
                        print(f"📋 任务ID: {task_id}")
                        print(f"⏱️  总耗时: {progress.format_time(elapsed)}")
                        print(f"💰 消耗信息: {json.dumps(result.get('usage', {}), ensure_ascii=False, indent=2)}")

                        if result.get("results") and len(result["results"]) > 0:
                            output_url = result["results"][0].get("url", "")
                            print(f"🎬 视频地址: {output_url}")
                            if output_file and output_url:
                                with open(output_file, 'w', encoding='utf-8') as f:
                                    json.dump(result, f, ensure_ascii=False, indent=2)
                                print(f"💾 结果已保存: {output_file}")
                        print(f"{'='*60}\n")

                        return result

                    elif status == "FAILED":
                        elapsed = time.time() - start_time
                        error_msg = result.get("errorMessage", "未知错误")
                        print(f"\n\n{'='*60}")
                        print(f"❌ 任务失败!")
                        print(f"{'='*60}")
                        print(f"📋 任务ID: {task_id}")
                        print(f"⏱️  已用时: {progress.format_time(elapsed)}")
                        print(f"🚫 错误信息: {error_msg}")
                        print(f"{'='*60}\n")
                        return result

                    elif status in ("RUNNING", "QUEUED", "PROCESSING"):
                        if status not in status_history:
                            status_history[status] = time.time()
                        else:
                            status_duration = time.time() - status_history[status]
                            if status == "RUNNING" and status_duration > 60:
                                progress.update(f"🔥 渲染中... ({progress.format_time(status_duration)})")

                time.sleep(poll_interval)

            print(f"\n\n⚠️ 任务超时（等待 {max_wait} 秒）")
            return {"status": "TIMEOUT", "taskId": task_id}

        finally:
            progress.stop()
            progress_thread.join(timeout=1)


def main():
    parser = argparse.ArgumentParser(description="RunningHub 数字人口播完整流程")
    parser.add_argument("--text", "-t", type=str, help="口播文本")
    parser.add_argument("--input", "-i", type=str, help="输入文件路径（文本文件）")
    parser.add_argument("--output", "-o", type=str, default="digital_human_result.json", help="输出文件路径")
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
    parser.add_argument("--poll-interval", type=int, default=15, help="轮询间隔（秒），默认 15")
    parser.add_argument("--max-wait", type=int, default=600, help="最大等待时间（秒）")

    args = parser.parse_args()

    if not args.text and not args.input:
        parser.print_help()
        print("\n❌ 错误: 必须提供 --text 或 --input 参数")
        sys.exit(1)

    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"❌ 错误: 输入文件不存在: {input_path}", file=sys.stderr)
            sys.exit(1)
        text = input_path.read_text(encoding="utf-8")
    else:
        text = args.text

    text = text.strip()
    if not text:
        print("❌ 错误: 输入文本为空", file=sys.stderr)
        sys.exit(1)

    total_start = time.time()

    print(f"\n{'='*60}")
    print(f"🚀 RunningHub 数字人口播生成器")
    print(f"{'='*60}")
    print(f"📝 文本长度: {len(text)} 字符")
    print(f"⏱️  目标时长: {args.duration}")
    if args.image:
        print(f"🖼️  人物图片: {args.image}")
    print(f"{'='*60}\n")

    config = load_config(args.config) if args.config else load_config()
    cfg = merge_config(config, args)

    if not cfg["api_key"]:
        print("❌ 错误: 未找到 API Key，请通过 --api-key 或配置文件提供", file=sys.stderr)
        sys.exit(1)

    api = RunningHubComplete(
        api_url=cfg["api_url"],
        query_url=cfg["query_url"],
        api_key=cfg["api_key"],
        instance_type=cfg["instance_type"],
        use_personal_queue=cfg["use_personal_queue"]
    )

    print("📤 正在提交任务...")
    task_id = api.submit_task(text, args.duration, cfg["image"])

    if not task_id:
        print("❌ 任务提交失败，请检查配置和网络连接", file=sys.stderr)
        sys.exit(1)

    print(f"✅ 任务已提交，任务ID: {task_id}")
    print(f"🔄 等待任务完成（轮询间隔: {cfg['poll_interval']}秒）...\n")

    result = api.wait_for_result(
        task_id,
        poll_interval=cfg["poll_interval"],
        max_wait=cfg["max_wait"],
        output_file=cfg["output"]
    )

    total_time = time.time() - total_start
    print(f"📊 总耗时: {total_time:.1f} 秒")


if __name__ == "__main__":
    main()