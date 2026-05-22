#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 .srt 字幕转为纯文本（去掉序号与时间轴，只保留正文）。

用法：
  python3 scripts/srt_to_text.py 字幕.srt
  python3 scripts/srt_to_text.py 字幕.srt -o 正文.txt
  python3 scripts/srt_to_text.py 字幕.srt --lines          # 每条字幕一行，无空行
  python3 scripts/srt_to_text.py 字幕.srt --join           # 全部拼成一段，不换行

依赖：Python 3.9+ 标准库。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable


TIMECODE_LINE = re.compile(
    r"^\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*$"
)


def _normalize_text(lines: Iterable[str]) -> str:
    parts: list[str] = []
    for line in lines:
        t = line.strip()
        if not t:
            continue
        t = re.sub(r"<[^>]+>", "", t)
        parts.append(t)
    return "\n".join(parts).strip()


def parse_srt_texts(content: str) -> list[str]:
    content = content.lstrip("\ufeff")
    blocks = re.split(r"\n\s*\n+", content.strip())
    texts: list[str] = []

    for block in blocks:
        lines = [ln.rstrip("\r") for ln in block.splitlines()]
        lines = [ln for ln in lines if ln.strip()]
        if not lines:
            continue

        time_line_at = 0
        if not TIMECODE_LINE.match(lines[0]):
            time_line_at = 1

        if time_line_at >= len(lines):
            continue
        if not TIMECODE_LINE.match(lines[time_line_at]):
            continue

        text = _normalize_text(lines[time_line_at + 1 :])
        if text:
            texts.append(text)

    return texts


def texts_to_plain(texts: list[str], *, lines: bool, join: bool) -> str:
    if not texts:
        return ""
    if join:
        return "".join(texts).rstrip() + "\n"
    if lines:
        return "\n".join(texts).rstrip() + "\n"
    return "\n\n".join(texts).rstrip() + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="SRT → 纯文本")
    parser.add_argument("srt_path", type=Path, help="输入 .srt 文件")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="输出 .txt（默认：与字幕同目录 <basename>.txt）",
    )
    parser.add_argument(
        "--lines",
        action="store_true",
        help="每条字幕一行，段间无空行（默认：段间空一行）",
    )
    parser.add_argument(
        "--join",
        action="store_true",
        help="全部拼成一段连续正文，不换行",
    )
    args = parser.parse_args(argv)

    srt_path = args.srt_path.expanduser().resolve()
    if not srt_path.is_file():
        print(f"找不到字幕文件: {srt_path}", file=sys.stderr)
        return 2

    texts = parse_srt_texts(srt_path.read_text(encoding="utf-8", errors="replace"))
    if not texts:
        print("未能解析出任何字幕正文。", file=sys.stderr)
        return 3

    out_path = (
        args.output.expanduser().resolve()
        if args.output
        else srt_path.with_suffix(".txt")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        texts_to_plain(texts, lines=args.lines, join=args.join),
        encoding="utf-8",
    )

    print(f"{len(texts)} 条字幕 → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
