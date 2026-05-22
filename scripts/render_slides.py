#!/usr/bin/env python3
"""将 HTML PPT 渲染为 PNG 幻灯片，可选自动合成视频。

用法:
  python render_slides.py <html文件> [幻灯片数量] [选项]

输出:
  默认输出到 HTML 同级目录下的 <文件名>_frame/ 目录
  slide_01.png ~ slide_NN.png

视频模式（HTML 需包含 data-time-start / data-time-end 属性）:
  python render_slides.py ppt.html 10 --audio 音频.flac --output-video 成片.mp4
  python render_slides.py ppt.html 10 --audio 音频.flac --srt 字幕.srt --output-video 成片.mp4

依赖: playwright (pip install playwright && playwright install chromium), ffmpeg
"""

import re
import shutil
import sys
import time
import threading
import socketserver
import subprocess
import tempfile
from pathlib import Path
from http.server import SimpleHTTPRequestHandler


MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".wav": "audio/wav",
    ".json": "application/json",
}


def get_mime(path: str) -> str:
    return MIME.get(Path(path).suffix, "application/octet-stream")


def make_handler(html_path: Path):
    base_dir = html_path.parent
    html_name = html_path.name

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            url_path = self.path.split("?")[0].split("#")[0]
            if url_path == "/":
                url_path = "/" + html_name

            file_path = base_dir / url_path.lstrip("/")
            try:
                content = file_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", get_mime(file_path.name))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_error(404)

        def log_message(self, format, *args):
            pass

    return Handler


def parse_time_to_seconds(ts: str) -> float:
    """将 MM:SS 或 HH:MM:SS 转为秒数"""
    ts = ts.strip()
    parts = ts.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def parse_slide_timings_from_html(html_path: Path) -> list[tuple[float, float]]:
    """从 HTML 中解析每页幻灯片的时间范围（data-time-start / data-time-end）。

    返回 [(start_seconds, end_seconds), ...] 列表，与 HTML 中 .slide 元素一一对应。
    封面页可能无时间属性，返回 (0, 0)。
    """
    content = html_path.read_text(encoding="utf-8", errors="replace")

    # 两步匹配：先找 slide 容器标签，再从标签内提取 data-time 属性
    # \bslide\b(?!-) 避免匹配 slide-num / slide-time 等 class
    tag_pattern = re.compile(
        r'<(?:div|section)\b[^>]*\bclass\s*=\s*"[^"]*\bslide\b(?!-)[^"]*"[^>]*>',
        re.IGNORECASE,
    )
    time_pattern = re.compile(r'data-time-(start|end)\s*=\s*"([^"]*)"', re.IGNORECASE)

    timings: list[tuple[float, float]] = []
    for tag_m in tag_pattern.finditer(content):
        tag = tag_m.group(0)
        start_val = ""
        end_val = ""
        for tm in time_pattern.finditer(tag):
            if tm.group(1).lower() == "start":
                start_val = tm.group(2)
            else:
                end_val = tm.group(2)
        if start_val and end_val:
            timings.append((parse_time_to_seconds(start_val), parse_time_to_seconds(end_val)))
        else:
            timings.append((0.0, 0.0))

    return timings


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        text=True,
    ).strip()
    return float(out)


