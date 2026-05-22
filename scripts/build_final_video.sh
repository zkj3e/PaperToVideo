#!/usr/bin/env bash
set -euo pipefail

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
TMP="$WORKDIR/.build_final"
SRT="$WORKDIR/语音-flac-encoded.mp3 (3).srt"
AUDIO="$WORKDIR/语音.flac"
INTRO_VID="$WORKDIR/前26s.mp4"
OUT="$WORKDIR/成片.mp4"
MANIFEST="$WORKDIR/ppt_timing_manifest.txt"

rm -rf "$TMP"
mkdir -p "$TMP"

# PPT 时长：严格按 今年的趋势已经打明牌了 时代变太快-gamma-8slides.md
# 正文 8 张卡片顺序 ↔ ppt/1–8.png，时间轴来自 SRT（不整体缩放，仅末页补齐空隙）
DURS=()
while IFS= read -r _dur; do
  DURS+=("$_dur")
done < <(python3 - "$SRT" "$AUDIO" "$INTRO_VID" "$MANIFEST" <<'PY'
import re
import sys
from pathlib import Path

# gamma-8slides.md 正文 8 卡（与 ppt 文件名顺序一致）
GAMMA_SLIDES = [
    ("1 AI已经亮牌/94%与33%", 7, 7, None, None),
    ("2 权限信任与签字权", 8, 10, None, "观察到的暴露度"),
    ("3 冰山一角", 10, 12, "观察到的暴露度", None),
    ("4 越精英越承压 (zh-cn 行9)", 13, 16, None, None),
    ("5 慕尼黑部门 (zh-cn 行11)", 17, 21, None, None),
    ("6 白领基础活 (zh-cn 行13+15)", 22, 28, None, None),
    ("7 年轻人入口变窄 (zh-cn 行17-19)", 29, 34, None, None),
    ("8 能力结构 (zh-cn 行21)", 35, 39, None, None),
]


def parse_ts(ts: str) -> float:
    h, m, s = ts.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def parse_srt(path: Path) -> dict[int, tuple[float, float, str]]:
    content = path.read_text(encoding="utf-8", errors="replace")
    cues: dict[int, tuple[float, float, str]] = {}
    for block in re.split(r"\n\s*\n", content.strip()):
        lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip()]
        if len(lines) < 2 or not lines[0].isdigit():
            continue
        m = re.match(
            r"(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)", lines[1]
        )
        if not m:
            continue
        num = int(lines[0])
        cues[num] = (
            parse_ts(m.group(1)),
            parse_ts(m.group(2)),
            "".join(lines[2:]),
        )
    return cues


def probe_duration(path: Path) -> float:
    import subprocess

    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def cue_start(cues: dict, n: int, marker: str | None) -> float:
    s, e, text = cues[n]
    if not marker:
        return s
    idx = text.index(marker)
    return s + (e - s) * (idx / len(text))


def cue_end(cues: dict, n: int, marker: str | None) -> float:
    s, e, text = cues[n]
    if not marker:
        return e
    idx = text.index(marker)
    return s + (e - s) * (idx / len(text))


srt_path = Path(sys.argv[1])
audio_path = Path(sys.argv[2])
intro_vid = Path(sys.argv[3])
manifest_path = Path(sys.argv[4])

cues = parse_srt(srt_path)
intro = probe_duration(intro_vid)
adur = probe_duration(audio_path)
outro_start = adur - intro
ppt_end = outro_start

lines: list[str] = [
    "# PPT 时间轴（gamma-8slides 正文 8 卡 + SRT）\n",
    f"# 片头/片尾各 {intro:.3f}s，PPT 窗口 [{intro:.3f}, {ppt_end:.3f}]\n\n",
]

durs: list[float] = []
for title, c0, c1, start_marker, end_marker in GAMMA_SLIDES:
    t0 = cue_start(cues, c0, start_marker)
    t1 = cue_end(cues, c1, end_marker)
    vs = max(intro, t0)
    ve = min(ppt_end, t1)
    d = max(0.0, ve - vs)
    durs.append(d)
    lines.append(
        f"{title}\n  口播 [{t0:.3f}, {t1:.3f}]  视频 [{vs:.3f}, {ve:.3f}]  时长 {d:.3f}s\n"
    )

gap = (ppt_end - intro) - sum(durs)
if gap > 0.001:
    durs[-1] += gap
    lines.append(f"# 末页补齐空隙 +{gap:.3f}s -> 第8页最终 {durs[-1]:.3f}s\n")

manifest_path.write_text("".join(lines), encoding="utf-8")

for d in durs:
    print(f"{d:.6f}")
PY
)

PNGS=()
for i in 1 2 3 4 5 6 7 8; do
  PNGS+=("$WORKDIR/ppt/slide_$(printf '%02d' "$i").png")
done

SCALE_VF="scale=1280:704:force_original_aspect_ratio=decrease,pad=1280:704:(ow-iw)/2:(oh-ih)/2,format=yuv420p"

for i in 1 2 3 4 5 6 7 8; do
  idx=$((i - 1))
  dur="${DURS[$idx]}"
  ffmpeg -hide_banner -y -loop 1 -i "${PNGS[$idx]}" -t "$dur" -vf "$SCALE_VF" -r 30 \
    -c:v libx264 -preset veryfast -crf 18 -an "$TMP/slide_${i}.mp4"
done

{
  for i in 1 2 3 4 5 6 7 8; do
    printf "file '%s'\n" "$TMP/slide_${i}.mp4"
  done
} >"$TMP/ppt_list.txt"

ffmpeg -hide_banner -y -f concat -safe 0 -i "$TMP/ppt_list.txt" -c copy "$TMP/ppt.mp4"

ffmpeg -hide_banner -y -i "$INTRO_VID" -t 26 -vf "$SCALE_VF" -r 30 \
  -c:v libx264 -preset veryfast -crf 18 -an "$TMP/intro.mp4"

ffmpeg -hide_banner -y -i "$INTRO_VID" -t 26 -vf "$SCALE_VF" -r 30 \
  -c:v libx264 -preset veryfast -crf 18 -an "$TMP/outro.mp4"

{
  printf "file '%s'\n" "$TMP/intro.mp4"
  printf "file '%s'\n" "$TMP/ppt.mp4"
  printf "file '%s'\n" "$TMP/outro.mp4"
} >"$TMP/video_list.txt"

ffmpeg -hide_banner -y -f concat -safe 0 -i "$TMP/video_list.txt" -c copy "$TMP/video_noaudio.mp4"

ffmpeg -hide_banner -y -i "$TMP/video_noaudio.mp4" -i "$AUDIO" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -shortest "$OUT"

echo "完成: $OUT"
echo "时间轴说明: $MANIFEST"
echo "PPT 各页时长(秒): ${DURS[*]}"
ffprobe -hide_banner -show_entries format=duration -of default=noprint_wrappers=1 "$OUT"
