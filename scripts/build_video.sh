#!/usr/bin/env bash
set -euo pipefail

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
TMP="$WORKDIR/.build_tmp"
AUDIO="$WORKDIR/语音.flac"
OUT="$WORKDIR/今年趋势_成片.mp4"

rm -rf "$TMP"
mkdir -p "$TMP"

# ── 幻灯片时长（从 HTML data-time 提取）─────────────────
# Slide  1: 00:00-00:11 = 11s
# Slide  2: 00:11-00:27 = 16s
# Slide  3: 00:27-00:40 = 13s
# Slide  4: 00:40-00:53 = 13s
# Slide  5: 00:53-01:15 = 22s
# Slide  6: 01:15-01:38 = 23s
# Slide  7: 01:38-02:09 = 31s
# Slide  8: 02:09-02:36 = 27s
# Slide  9: 02:36-02:56 = 20s
# Slide 10: 02:56-03:17 = 21s
# 合计 197s，音频 197.94s，余量补到最后一页
DURS=(11 16 13 13 22 23 31 27 20 21)

AUDIO_DUR=$(ffprobe -hide_banner -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$AUDIO" 2>/dev/null)
TOTAL_DUR=$(printf "%.3f" "$AUDIO_DUR")
SUM_DUR=0
for d in "${DURS[@]}"; do SUM_DUR=$((SUM_DUR + d)); done
GAP=$(echo "$TOTAL_DUR - $SUM_DUR" | bc -l)
if (( $(echo "$GAP > 0" | bc -l) )); then
  DURS[9]=$(echo "${DURS[9]} + $GAP" | bc -l)
  echo "音频 $TOTAL_DUR 秒，PPT 合计 ${SUM_DUR}s，末页补齐 ${GAP}s → 末页 ${DURS[9]}s"
fi

SCALE_VF="scale=1280:704:force_original_aspect_ratio=decrease,pad=1280:704:(ow-iw)/2:(oh-ih)/2,format=yuv420p"

# ── 渲染每页为视频 ────────────────────────────────────────
for i in $(seq 1 10); do
  idx=$((i - 1))
  dur="${DURS[$idx]}"
  png="$WORKDIR/ppt_new/slide_$(printf '%02d' "$i").png"
  echo "第${i}页: $png → ${dur}s"
  ffmpeg -hide_banner -y -loop 1 -i "$png" -t "$dur" -vf "$SCALE_VF" -r 30 \
    -c:v libx264 -preset veryfast -crf 18 -an "$TMP/slide_${i}.mp4"
done

# ── 拼接所有视频段 ────────────────────────────────────────
{
  for i in $(seq 1 10); do
    printf "file '%s'\n" "$TMP/slide_${i}.mp4"
  done
} >"$TMP/list.txt"

ffmpeg -hide_banner -y -f concat -safe 0 -i "$TMP/list.txt" -c copy "$TMP/video_noaudio.mp4"

# ── 合入音频 ──────────────────────────────────────────────
ffmpeg -hide_banner -y -i "$TMP/video_noaudio.mp4" -i "$AUDIO" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -shortest "$OUT"

echo "完成: $OUT"
ffprobe -hide_banner -show_entries format=duration -of default=noprint_wrappers=1 "$OUT" 2>/dev/null
