#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RunningHub 任务取消脚本
通过 taskid 显示如何取消任务

用法:
    python3 scripts/runninghub_cancel_task.py <taskid>
    python3 scripts/runninghub_cancel_task.py --task-id <taskid>
"""

import argparse
import sys
import json
import requests
from pathlib import Path

DEFAULT_API_URL = "https://www.runninghub.ai/openapi/v2/run/ai-app/{workflow_id}"
DEFAULT_QUERY_URL = "https://www.runninghub.ai/openapi/v2/query"
DEFAULT_CONFIG_FILE = ".runninghub_config.json"


def load_config():
    search_paths = [
        Path.cwd() / DEFAULT_CONFIG_FILE,
        Path(__file__).parent / DEFAULT_CONFIG_FILE,
    ]
    for path in search_paths:
        if path.exists() and path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
    return {}


def query_task(api_key: str, query_url: str, task_id: str) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {"taskId": task_id}
    try:
        response = requests.post(query_url, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="RunningHub 任务取消工具")
    parser.add_argument("task_id", type=str, nargs="?", help="任务 ID")
    parser.add_argument("--task-id", type=str, dest="task_id_flag", default="", help="任务 ID")
    args = parser.parse_args()

    task_id = args.task_id or args.task_id_flag
    if not task_id:
        parser.print_help()
        print("\n❌ 错误: 必须提供 taskid")
        sys.exit(1)

    config = load_config()
    api_key = config.get("api_key", "")
    query_url = config.get("query_url", DEFAULT_QUERY_URL)

    if not api_key:
        print("\n🛑 取消任务方法:")
        print(f"   1. 打开 https://www.runninghub.ai/call-api/bill-task")
        print(f"   2. 找到任务 ID: {task_id}")
        print(f"   3. 点击停止/取消按钮")
        sys.exit(0)

    # 查询任务状态
    result = query_task(api_key, query_url, task_id)
    status = result.get("status", "UNKNOWN")
    error_msg = result.get("errorMessage", "")

    print(f"\n{'='*60}")
    print(f"🔍 任务状态查询")
    print(f"{'='*60}")
    print(f"📋 任务ID: {task_id}")
    print(f"📊 状态: {status}")
    if error_msg:
        print(f"🚫 错误: {error_msg}")
    print(f"{'='*60}")

    if status in ("RUNNING", "QUEUED", "PROCESSING"):
        print(f"\n🛑 取消任务方法:")
        print(f"   1. 打开 https://www.runninghub.ai/call-api/bill-task")
        print(f"   2. 找到任务 ID: {task_id}")
        print(f"   3. 点击停止/取消按钮")
    elif status == "SUCCESS":
        print(f"\n✅ 任务已完成，无需取消")
    elif status == "FAILED":
        print(f"\n⚠️ 任务已失败，无需取消")
    elif status == "UNKNOWN":
        print(f"\n⚠️ 无法查询任务状态")
        print(f"💡 请手动在 https://www.runninghub.ai/call-api/bill-task 查看")
    else:
        print(f"\n💡 任务状态: {status}，请在控制台查看是否可以取消")


if __name__ == "__main__":
    main()