def build_video(
    slide_images: list[Path],
    timings: list[tuple[float, float]],
    audio_path: Path,
    srt_path: Path | None,
    output_path: Path,
    resolution: tuple[int, int],
    subtitle_style: str = "",
):
    """用 ffmpeg 将幻灯片图片 + 时间 + 音频合成视频。"""
    w, h = resolution

    tmp = Path(tempfile.mkdtemp(prefix="render_slides_video_"))

    try:
        vf_scale = (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
        )

        if not subtitle_style:
            subtitle_style = (
                "FontSize=22,PrimaryColour=&H00FFFFFF,"
                "OutlineColour=&H00000000,Outline=2,Shadow=1,"
                "Alignment=2,MarginV=40"
            )

        # 第一步：每页生成视频片段
        print("  [1/3] 生成幻灯片视频片段 ...")
        clip_paths: list[Path] = []
        for i, (img, (start, end)) in enumerate(zip(slide_images, timings)):
            dur = max(0.5, end - start) if (start > 0 or end > 0) else 5.0
            out = tmp / f"clip_{i:02d}.mp4"
            subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-y",
                    "-loop", "1", "-i", str(img),
                    "-t", str(dur),
                    "-vf", vf_scale,
                    "-r", "30",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                    "-an", str(out),
                ],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            clip_paths.append(out)
            print(f"    [{i + 1}/{len(slide_images)}] {img.name} 时长 {dur:.1f}s")

        # 第二步：拼接
        print("  [2/3] 拼接视频片段 ...")
        concat_txt = tmp / "concat.txt"
        with open(concat_txt, "w") as f:
            for p in clip_paths:
                f.write(f"file '{p}'\n")

        concat_mp4 = tmp / "concat.mp4"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-y",
             "-f", "concat", "-safe", "0", "-i", str(concat_txt),
             "-c", "copy", str(concat_mp4)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

        # 第三步：加音频 + 可选字幕
        print("  [3/3] 合成音频" + (" + 字幕 ..." if srt_path else " ..."))
        filter_args = []
        map_args = ["-map", "0:v:0", "-map", "1:a:0"]

        if srt_path and srt_path.exists():
            srt_safe = tmp / "subtitles.srt"
            shutil.copy2(srt_path, srt_safe)
            filter_args = ["-vf", f"subtitles={srt_safe}:force_style='{subtitle_style}'"]

        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-y",
                "-i", str(concat_mp4),
                "-i", str(audio_path),
            ]
            + filter_args
            + map_args
            + [
                "-c:v", "libx264", "-preset", "medium", "-crf", "22",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                str(output_path),
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

        duration = probe_duration(output_path)
        size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"  视频时长: {duration:.1f}s  |  大小: {size_mb:.1f} MB")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def parse_args():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    html_path = Path(sys.argv[1]).resolve()
    if not html_path.exists():
        print(f"错误: HTML 文件不存在: {html_path}")
        sys.exit(1)

    slides = 8
    width, height, scale = 1280, 720, 2
    port = 8765
    audio: Path | None = None
    srt: Path | None = None
    output_video: Path | None = None

    for arg in sys.argv[2:]:
        if arg.startswith("--"):
            if "=" in arg:
                k, v = arg.lstrip("-").split("=", 1)
            else:
                k, v = arg.lstrip("-"), None
            if k == "slides":
                slides = int(v)
            elif k == "width":
                width = int(v)
            elif k == "height":
                height = int(v)
            elif k == "scale":
                scale = int(v)
            elif k == "port":
                port = int(v)
            elif k == "audio":
                audio = Path(v).resolve()
                if not audio.exists():
                    print(f"错误: 音频文件不存在: {audio}")
                    sys.exit(1)
            elif k == "srt":
                srt = Path(v).resolve()
                if not srt.exists():
                    print(f"错误: SRT 文件不存在: {srt}")
                    sys.exit(1)
            elif k == "output-video" or k == "output_video":
                output_video = Path(v).resolve()
        else:
            slides = int(arg)

    return html_path, slides, width, height, scale, port, audio, srt, output_video


def start_server(html_path: Path, port: int) -> threading.Thread:
    handler = make_handler(html_path)
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    time.sleep(0.5)
    return t


def main():
    html_path, slides, width, height, scale, port, audio, srt, output_video = parse_args()

    out_dir = html_path.parent / f"{html_path.stem}_frame"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 解析 HTML 中的时间信息（用于视频模式）
    slide_timings: list[tuple[float, float]] = []
    if audio:
        slide_timings = parse_slide_timings_from_html(html_path)
        if not slide_timings:
            print("警告: HTML 中未找到 data-time-start/data-time-end 属性")
            print("  视频模式需要幻灯片包含时间属性，将使用默认时长")
        else:
            print(f"从 HTML 解析到 {len(slide_timings)} 页时间信息")
            for i, (s, e) in enumerate(slide_timings):
                if s > 0 or e > 0:
                    print(f"  第{i+1:2d}页: {s:.1f}s - {e:.1f}s (时长 {e-s:.1f}s)")

    start_server(html_path, port)
    base_url = f"http://127.0.0.1:{port}/{html_path.name}"
    print(f"HTTP 服务器已启动: http://127.0.0.1:{port}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "错误: 需要 playwright，请执行:\n"
            "  pip install playwright && playwright install chromium"
        )
        sys.exit(1)

    rendered_images: list[Path] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for i in range(1, slides + 1):
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=scale,
            )
            url = f"{base_url}#slide-{i}"
            print(f"  渲染第 {i}/{slides} 页: {url}")

            page.goto(url, wait_until="networkidle", timeout=30000)
            page.evaluate("() => document.fonts.ready")
            page.wait_for_timeout(500)

            out_file = out_dir / f"slide_{i:02d}.png"
            page.screenshot(path=str(out_file), type="png")
            size = out_file.stat().st_size
            print(f"    已保存: {out_file} ({size / 1024:.1f} KB)")
            rendered_images.append(out_file)
            page.close()

        browser.close()

    print(f"渲染完成: {out_dir}/slide_01.png ~ slide_{slides:02d}.png")

    # ── 视频合成 ────────────────────────────────────────
    if audio:
        if not output_video:
            output_video = html_path.parent / f"{html_path.stem}.mp4"

        # 确保 timing 数据量匹配
        if len(slide_timings) < slides:
            slide_timings += [(0.0, 0.0)] * (slides - len(slide_timings))
        timings = slide_timings[:slides]

        # 对于无时间属性的页，用音频总时长均匀分配
        audio_dur = probe_duration(audio)
        has_timings = any(s > 0 or e > 0 for s, e in timings)
        if not has_timings:
            per_slide = audio_dur / slides
            timings = [(i * per_slide, (i + 1) * per_slide) for i in range(slides)]
            print(f"无时间信息，均匀分配: 每页 {per_slide:.1f}s")

        print(f"\n合成视频 -> {output_video}")
        build_video(
            slide_images=rendered_images,
            timings=timings,
            audio_path=audio,
            srt_path=srt,
            output_path=output_video,
            resolution=(width, height),
        )

        print(f"\n完成: {output_video}")


if __name__ == "__main__":
    main()
