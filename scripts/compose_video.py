#!/usr/bin/env python3
"""
将 SRT 字幕 + 音频 + PPT HTML 合成视频

用法:
    python3 build_video.py 字幕.srt 音频.flac 演示文稿.html

    python3 build_video.py 字幕.srt 音频.flac 演示文稿.html --resolution 1920x1080 -o 成片.mp4

    # 手动指定每页时长（秒）
    python3 build_video.py 字幕.srt 音频.flac 演示文稿.html --slide-durations 5,8,12,10,8,6,10

    # 使用已有图片，跳过 HTML 渲染
    python3 build_video.py 字幕.srt 音频.flac --slide-images "ppt/slide_*.png" -o 成片.mp4

依赖: python3, ffmpeg, playwright (pip install playwright && playwright install chromium)
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# ── SRT 解析 ──────────────────────────────────────────────

def parse_ts(ts: str) -> float:
    h, m, s = ts.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    """返回 [(开始秒, 结束秒, 文本), ...]"""
    content = path.read_text(encoding="utf-8", errors="replace")
    cues: list[tuple[float, float, str]] = []
    for block in re.split(r"\n\s*\n", content.strip()):
        lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip()]
        if len(lines) < 2 or not lines[0].isdigit():
            continue
        m = re.match(r"(\d+:\d+:\d+[,.]\d+)\s*-->\s*(\d+:\d+:\d+[,.]\d+)", lines[1])
        if not m:
            continue
        cues.append((parse_ts(m.group(1)), parse_ts(m.group(2)), "".join(lines[2:])))
    return cues


# ── 工具 ────────────────────────────────────────────────────

def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def run(*args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


# ── HTML → 图片渲染 ────────────────────────────────────────

def count_slides_in_html(html_path: Path) -> int:
    content = html_path.read_text(encoding="utf-8", errors="replace")
    return len(re.findall(r'<div[^>]*class="[^"]*slide[^"]*"', content))


def render_slides(html_path: Path, output_dir: Path, resolution: tuple[int, int]) -> list[Path]:
    """用 headless Chromium 逐页截图，返回图片路径列表"""
    from playwright.sync_api import sync_playwright

    w, h = resolution
    html_uri = html_path.resolve().as_uri()

    print(f"  启动 headless Chromium，分辨率 {w}x{h} ...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": w, "height": h})
        page.goto(html_uri, wait_until="domcontentloaded", timeout=30000)

        # 等待字体和动画就绪
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(1500)

        slide_count = page.evaluate(
            "() => document.querySelectorAll('.slide').length"
        )
        print(f"  共 {slide_count} 页幻灯片")

        paths: list[Path] = []
        for i in range(slide_count):
            page.evaluate(
                f"""() => {{
                    document.querySelectorAll('.slide').forEach(s => s.classList.remove('active'));
                    const el = document.querySelectorAll('.slide')[{i}];
                    if (el) el.classList.add('active');
                }}"""
            )
            page.wait_for_timeout(800)  # 等 CSS transition

            out = output_dir / f"slide_{i + 1:02d}.png"
            page.screenshot(path=str(out))
            paths.append(out)
            print(f"  [{i + 1}/{slide_count}] {out.name}")

        browser.close()
    return paths


# ── 幻灯片时间分配 ────────────────────────────────────────

def distribute_slides(
    cues: list[tuple[float, float, str]],
    slide_count: int,
    audio_duration: float,
    min_gap: float = 0.5,
) -> list[tuple[float, float]]:
    """
    分配幻灯片时间轴。

    优先在 SRT 自然断句处换页（间隔 >= min_gap 的停顿），
    如果自然断点不够则均匀分配剩余页。
    返回 [(开始秒, 结束秒), ...] 共 slide_count 项。
    """
    if slide_count <= 1:
        return [(0.0, audio_duration)]

    # 收集自然断点（间隔足够大的 cue 之间）
    natural_breaks: list[int] = []
    for i in range(len(cues) - 1):
        gap = cues[i + 1][0] - cues[i][1]
        if gap >= min_gap:
            natural_breaks.append(i)

    need = slide_count - 1

    # 如果自然断点够了，取前 need 个（按时间均匀挑选）
    if len(natural_breaks) >= need:
        # 均匀挑选 need 个
        step = len(natural_breaks) / need
        selected = [natural_breaks[int(i * step)] for i in range(need)]
    else:
        # 先用自然断点，不够的用均匀分布补充
        selected = list(natural_breaks)
        remaining = need - len(selected)

        # 在已有断点之间均匀插入
        existing = set(selected) | {-1, len(cues) - 1}
        if remaining > 0:
            total_cues = len(cues)
            step = max(1, total_cues // (remaining + 1))
            for k in range(1, remaining + 1):
                idx = min(k * step, total_cues - 2)
                if idx not in existing:
                    selected.append(idx)

    selected = sorted(selected)[:need]

    # 换页点取前后 cue 的中间时刻
    segments: list[tuple[float, float]] = []
    prev = 0.0
    for bi in selected:
        mid = (cues[bi][1] + cues[bi + 1][0]) / 2
        segments.append((prev, mid))
        prev = mid
    segments.append((prev, audio_duration))

    while len(segments) < slide_count:
        segments.append((prev, audio_duration))
    return segments[:slide_count]


# ── 视频合成 ───────────────────────────────────────────────

def build_video(
    slide_images: list[Path],
    slide_segments: list[tuple[float, float]],
    audio_path: Path,
    srt_path: Path,
    output_path: Path,
    resolution: tuple[int, int],
    subtitle_style: str = "",
    work_tmp: Path | None = None,
):
    """
    用 ffmpeg 合成最终视频：
      幻灯片图片 → 视频片段 → 拼接 → 叠加音频 + 烧录字幕
    """
    w, h = resolution
    if work_tmp is None:
        work_tmp = output_path.parent / ".build_video_tmp"
    tmp = work_tmp / "ffmpeg"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    vf_scale = (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
    )

    # 默认字幕样式
    if not subtitle_style:
        subtitle_style = (
            "FontSize=22,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,Outline=2,Shadow=1,"
            "Alignment=2,MarginV=40"
        )

    # 第一步：每页生成视频片段
    print("  [1/3] 生成幻灯片视频片段 ...")
    clip_paths: list[Path] = []
    for i, (img, (start, end)) in enumerate(zip(slide_images, slide_segments)):
        dur = max(0.5, end - start)
        out = tmp / f"clip_{i:02d}.mp4"
        run(
            "ffmpeg", "-hide_banner", "-y",
            "-loop", "1", "-i", str(img),
            "-t", str(dur),
            "-vf", vf_scale,
            "-r", "30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-an", str(out),
        )
        clip_paths.append(out)

    # 第二步：拼接
    print("  [2/3] 拼接视频片段 ...")
    concat_txt = tmp / "concat.txt"
    with open(concat_txt, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")

    concat_mp4 = tmp / "concat.mp4"
    run(
        "ffmpeg", "-hide_banner", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_txt),
        "-c", "copy", str(concat_mp4),
    )

    # 第三步：加音频 + 字幕
    print("  [3/3] 合成音频和字幕 ...")
    # 把 SRT 复制到安全路径，避免特殊字符导致 ffmpeg subtitles 滤镜解析失败
    srt_safe = tmp / "subtitles.srt"
    shutil.copy2(srt_path, srt_safe)

    sub_style = subtitle_style or (
        "FontSize=22,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,Outline=2,Shadow=1,"
        "Alignment=2,MarginV=40"
    )

    run(
        "ffmpeg", "-hide_banner", "-y",
        "-i", str(concat_mp4),
        "-i", str(audio_path),
        "-vf", f"subtitles={srt_safe}:force_style='{sub_style}'",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_path),
    )

    duration = probe_duration(output_path)
    print(f"  视频时长: {duration:.1f}s")

    shutil.rmtree(tmp)


# ── 主入口 ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SRT 字幕 + 音频 + PPT HTML → 对齐视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 build_video.py sub.srt audio.flac ppt.html
  python3 build_video.py sub.srt audio.flac ppt.html -r 1920x1080 -o out.mp4
  python3 build_video.py sub.srt audio.flac ppt.html --slide-durations 5,8,12,10
  python3 build_video.py sub.srt audio.flac --slide-images "ppt/*.png" --no-render
        """,
    )
    parser.add_argument("srt", help="SRT 字幕文件路径")
    parser.add_argument("audio", help="音频文件路径")
    parser.add_argument("ppt_html", nargs="?", help="PPT HTML 文件路径（如不用 HTML 渲染可省略）")
    parser.add_argument("-r", "--resolution", default="1280x720", help="视频分辨率 WxH (默认 1280x720)")
    parser.add_argument("-o", "--output", default="output.mp4", help="输出视频路径 (默认 output.mp4)")
    parser.add_argument("--slide-durations", help="手动指定每页时长(秒)，逗号分隔，如 7.8,9.7,9.1")
    parser.add_argument("--no-render", action="store_true", help="跳过 HTML 渲染（需要配合 --slide-images）")
    parser.add_argument("--slide-images", help="已有图片的 glob pattern，如 ppt/slide_*.png")
    parser.add_argument("--subtitle-style", default="",
                        help="ffmpeg subtitles force_style 覆盖 (默认内置样式)")
    args = parser.parse_args()

    # 解析分辨率
    try:
        w, h = map(int, args.resolution.lower().split("x"))
    except ValueError:
        sys.exit(f"分辨率格式错误: {args.resolution} (应为 WxH，如 1280x720)")
    resolution = (w, h)

    srt_path = Path(args.srt).resolve()
    audio_path = Path(args.audio).resolve()
    output_path = Path(args.output).resolve()

    if not srt_path.exists():
        sys.exit(f"SRT 文件不存在: {srt_path}")
    if not audio_path.exists():
        sys.exit(f"音频文件不存在: {audio_path}")

    # 解析输入
    cues = parse_srt(srt_path)
    audio_dur = probe_duration(audio_path)
    print(f"字幕: {len(cues)} 条  |  音频时长: {audio_dur:.1f}s  |  分辨率: {w}x{h}")

    # 工作临时目录（整个 build 过程共用）
    work_tmp = Path(tempfile.mkdtemp(prefix="build_video_"))

    try:
        # 获取幻灯片图片
        if args.no_render or (args.slide_images and not args.ppt_html):
            if not args.slide_images:
                sys.exit("--no-render 模式下需要 --slide-images 指定已有图片")
            import glob as _glob
            slide_images = sorted(Path(p) for p in _glob.glob(args.slide_images))
            if not slide_images:
                sys.exit(f"未找到图片: {args.slide_images}")
            print(f"已有图片: {len(slide_images)} 张")
        elif args.ppt_html:
            ppt_path = Path(args.ppt_html).resolve()
            if not ppt_path.exists():
                sys.exit(f"PPT HTML 文件不存在: {ppt_path}")
            if ppt_path.suffix.lower() not in (".html", ".htm"):
                sys.exit(f"PPT 文件应为 .html 格式: {ppt_path}")

            slide_count = count_slides_in_html(ppt_path)
            print(f"幻灯片: {slide_count} 页")

            slide_images = render_slides(ppt_path, work_tmp, resolution)
        else:
            sys.exit("请指定 PPT HTML 文件，或使用 --slide-images + --no-render")

        slide_count = len(slide_images)

        # 确定时间分配
        if args.slide_durations:
            durs = [float(x.strip()) for x in args.slide_durations.split(",")]
            if len(durs) != slide_count:
                sys.exit(f"--slide-durations 项数 ({len(durs)}) 与幻灯片数 ({slide_count}) 不匹配")
            segments = []
            t = 0.0
            for d in durs:
                segments.append((t, t + d))
                t += d
            print(f"手动时长: {durs}")
        else:
            segments = distribute_slides(cues, slide_count, audio_dur)
            print(f"自动分配的幻灯片时间:")
            for i, (s, e) in enumerate(segments):
                print(f"  第{i+1:2d}页: [{s:.1f}s - {e:.1f}s] 时长 {e-s:.1f}s")

        # 合成视频
        print(f"\n合成视频 -> {output_path}")
        build_video(
            slide_images=slide_images,
            slide_segments=segments,
            audio_path=audio_path,
            srt_path=srt_path,
            output_path=output_path,
            resolution=resolution,
            subtitle_style=args.subtitle_style,
            work_tmp=work_tmp,
        )

        # 报告
        final_dur = probe_duration(output_path)
        size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"\n完成: {output_path}")
        print(f"时长: {final_dur:.1f}s  |  大小: {size_mb:.1f} MB")

    finally:
        shutil.rmtree(work_tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
