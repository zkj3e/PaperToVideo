#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调整音频语速（不改音调），基于 ffmpeg atempo 滤镜。

用法：
  python3 scripts/adjust_audio_speed.py audio.flac --speed 1.1
  python3 scripts/adjust_audio_speed.py audio.flac --speed 0.9 -o slower.flac
  python3 scripts/adjust_audio_speed.py audio.flac --percent 110

  --speed 1.0  原速
  --speed 1.1  快 10%（时长约为原来的 91%）
  --speed 0.9  慢 10%（时长约为原来的 111%）

依赖：系统已安装 ffmpeg（PATH 可找到）。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def build_atempo_chain(speed: float) -> str:
    if speed <= 0:
        raise ValueError("语速倍率必须大于 0")

    filters: list[str] = []
    remaining = speed

    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0

    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5

    filters.append(f"atempo={remaining:.6f}".rstrip("0").rstrip("."))
    return ",".join(filters)


def default_output_path(input_path: Path, speed: float) -> Path:
    label = f"{speed:.2f}".rstrip("0").rstrip(".")
    return input_path.with_name(f"{input_path.stem}_x{label}{input_path.suffix}")


def probe_duration(path: Path) -> float | None:
    ffmpeg = shutil.which("ffprobe")
    if not ffmpeg:
        return None
    result = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def adjust_speed(input_path: Path, output_path: Path, speed: float) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg，请先安装并加入 PATH")

    filter_chain = build_atempo_chain(speed)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-i",
        str(input_path),
        "-filter:a",
        filter_chain,
        "-vn",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "未知错误").strip()
        raise RuntimeError(f"ffmpeg 处理失败:\n{detail}")


def parse_speed(speed: float | None, percent: float | None) -> float:
    if speed is not None and percent is not None:
        raise ValueError("请只指定 --speed 或 --percent 其中之一")
    if speed is not None:
        return speed
    if percent is not None:
        return percent / 100.0
    raise ValueError("必须指定 --speed 或 --percent")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="调整音频语速（不改音调）")
    parser.add_argument("input", type=Path, help="输入音频文件")
    speed_group = parser.add_mutually_exclusive_group(required=True)
    speed_group.add_argument(
        "--speed",
        type=float,
        help="语速倍率，例如 1.1=快10%%，0.9=慢10%%",
    )
    speed_group.add_argument(
        "--percent",
        type=float,
        help="语速百分比，例如 110=快10%%，90=慢10%%",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="输出文件（默认：<原名>_x<倍率>.<后缀>）",
    )
    args = parser.parse_args(argv)

    input_path = args.input.expanduser().resolve()
    if not input_path.is_file():
        print(f"找不到音频文件: {input_path}", file=sys.stderr)
        return 2

    try:
        speed = parse_speed(args.speed, args.percent)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if speed <= 0:
        print("语速倍率必须大于 0", file=sys.stderr)
        return 2

    out_path = (
        args.output.expanduser().resolve()
        if args.output
        else default_output_path(input_path, speed)
    )

    before = probe_duration(input_path)
    try:
        adjust_speed(input_path, out_path, speed)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 3

    after = probe_duration(out_path)
    print(f"语速 x{speed:g} → {out_path}")
    if before is not None and after is not None:
        print(f"时长 {before:.2f}s → {after:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
