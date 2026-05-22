#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 .srt 生成纯文本：每条字幕一段，段之间空一行。

用法：
  python3 scripts/srt_to_qwentts_prompt.py 字幕.srt
  python3 scripts/srt_to_qwentts_prompt.py 字幕.srt -o 朗读稿.txt

依赖：Python 3.9+ 标准库。
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TIMECODE_LINE = re.compile(
    r"^\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*$"
)


@dataclass(frozen=True)
class Cue:
    index: int
    start_sec: float
    text: str


def _tc_parts_to_sec(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def _normalize_text(lines: Iterable[str]) -> str:
    parts = []
    for line in lines:
        t = line.strip()
        if not t:
            continue
        t = re.sub(r"<[^>]+>", "", t)
        parts.append(t)
    return " ".join(parts).strip()


def parse_srt(content: str) -> list[Cue]:
    content = content.lstrip("\ufeff")
    blocks = re.split(r"\n\s*\n+", content.strip())
    cues: list[Cue] = []

    for block in blocks:
        lines = [ln.rstrip("\r") for ln in block.splitlines()]
        lines = [ln for ln in lines if ln.strip() != ""]
        if not lines:
            continue

        idx = 0
        time_line_at = 0
        if TIMECODE_LINE.match(lines[0]):
            time_line_at = 0
        else:
            try:
                idx = int(lines[0].strip())
            except ValueError:
                idx = len(cues) + 1
            time_line_at = 1

        if time_line_at >= len(lines):
            continue
        m = TIMECODE_LINE.match(lines[time_line_at])
        if not m:
            continue

        start_sec = _tc_parts_to_sec(*m.groups()[0:4])
        body_lines = lines[time_line_at + 1 :]
        text = _normalize_text(body_lines)
        if not text:
            continue

        cues.append(Cue(index=idx or len(cues) + 1, start_sec=start_sec, text=text))

    cues.sort(key=lambda c: (c.start_sec, c.index))
    return cues


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="SRT → 分段纯文本（仅正文）")
    parser.add_argument("srt_path", type=Path, help="输入 .srt")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="输出 .txt（默认：与字幕同目录 <basename>_qwentts.txt）",
    )
    args = parser.parse_args(argv)

    srt_path = args.srt_path.expanduser().resolve()
    if not srt_path.is_file():
        print(f"找不到字幕文件: {srt_path}", file=sys.stderr)
        return 2

    cues = parse_srt(srt_path.read_text(encoding="utf-8", errors="replace"))
    if not cues:
        print("未能解析出任何字幕块。", file=sys.stderr)
        return 3

    stem = srt_path.stem
    out = args.output.expanduser().resolve() if args.output else (srt_path.parent / f"{stem}_qwentts.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    paragraphs = [c.text.strip() for c in cues if c.text.strip()]
    out.write_text("\n\n".join(paragraphs).rstrip() + "\n", encoding="utf-8")

    print(f"{len(cues)} 段 → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
