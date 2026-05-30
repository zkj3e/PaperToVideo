#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""使用 Playwright 浏览器渲染 HTML PPT 为高质量 PNG 序列

依赖:
    pip install playwright
    playwright install chromium

用法:
    python3 scripts/render_slides_browser.py <html_ppt.html> <输出目录>

示例:
    python3 scripts/render_slides_browser.py "workspace/文章2/1-ppt.html" "workspace/文章2/ppt_frames_browser"
"""

import sys
import time
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

WIDTH, HEIGHT = 1280, 720

def parse_time_to_seconds(ts: str) -> float:
    ts = ts.strip()
    parts = ts.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0

def parse_slide_timings_from_html(html_path: Path):
    content = html_path.read_text(encoding="utf-8", errors="replace")
    tag_pattern = re.compile(
        r'<(?:div|section)\b[^>]*\bclass\s*=\s*"[^"]*\bslide\b(?!-)[^"]*"[^>]*>',
        re.IGNORECASE,
    )
    time_pattern = re.compile(r'data-time-(start|end)\s*=\s*"([^"]*)"', re.IGNORECASE)
    timings = []
    for tag_m in tag_pattern.finditer(content):
        tag = tag_m.group(0)
        start_val, end_val = "", ""
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

def count_slides(html_path: Path) -> int:
    content = html_path.read_text(encoding="utf-8", errors="replace")
    tag_pattern = re.compile(
        r'<(?:div|section)\b[^>]*\bclass\s*=\s*"[^"]*\bslide\b(?!-)[^"]*"[^>]*>',
        re.IGNORECASE,
    )
    return len(tag_pattern.findall(content))

def render_html_to_images(html_path: Path, output_dir: Path, viewport_size=(WIDTH, HEIGHT)):
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = Path(html_path).resolve()
    output_dir = output_dir.resolve()

    timings = parse_slide_timings_from_html(html_path)
    total_slides = count_slides(html_path)

    print(f"检测到 {total_slides} 张幻灯片")
    print(f"时间信息: {timings}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )

        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        page.set_viewport_size({"width": WIDTH, "height": HEIGHT})

        page.goto(f"file://{html_path}", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        for i in range(1, total_slides + 1):
            slide_idx = i - 1

            page.evaluate("""
                () => {
                    const slides = document.querySelectorAll('.slide');
                    slides.forEach((s, idx) => {
                        s.classList.remove('active');
                        s.classList.remove('target');
                        if (idx === %d) {
                            s.classList.add('active');
                            s.classList.add('target');
                        }
                    });
                    document.body.classList.add('export-mode');
                }
            """ % slide_idx)

            page.wait_for_timeout(500)

            slide_path = output_dir / f"slide_{i:02d}.png"
            page.screenshot(
                path=str(slide_path),
                type="png",
                full_page=False
            )

            if timings and slide_idx < len(timings):
                start, end = timings[slide_idx]
                duration = end - start
                print(f"  幻灯片 {i}: {slide_path.name} (持续 {duration:.1f}秒)")
            else:
                print(f"  幻灯片 {i}: {slide_path.name}")

        browser.close()

    return total_slides, timings

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    html_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    if not html_path.exists():
        print(f"错误: HTML 文件不存在: {html_path}")
        sys.exit(1)

    print(f"开始渲染 HTML PPT: {html_path}")
    print(f"输出目录: {output_dir}")

    total_slides, timings = render_html_to_images(html_path, output_dir)

    print(f"\n渲染完成! 共 {total_slides} 张幻灯片")
    print(f"PNG 文件位于: {output_dir}")

    if timings:
        print("\n各幻灯片时长:")
        for i, (start, end) in enumerate(timings, 1):
            print(f"  第{i}页: {start:.1f}s - {end:.1f}s (持续 {end-start:.1f}秒)")

    durations = [int(end - start) for start, end in timings] if timings else []
    if durations:
        print(f"\ndurations 参数 (用于 build_video.py):")
        print(f"  --durations \"{','.join(map(str, durations))}\"")

if __name__ == "__main__":
    main()
