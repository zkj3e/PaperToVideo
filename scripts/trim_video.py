#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将视频裁剪到指定时长（默认从开头截取，流复制不重编码）。

用法：
  python3 scripts/trim_video.py input.mp4
  python3 scripts/trim_video.py input.mp4 -d 26
  python3 scripts/trim_video.py input.mp4 -o output.mp4 -d 26

依赖：系统已安装 ffmpeg、ffprobe（PATH 可找到）。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def probe_duration(path: Path) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    result = subprocess.run(
        [
            ffprobe,
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


def trim_video(input_path: Path, output_path: Path, duration: float) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg，请先安装并加入 PATH")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-i",
        str(input_path),
        "-t",
        str(duration),
        "-c",
        "copy",
        "-avoid_negative_ts",
        "make_zero",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "未知错误").strip()
        raise RuntimeError(f"ffmpeg 处理失败:\n{detail}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="裁剪视频到指定时长")
    parser.add_argument("input", type=Path, help="输入视频文件")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="输出文件（默认：覆盖输入文件）",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=float,
        default=26.0,
        help="保留时长（秒，默认 26）",
    )
    args = parser.parse_args(argv)

    input_path = args.input.expanduser().resolve()
    if not input_path.is_file():
        print(f"找不到视频文件: {input_path}", file=sys.stderr)
        return 2

    if args.duration <= 0:
        print("时长必须大于 0", file=sys.stderr)
        return 2

    output_path = (
        args.output.expanduser().resolve() if args.output else input_path
    )

    before = probe_duration(input_path)
    in_place = input_path == output_path

    try:
        if in_place:
            suffix = input_path.suffix or ".mp4"
            with tempfile.NamedTemporaryFile(
                suffix=suffix,
                dir=input_path.parent,
                delete=False,
            ) as tmp:
                tmp_path = Path(tmp.name)
            try:
                trim_video(input_path, tmp_path, args.duration)
                tmp_path.replace(output_path)
            except Exception:
                tmp_path.unlink(missing_ok=True)
                raise
        else:
            trim_video(input_path, output_path, args.duration)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 3

    after = probe_duration(output_path)
    print(f"输入: {input_path}")
    print(f"输出: {output_path}")
    print(f"目标时长: {args.duration:g}s")
    if before is not None and after is not None:
        print(f"时长 {before:.2f}s → {after:.2f}s")
    else:
        print("完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
