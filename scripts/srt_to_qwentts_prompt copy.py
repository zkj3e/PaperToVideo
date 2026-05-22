#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 .srt 字幕生成纯文本：每条字幕一段，段间空一行（标准段落分隔）。

典型用法：
  python3 scripts/srt_to_qwentts_prompt.py "字幕.zh-cn.srt"
  python3 scripts/srt_to_qwentts_prompt.py video.srt -o 朗读稿.txt
  python3 scripts/srt_to_qwentts_prompt.py video.srt --with-instruction

依赖：仅 Python 3.9+ 标准库。
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


TIMECODE_LINE = re.compile(
    r"^\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*$"
)

DEFAULT_VOICE_INSTRUCTION_ZH = (
    "语速适中，吐字清晰，语气专业克制，情绪平稳自然，偏知识类口播，避免播音腔与夸张起伏。"
)


@dataclass(frozen=True)
class Cue:
    index: int
    start_sec: float
    end_sec: float
    text: str

    @property
    def duration_sec(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)


def _tc_parts_to_sec(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def _normalize_text(lines: Iterable[str]) -> str:
    parts = []
    for line in lines:
        t = line.strip()
        if not t:
            continue
        # Strip common SRT inline cues like <i>...</i>
        t = re.sub(r"<[^>]+>", "", t)
        parts.append(t)
    return " ".join(parts).strip()


def parse_srt(content: str) -> list[Cue]:
    """解析 SubRip（.srt）内容为有序字幕块列表。"""
    content = content.lstrip("\ufeff")
    blocks = re.split(r"\n\s*\n+", content.strip())
    cues: list[Cue] = []

    for block in blocks:
        lines = [ln.rstrip("\r") for ln in block.splitlines()]
        lines = [ln for ln in lines if ln.strip() != ""]
        if not lines:
            continue

        # 兼容极少数不带序号块的导出：第一行即时间轴
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
        end_sec = _tc_parts_to_sec(*m.groups()[4:8])
        body_lines = lines[time_line_at + 1 :]
        text = _normalize_text(body_lines)
        if not text:
            continue

        cues.append(
            Cue(index=idx or len(cues) + 1, start_sec=start_sec, end_sec=end_sec, text=text)
        )

    cues.sort(key=lambda c: (c.start_sec, c.index))
    return cues


def estimate_max_new_tokens_zh(duration_sec: float, text: str) -> int:
    """
    粗估 max_new_tokens：仅供 ComfyUI 里随手填参时参考（精确值请用节点的 Token Count）。
    """
    # 字符量级启发：中文约 ~0.35 token/字（粗），再给一点裕量；并按时长设下限。
    char_based = int(math.ceil(len(text) * 0.45)) + 64
    time_based = int(math.ceil(duration_sec * 25)) + 128
    raw = max(char_based, time_based, 256)
    return min(raw, 4096)


def format_seconds(sec: float) -> str:
    if sec < 0:
        sec = 0.0
    ms_total = int(round(sec * 1000))
    h = ms_total // 3_600_000
    ms_total %= 3_600_000
    m = ms_total // 60_000
    ms_total %= 60_000
    s = ms_total // 1000
    ms = ms_total % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def emit_plain_paragraphs(
    cues: list[Cue],
    path: Path,
    *,
    leading_instruction: str | None,
) -> None:
    """每条字幕一段纯文本，段落之间一个空行。"""
    paragraphs: list[str] = []
    if leading_instruction and leading_instruction.strip():
        paragraphs.append(leading_instruction.strip())
    paragraphs.extend(c.text.strip() for c in cues if c.text.strip())
    path.write_text("\n\n".join(paragraphs).rstrip() + "\n", encoding="utf-8")


def emit_md(cues: list[Cue], voice_instruction: str, path: Path) -> None:
    lines: list[str] = []
    lines.append("# Qwen3-TTS 提示词（由字幕自动生成）")
    lines.append("")
    lines.append("## global_voice_instruction")
    lines.append("")
    lines.append("```text")
    lines.append(voice_instruction.strip())
    lines.append("```")
    lines.append("")
    lines.append("## segments")
    lines.append("")
    total_sec = cues[-1].end_sec - cues[0].start_sec if cues else 0.0
    lines.append(f"- cues: **{len(cues)}**")
    lines.append(f"- approximate span: **{total_sec:.2f}s**（首条开始 → 末条结束）")
    lines.append("")
    for c in cues:
        hint = estimate_max_new_tokens_zh(c.duration_sec, c.text)
        lines.append(f"### 段 {c.index} · `{format_seconds(c.start_sec)} → {format_seconds(c.end_sec)}` · {c.duration_sec:.2f}s")
        lines.append("")
        lines.append(f"- suggested_max_new_tokens（粗估）: `{hint}`")
        lines.append("")
        lines.append("朗读文案：")
        lines.append("")
        lines.append(c.text)
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def emit_json(cues: list[Cue], voice_instruction: str, path: Path) -> None:
    payload = {
        "global_voice_instruction": voice_instruction.strip(),
        "segment_count": len(cues),
        "segments": [
            {
                **asdict(c),
                "start_tc": format_seconds(c.start_sec),
                "end_tc": format_seconds(c.end_sec),
                "suggested_max_new_tokens": estimate_max_new_tokens_zh(c.duration_sec, c.text),
                # 便于一键复制到「朗读 + 风格」合一的提示框（若节点支持在同一段文本里描述风格）
                "combined_instruction_text": f"{voice_instruction.strip()}\n\n{c.text}".strip(),
            }
            for c in cues
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="SRT → 分段纯文本（每字幕一段）")
    parser.add_argument("srt_path", type=Path, help="输入 .srt 路径")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="输出 .txt 路径（默认：与字幕同目录 <basename>_qwentts.txt）",
    )
    parser.add_argument(
        "--with-instruction",
        action="store_true",
        help="在正文最前面多一段语音风格说明（仍为纯文本）",
    )
    parser.add_argument(
        "--instruction-file",
        type=Path,
        default=None,
        help="配合 --with-instruction：从 UTF-8 文件读取风格说明，优先级高于 --instruction",
    )
    parser.add_argument(
        "--instruction",
        default=DEFAULT_VOICE_INSTRUCTION_ZH,
        help="配合 --with-instruction：风格说明正文（默认内置一段知识口播风格）",
    )
    parser.add_argument(
        "--format",
        choices=("txt", "md", "json", "all"),
        default="txt",
        help="默认仅 txt；需要 md/json 时用 md、json 或 all",
    )
    args = parser.parse_args(argv)

    srt_path = args.srt_path.expanduser().resolve()
    if not srt_path.is_file():
        print(f"找不到字幕文件: {srt_path}", file=sys.stderr)
        return 2

    raw = srt_path.read_text(encoding="utf-8", errors="replace")
    cues = parse_srt(raw)
    if not cues:
        print("未能解析出任何字幕块，请确认为标准 SRT。", file=sys.stderr)
        return 3

    voice_instruction = args.instruction.strip()
    if args.instruction_file is not None:
        p = args.instruction_file.expanduser().resolve()
        voice_instruction = p.read_text(encoding="utf-8", errors="replace").strip()

    stem = srt_path.stem
    txt_path = args.output.expanduser().resolve() if args.output is not None else (srt_path.parent / f"{stem}_qwentts.txt")
    if args.format in ("txt", "all"):
        leading = voice_instruction if args.with_instruction else None
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        emit_plain_paragraphs(cues, txt_path, leading_instruction=leading)

    extras_base = txt_path.parent
    if args.format in ("md", "all"):
        emit_md(cues, voice_instruction, extras_base / f"{stem}_qwentts.md")
    if args.format in ("json", "all"):
        emit_json(cues, voice_instruction, extras_base / f"{stem}_qwentts.json")

    print(f"解析字幕块: {len(cues)}")
    if args.format in ("txt", "all"):
        print(f"输出: {txt_path}")
    if args.format in ("md", "json", "all"):
        print(f"其它输出目录: {extras_base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
