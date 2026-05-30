#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 HTML PPT 使用 Pillow 渲染为 PNG 幻灯片序列图（支持报纸风/赛博朋克风）

用法:
    python3 scripts/render_slides.py <html_ppt.html> <输出目录>

示例:
    python3 scripts/render_slides.py "workspace/文章1/字幕-ppt.html" "workspace/文章1/ppt_frames"
    python3 scripts/render_slides.py "workspace/文章1/字幕-ppt-cyberpunk.html" "workspace/文章1/cyberpunk_frames"

依赖: pip install Pillow
"""

import re
import sys
import hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup

WIDTH, HEIGHT = 1280, 720
EXPECTED_RESOLUTION = (WIDTH, HEIGHT)

CYAN = (0, 229, 255)
PINK = (255, 46, 166)
PURPLE = (139, 92, 246)
INK = (216, 231, 255)
BG = (6, 8, 22)
BG2 = (23, 37, 61)
PANEL_RGBA = (10, 18, 32, 210)
MUTED = (110, 126, 168)
WHITE = (255, 255, 255)
BG_PAPER = (244, 239, 230)
INK_PAPER = (25, 25, 25)
ACCENT_RED = (198, 40, 40)
LINE_PAPER = (215, 208, 194)

FONT_PINGFANG = "/System/Library/Fonts/PingFang.ttc"
FONT_SF = "/System/Library/Fonts/SFNS.ttc"
FONT_HELVETICA_NEUE = "/System/Library/Fonts/HelveticaNeue.ttc"
FONT_AVENIR = "/System/Library/Fonts/Avenir Next.ttc"
FONT_SF_COMPACT = "/System/Library/Fonts/SFCompact.ttf"

FONT_FALLBACKS = [
    ("PingFang", FONT_PINGFANG),
    ("SF NS", FONT_SF),
    ("Helvetica Neue", FONT_HELVETICA_NEUE),
    ("Avenir", FONT_AVENIR),
    ("SF Compact", FONT_SF_COMPACT),
]

FONT_BOLD_FALLBACKS = [
    ("PingFang", "/System/Library/Fonts/PingFang.ttc"),
    ("Helvetica Neue", "/System/Library/Fonts/HelveticaNeue.ttc"),
    ("SF Compact", "/System/Library/Fonts/SFCompact.ttf"),
    ("Avenir", "/System/Library/Fonts/Avenir Next.ttc"),
    ("SF NS", "/System/Library/Fonts/SFNS.ttc"),
]

def get_font(size, bold=False, prefer_font=None):
    fonts_to_try = []
    
    if bold:
        for name, path in FONT_BOLD_FALLBACKS:
            if prefer_font and prefer_font.lower() in name.lower():
                fonts_to_try.insert(0, (name, path))
                break
        for name, path in fonts_to_try:
            try:
                return ImageFont.truetype(path, size)
            except:
                pass
        for name, path in FONT_BOLD_FALLBACKS:
            try:
                return ImageFont.truetype(path, size)
            except:
                pass
    
    if prefer_font:
        for name, path in FONT_FALLBACKS:
            if prefer_font.lower() in name.lower():
                fonts_to_try.insert(0, (name, path))
                break
    
    for name, path in fonts_to_try:
        try:
            return ImageFont.truetype(path, size)
        except:
            pass
    
    for name, path in FONT_FALLBACKS:
        try:
            return ImageFont.truetype(path, size)
        except:
            pass
    
    return ImageFont.load_default()

def get_cyberpunk_font(size, bold=True):
    return get_font(size, bold=bold, prefer_font="pingfang")

def get_file_md5(filepath: Path) -> str:
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()

def validate_png_uniqueness(png_files: list) -> dict:
    seen = {}
    duplicates = []
    for png_path in png_files:
        h = get_file_md5(png_path)
        if h in seen:
            duplicates.append((str(png_path.name), seen[h]))
        else:
            seen[h] = str(png_path.name)
    return {"unique": len(seen), "total": len(png_files), "duplicates": duplicates}

def validate_png_resolution(png_path: Path) -> tuple:
    try:
        with Image.open(png_path) as img:
            return (img.size == EXPECTED_RESOLUTION, img.size)
    except Exception as e:
        return (False, f"error: {e}")

def validate_slides_output(output_dir: Path) -> dict:
    png_files = sorted(output_dir.glob("slide_*.png"))
    if not png_files:
        return {"error": "No PNG files found", "valid": False}
    
    results = {
        "total": len(png_files),
        "uniqueness": validate_png_uniqueness(png_files),
        "resolution_check": [],
        "valid": True,
        "issues": []
    }
    
    for png_path in png_files:
        is_valid_res, size = validate_png_resolution(png_path)
        results["resolution_check"].append({"file": png_path.name, "valid": is_valid_res, "size": size})
        if not is_valid_res:
            results["valid"] = False
            results["issues"].append(f"Resolution mismatch in {png_path.name}: {size} (expected {EXPECTED_RESOLUTION})")
    
    uniqueness = results["uniqueness"]
    if uniqueness["duplicates"]:
        results["valid"] = False
        for dup_name, orig_name in uniqueness["duplicates"]:
            results["issues"].append(f"Duplicate content: {dup_name} is identical to {orig_name}")
    
    return results

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

def detect_theme(html_path: Path) -> str:
    content = html_path.read_text(encoding="utf-8", errors="replace")
    if "#060816" in content or "var(--bg): #060816" in content or "background: #060816" in content:
        return "cyberpunk"
    return "newspaper"

def draw_gradient_bg(img):
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(BG[0] + (BG2[0] - BG[0]) * ratio * 0.5)
        g = int(BG[1] + (BG2[1] - BG[1]) * ratio * 0.5)
        b = int(BG[2] + (BG2[2] - BG[2]) * ratio * 0.5)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    return img

def draw_grid(img, alpha=10):
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for x in range(0, WIDTH, 40):
        draw.line([(x, 0), (x, HEIGHT)], fill=(0, 229, 255, alpha))
    for y in range(0, HEIGHT, 40):
        draw.line([(0, y), (WIDTH, y)], fill=(0, 229, 255, alpha))
    result = Image.new('RGBA', img.size)
    result.paste(img, (0, 0))
    result.paste(overlay, (0, 0), overlay)
    return result.convert('RGB')

def glow_text(draw, pos, text, font, color, glow_color=None, glow_radius=3):
    if glow_color:
        for dx in range(-glow_radius, glow_radius+1):
            for dy in range(-glow_radius, glow_radius+1):
                if dx*dx + dy*dy <= glow_radius * glow_radius:
                    draw.text((pos[0]+dx, pos[1]+dy), text, fill=glow_color, font=font)
    draw.text(pos, text, fill=color, font=font)

def stroke_text(draw, pos, text, font, fill_color, stroke_color=None, stroke_width=2):
    if stroke_color and stroke_width > 0:
        for sw in range(stroke_width, 0, -1):
            for dx in range(-sw, sw+1):
                for dy in range(-sw, sw+1):
                    if abs(dx) == sw or abs(dy) == sw:
                        draw.text((pos[0]+dx, pos[1]+dy), text, fill=stroke_color, font=font)
    draw.text(pos, text, fill=fill_color, font=font)

def draw_kicker_cyberpunk(draw, text, x=80, y=60):
    draw.text((x, y), text.upper(), fill=CYAN, font=get_cyberpunk_font(13, bold=True))

def draw_display_cyberpunk(draw, text, x=80, y=120, color=CYAN, font_size=72):
    font = get_cyberpunk_font(font_size, bold=True)
    glow_text(draw, (x, y), text, font, color, color, glow_radius=4)

def draw_headline_cyberpunk(draw, text, x=80, y=120, color=INK, font_size=40):
    font = get_cyberpunk_font(font_size, bold=True)
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = line + " " + word if line else word
        tw = font.getsize(test)[0] if hasattr(font, 'getsize') else font.getbbox(test)[2]
        if tw > WIDTH - 200:
            if line:
                lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    y_off = 0
    for l in lines:
        draw.text((x, y + y_off), l, fill=color, font=font)
        y_off += int(font_size * 1.3)

def draw_divider_cyberpunk(draw, x=80, y=200, color=PINK, width_val=60):
    draw.rectangle([x, y, x+width_val, y+3], fill=color)

def draw_subtitle_cyberpunk(draw, text, x=80, y=240, color=INK, font_size=24, max_width=900):
    font = get_font(font_size, bold=False)
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = line + " " + word if line else word
        tw = font.getsize(test)[0] if hasattr(font, 'getsize') else font.getbbox(test)[2]
        if tw > max_width:
            if line:
                lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    y_off = 0
    for l in lines:
        draw.text((x, y + y_off), l, fill=color, font=font)
        y_off += int(font_size * 1.7)

def draw_panel_cyberpunk(draw, x, y, w, h, border_color=None):
    if border_color is None:
        border_color = (0, 229, 255, 50)
    draw.rectangle([x, y, x+w-1, y+h-1], fill=PANEL_RGBA[:3])
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([0, 0, w-1, h-1], outline=border_color[:3], width=1)
    result = Image.new('RGB', (w, h), PANEL_RGBA[:3])
    result.paste(overlay, (0, 0), overlay)
    img_overlay = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
    img_overlay.paste(result, (x, y), result)
    background = draw.im.convert('RGBA')
    background.paste(img_overlay, (0, 0), img_overlay)
    draw.im = background.convert('RGB')

def draw_stat_cyberpunk(draw, text, x, y, color=CYAN, font_size=64):
    font = get_font(font_size, bold=True)
    stroke_color = (6, 8, 22)
    
    def get_char_width(c):
        if hasattr(font, 'getsize'):
            return font.getsize(c)[0]
        return font.getbbox(c)[2]
    
    char_spacing = max(3, int(font_size * 0.15))
    total_width = sum(get_char_width(c) for c in text) + char_spacing * (len(text) - 1)
    current_x = x
    
    for c in text:
        char_w = get_char_width(c)
        stroke_text(draw, (current_x, y), c, font, color, stroke_color=stroke_color, stroke_width=3)
        glow_text(draw, (current_x, y), c, font, color, color, glow_radius=3)
        current_x += char_w + char_spacing

def draw_stat_label_cyberpunk(draw, text, x, y, color=MUTED, font_size=16):
    draw.text((x, y), text, fill=color, font=get_font(font_size))

def draw_tag_cyberpunk(draw, text, x, y, color=CYAN):
    font = get_font(15)
    tw = font.getsize(text)[0] if hasattr(font, 'getsize') else font.getbbox(text)[2]
    padding = 16
    h = 36
    draw.rectangle([x, y, x+tw+padding*2, y+h], fill=(*color, 20))
    draw.rectangle([x, y, x+tw+padding*2, y+h], outline=(*color, 80), width=1)
    draw.text((x+padding, y+8), text, fill=color, font=font)

def draw_quote_cyberpunk(draw, text, x, y, color=INK, font_size=20, max_width=900):
    font = get_font(font_size, bold=False)
    draw.rectangle([x, y, x+3, y+60], fill=CYAN)
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = line + " " + word if line else word
        tw = font.getsize(test)[0] if hasattr(font, 'getsize') else font.getbbox(test)[2]
        if tw > max_width - 30:
            if line:
                lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    y_off = 10
    for l in lines:
        draw.text((x+20, y+y_off), l, fill=color, font=font)
        y_off += int(font_size * 1.7)

def draw_footer_cyberpunk(draw, left_text, time_text, page_text, y=None):
    if y is None:
        y = HEIGHT - 50
    font = get_font(12)
    draw.text((80, y), left_text, fill=MUTED, font=font)
    tw = font.getsize(time_text)[0] if hasattr(font, 'getsize') else font.getbbox(time_text)[2]
    draw.text((WIDTH - 80 - tw, y), time_text, fill=PINK, font=font)
    pw = get_font(12, bold=True).getsize(page_text)[0] if hasattr(get_font(12, bold=True), 'getsize') else get_font(12, bold=True).getbbox(page_text)[2]
    draw.text(((WIDTH - pw) // 2, y), page_text, fill=MUTED, font=get_font(12, bold=True))

def draw_corner_deco_cyberpunk(draw, text, x=None, y=20):
    if x is None:
        x = WIDTH - 120
    draw.text((x, y), text, fill=(0, 229, 255, 60), font=get_font(11))

def draw_kicker_newspaper(draw, text, x=88, y=72):
    font = get_font(13, bold=True)
    draw.text((x, y), text.upper(), fill=ACCENT_RED, font=font)

def draw_display_newspaper(draw, text, x=88, y=140, color=INK_PAPER, font_size=92):
    font = get_font(font_size, bold=True)
    draw.text((x, y), text, fill=color, font=font)

def draw_headline_newspaper(draw, text, x=88, y=140, color=INK_PAPER, font_size=56):
    font = get_font(font_size, bold=True)
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = line + " " + word if line else word
        tw = font.getsize(test)[0] if hasattr(font, 'getsize') else font.getbbox(test)[2]
        if tw > WIDTH - 200:
            if line:
                lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    y_off = 0
    for l in lines:
        draw.text((x, y + y_off), l, fill=color, font=font)
        y_off += int(font_size * 1.05)

def draw_hairline_newspaper(draw, x=88, y=135, width_val=420, thick=False):
    h = 3 if thick else 1
    color = INK_PAPER if thick else LINE_PAPER
    draw.rectangle([x, y, x+width_val, y+h], fill=color)

def draw_body_newspaper(draw, text, x, y, color=(43, 43, 43), font_size=18, max_width=800):
    font = get_font(font_size)
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = line + " " + word if line else word
        tw = font.getsize(test)[0] if hasattr(font, 'getsize') else font.getbbox(test)[2]
        if tw > max_width:
            if line:
                lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    y_off = 0
    for l in lines:
        draw.text((x, y + y_off), l, fill=color, font=font)
        y_off += int(font_size * 1.9)

def draw_stat_card_newspaper(draw, x, y, w, h):
    draw.rectangle([x, y, x+w-1, y+h-1], fill=(255, 253, 248), outline=LINE_PAPER)

def draw_stat_number_newspaper(draw, text, x, y, color=ACCENT_RED, font_size=96):
    draw.text((x, y), text, fill=color, font=get_font(font_size, bold=True))

def draw_stat_label_newspaper(draw, text, x, y, color=MUTED, font_size=16):
    draw.text((x, y), text, fill=color, font=get_font(font_size))

def draw_quote_newspaper(draw, text, x, y, color=INK_PAPER, font_size=24, max_width=800):
    font = get_font(font_size, bold=True)
    draw.rectangle([x, y, x+4, y+40], fill=ACCENT_RED)
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = line + " " + word if line else word
        tw = font.getsize(test)[0] if hasattr(font, 'getsize') else font.getbbox(test)[2]
        if tw > max_width - 30:
            if line:
                lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    y_off = 10
    for l in lines:
        draw.text((x+24, y+y_off), l, fill=color, font=font)
        y_off += int(font_size * 1.7)

def draw_tag_newspaper(draw, text, x, y, color=INK_PAPER, is_red=False):
    font = get_font(14)
    tw = font.getsize(text)[0] if hasattr(font, 'getsize') else font.getbbox(text)[2]
    padding = 18
    h = 36
    c = ACCENT_RED if is_red else INK_PAPER
    draw.rectangle([x, y, x+tw+padding*2, y+h], fill=(255, 255, 255, 200))
    draw.rectangle([x, y, x+tw+padding*2, y+h], outline=c, width=1)
    draw.text((x+padding, y+8), text, fill=c, font=font)

def draw_footer_newspaper(draw, left_text, time_text, page_text, y=None):
    if y is None:
        y = HEIGHT - 60
    draw.rectangle([88, y-10, WIDTH-88, y-9], fill=LINE_PAPER)
    draw.text((88, y), left_text, fill=MUTED, font=get_font(13))
    tw = get_font(13).getsize(time_text)[0] if hasattr(get_font(13), 'getsize') else get_font(13).getbbox(time_text)[2]
    draw.text((WIDTH-88-tw, y), time_text, fill=MUTED, font=get_font(13))
    pw = get_font(13, bold=True).getsize(page_text)[0] if hasattr(get_font(13, bold=True), 'getsize') else get_font(13, bold=True).getbbox(page_text)[2]
    draw.text(((WIDTH-pw)//2, y), page_text, fill=ACCENT_RED, font=get_font(13, bold=True))

CYBERPUNK_RENDERERS = []

def make_cyberpunk_renderer(slide_data):
    def renderer(img, time_start, time_end, page, total):
        draw = ImageDraw.Draw(img)
        draw_corner_deco_cyberpunk(draw, f"{page:02d} / {total:02d}")
        if slide_data.get('kicker'):
            draw_kicker_cyberpunk(draw, slide_data['kicker'])
        if slide_data.get('display'):
            draw_display_cyberpunk(draw, slide_data['display'], y=120, font_size=72)
        if slide_data.get('headline'):
            draw_headline_cyberpunk(draw, slide_data['headline'], font_size=40)
        if slide_data.get('divider'):
            draw_divider_cyberpunk(draw, y=210)
        if slide_data.get('subtitle'):
            draw_subtitle_cyberpunk(draw, slide_data['subtitle'], y=250, font_size=22, max_width=1000)
        if slide_data.get('panel'):
            p = slide_data['panel']
            draw_panel_cyberpunk(draw, p['x'], p['y'], p['w'], p['h'])
        if slide_data.get('stat'):
            s = slide_data['stat']
            draw_stat_cyberpunk(draw, s['label'], s['x'], s['y'], color=s.get('color', CYAN), font_size=s.get('size', 64))
        if slide_data.get('stat_label'):
            sl = slide_data['stat_label']
            draw_stat_label_cyberpunk(draw, sl['text'], sl['x'], sl['y'], color=MUTED, font_size=16)
        if slide_data.get('tags'):
            tx = slide_data.get('tags_x', 110)
            ty = slide_data.get('tags_y', 395)
            for tag_text, tag_color in slide_data['tags']:
                draw_tag_cyberpunk(draw, tag_text, tx, ty, color=tag_color)
                tw = get_font(15).getsize(tag_text)[0] if hasattr(get_font(15), 'getsize') else get_font(15).getbbox(tag_text)[0]
                tx += tw + 28 + 12
        if slide_data.get('quote'):
            draw_quote_cyberpunk(draw, slide_data['quote'], 80, 450, font_size=20, max_width=1100)
        draw_footer_cyberpunk(draw, slide_data.get('footer', 'THE GREATEST AI INVESTMENT'), f"{time_start} – {time_end}", f"{page:02d} / {total:02d}")
    return renderer

def parse_html_for_cyberpunk_slides(html_path: Path):
    content = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(content, 'html.parser')
    slides = []
    for slide_elem in soup.find_all('div', class_=lambda x: x and 'slide' in x and 'slide-' not in x):
        data = {}
        kicker = slide_elem.find(class_='kicker')
        if kicker:
            data['kicker'] = kicker.get_text(strip=True)
        display = slide_elem.find(class_='display')
        if display:
            data['display'] = display.get_text(strip=True).replace('\n', ' ')
        headline = slide_elem.find(class_='headline')
        if headline:
            data['headline'] = headline.get_text(strip=True).replace('\n', ' ')
        subtitle = slide_elem.find(class_='subtitle')
        if subtitle:
            data['subtitle'] = subtitle.get_text(strip=True).replace('\n', ' ')
        quote = slide_elem.find(class_='quote-block')
        if not quote:
            quote = slide_elem.find(class_='quote')
        if quote:
            data['quote'] = quote.get_text(strip=True).replace('\n', ' ')
        if slide_elem.find(class_='panel'):
            data['panel'] = {'x': 80, 'y': 340, 'w': 1070, 'h': 200}
        tags = slide_elem.find_all(class_=lambda x: x and 'tag' in x and 'tag-row' not in x)
        if tags:
            tag_list = []
            for t in tags:
                txt = t.get_text(strip=True)
                is_pink = 'pink' in t.get('class', [])
                tag_list.append((txt, PINK if is_pink else CYAN))
            data['tags'] = tag_list
            data['tags_x'] = 110
            data['tags_y'] = 395
        stat_cols = slide_elem.find_all(class_='stat-col')
        if stat_cols:
            for sc in stat_cols:
                big_num = sc.find(class_='big-num')
                if big_num:
                    txt = big_num.get_text(strip=True)
                    color = CYAN if 'cyan' in big_num.get('class', []) else PINK if 'pink' in big_num.get('class', []) else CYAN
                    if 'stat' not in data:
                        data['stat'] = {'label': txt, 'x': 100, 'y': 260, 'color': color, 'size': 64}
                    else:
                        if 'stat_label' not in data:
                            data['stat_label'] = txt
        slides.append(data)
    while len(slides) < 9:
        slides.append({})
    return slides[:9]

def parse_html_for_newspaper_slides(html_path: Path):
    content = html_path.read_text(encoding="utf-8", errors="replace")
    slides = []
    tag_pattern = re.compile(
        r'<(?:div|section)\b[^>]*\bclass\s*=\s*"[^"]*\bslide\b(?!-)[^"]*"[^>]*>(.*?)</(?:div|section)>',
        re.IGNORECASE | re.DOTALL,
    )
    for slide_match in tag_pattern.finditer(content):
        slide_html = slide_match.group(0)
        data = {}
        kicker_m = re.search(r'class="kicker"[^>]*>(.*?)</', slide_html, re.DOTALL)
        if kicker_m:
            data['kicker'] = re.sub(r'<[^>]+>', '', kicker_m.group(1)).strip()
        display_m = re.search(r'class="display"[^>]*>(.*?)</', slide_html, re.DOTALL)
        if display_m:
            data['display'] = re.sub(r'<[^>]+>', '', display_m.group(1)).strip().replace('\n', ' ')
        headline_m = re.search(r'class="headline"[^>]*>(.*?)</', slide_html, re.DOTALL)
        if headline_m:
            data['headline'] = re.sub(r'<[^>]+>', '', headline_m.group(1)).strip().replace('\n', ' ')
        body_ms = re.findall(r'class="body"[^>]*>(.*?)</', slide_html, re.DOTALL)
        if body_ms:
            data['body'] = ' '.join(re.sub(r'<[^>]+>', '', b).strip() for b in body_ms[:3])
        quote_m = re.search(r'class="quote"[^>]*>(.*?)</', slide_html, re.DOTALL)
        if quote_m:
            data['quote'] = re.sub(r'<[^>]+>', '', quote_m.group(1)).strip().replace('\n', ' ')
        stat_m = re.search(r'class="stat-number"[^>]*>(.*?)</', slide_html, re.DOTALL)
        if stat_m:
            txt = re.sub(r'<[^>]+>', '', stat_m.group(1)).strip()
            data['stat'] = txt
        stat_label_m = re.search(r'class="stat-label"[^>]*>(.*?)</', slide_html, re.DOTALL)
        if stat_label_m:
            txt = re.sub(r'<[^>]+>', '', stat_label_m.group(1)).strip().replace('\n', ' ')
            data['stat_label'] = txt
        slides.append(data)
    return slides

def render_cyberpunk_slide(draw, img, slide_data, time_start, time_end, page, total):
    draw_corner_deco_cyberpunk(draw, f"{page:02d} / {total:02d}")
    y = 80
    if slide_data.get('kicker'):
        draw_kicker_cyberpunk(draw, slide_data['kicker'])
        y = 120
    if slide_data.get('display'):
        parts = slide_data['display'].split('\n')
        dy = 120
        for part in parts:
            draw_display_cyberpunk(draw, part.strip(), y=dy, font_size=72)
            dy += 80
        y = dy + 10
    if slide_data.get('headline'):
        draw_headline_cyberpunk(draw, slide_data['headline'], y=y+10, font_size=40)
        y += 100
    draw_divider_cyberpunk(draw, y=y)
    y += 20
    if slide_data.get('subtitle'):
        draw_subtitle_cyberpunk(draw, slide_data['subtitle'], y=y, font_size=22, max_width=1000)
        y += 100
    if slide_data.get('panel'):
        p = slide_data['panel']
        panel_img = Image.new('RGB', (p['w'], p['h']), (10, 18, 32))
        img.paste(panel_img, (p['x'], p['y']))
        draw = ImageDraw.Draw(img)
        draw.rectangle([p['x'], p['y'], p['x']+p['w']-1, p['y']+p['h']-1], outline=(0, 229, 255, 50))
        y_p = p['y'] + 30
        if slide_data.get('stat'):
            s = slide_data['stat']
            color = s.get('color', CYAN) if isinstance(s, dict) else CYAN
            label = s.get('label', s) if isinstance(s, dict) else s
            draw_stat_cyberpunk(draw, label, p['x']+30, y_p, color=color, font_size=56)
            y_p += 80
        if slide_data.get('stat_label'):
            sl = slide_data['stat_label']
            draw_stat_label_cyberpunk(draw, sl, p['x']+30, y_p, color=MUTED, font_size=15)
        y = p['y'] + p['h'] + 30
    if slide_data.get('tags'):
        tx = 110
        ty = y
        for tag_text, tag_color in slide_data['tags']:
            font = get_font(15)
            tw = font.getsize(tag_text)[0] if hasattr(font, 'getsize') else font.getbbox(tag_text)[2]
            padding = 16
            h = 36
            draw.rectangle([tx, ty, tx+tw+padding*2, ty+h], fill=(*tag_color, 20))
            draw.rectangle([tx, ty, tx+tw+padding*2, ty+h], outline=(*tag_color, 80), width=1)
            draw.text((tx+padding, ty+8), tag_text, fill=tag_color, font=font)
            tx += tw + padding*2 + 12
        y = ty + h + 20
    if slide_data.get('quote'):
        draw_quote_cyberpunk(draw, slide_data['quote'], 80, y, font_size=20, max_width=1000)
    draw_footer_cyberpunk(draw, slide_data.get('footer', 'THE GREATEST AI INVESTMENT'), f"{time_start} – {time_end}", f"{page:02d} / {total:02d}")

def render_newspaper_slide(draw, img, slide_data, time_start, time_end, page, total):
    y = 72
    if slide_data.get('kicker'):
        draw_kicker_newspaper(draw, slide_data['kicker'])
        y = 120
    if slide_data.get('display'):
        parts = slide_data['display'].split('\n')
        dy = y
        for part in parts:
            draw_display_newspaper(draw, part.strip(), y=dy, font_size=92)
            dy += 92
        y = dy + 20
    if slide_data.get('headline'):
        draw_headline_newspaper(draw, slide_data['headline'], y=y+10, font_size=56)
        y += 110
    if slide_data.get('stat'):
        draw_stat_card_newspaper(draw, 88, y, 400, 180)
        draw_stat_number_newspaper(draw, slide_data['stat'], 120, y+20, font_size=96)
        if slide_data.get('stat_label'):
            draw_stat_label_newspaper(draw, slide_data['stat_label'], 120, y+120, color=MUTED, font_size=16)
        y += 200
    if slide_data.get('body'):
        draw_body_newspaper(draw, slide_data['body'], 88, y, font_size=18, max_width=900)
        y += 180
    if slide_data.get('quote'):
        draw_quote_newspaper(draw, slide_data['quote'], 88, y, font_size=24, max_width=900)
    draw_footer_newspaper(draw, slide_data.get('footer', 'FT WEEKEND STYLE'), f"{time_start} – {time_end}", f"{page:02d} / {total:02d}")

def generate_slides(html_path: Path, output_dir: Path, theme: str, timings: list):
    output_dir.mkdir(parents=True, exist_ok=True)

    if theme == "cyberpunk":
        slide_datas = parse_html_for_cyberpunk_slides(html_path)
    else:
        slide_datas = parse_html_for_newspaper_slides(html_path)

    total = len(slide_datas)
    for i, slide_data in enumerate(slide_datas):
        if theme == "cyberpunk":
            img = Image.new('RGB', (WIDTH, HEIGHT), BG)
            img = draw_gradient_bg(img)
            img = draw_grid(img, alpha=10)
            draw = ImageDraw.Draw(img)
            ts = timings[i] if i < len(timings) else (0.0, 0.0)
            time_start = f"{int(ts[0]//60):02d}:{int(ts[0]%60):02d}"
            time_end = f"{int(ts[1]//60):02d}:{int(ts[1]%60):02d}"
            render_cyberpunk_slide(draw, img, slide_data, time_start, time_end, i+1, total)
        else:
            img = Image.new('RGB', (WIDTH, HEIGHT), BG_PAPER)
            draw = ImageDraw.Draw(img)
            ts = timings[i] if i < len(timings) else (0.0, 0.0)
            time_start = f"{int(ts[0]//60):02d}:{int(ts[0]%60):02d}"
            time_end = f"{int(ts[1]//60):02d}:{int(ts[1]%60):02d}"
            render_newspaper_slide(draw, img, slide_data, time_start, time_end, i+1, total)

        out_path = output_dir / f"slide_{i+1:02d}.png"
        img.save(out_path, "PNG")
        print(f"  [{i+1}/{total}] {out_path.name}" + (f" ({ts[1]-ts[0]:.0f}s)" if ts[0] or ts[1] else ""))

    return slide_datas

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    html_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    if not html_path.exists():
        print(f"错误: HTML 文件不存在: {html_path}")
        sys.exit(1)

    theme = detect_theme(html_path)
    timings = parse_slide_timings_from_html(html_path)
    slide_count = len(timings) if timings else 9
    if not timings:
        timings = [(0.0, 0.0)] * slide_count

    print(f"渲染 HTML PPT -> {output_dir}/")
    print(f"  主题: {theme}")
    print(f"  页数: {slide_count}")
    if any(ts[0] > 0 or ts[1] > 0 for ts in timings):
        print(f"  时间范围:")
        for i, (s, e) in enumerate(timings):
            if s > 0 or e > 0:
                print(f"    第{i+1}页: {s:.1f}s - {e:.1f}s (时长 {e-s:.1f}s)")

    generate_slides(html_path, output_dir, theme, timings)
    print(f"\n完成! 共 {slide_count} 页幻灯片")
    
    print(f"\n校验生成结果...")
    validation = validate_slides_output(output_dir)
    print(f"  唯一性检查: {validation['uniqueness']['unique']}/{validation['uniqueness']['total']} 张唯一")
    if validation['uniqueness']['duplicates']:
        print(f"  ⚠️ 发现重复幻灯片:")
        for dup_name, orig_name in validation['uniqueness']['duplicates']:
            print(f"     {dup_name} 与 {orig_name} 内容相同")
    for check in validation['resolution_check']:
        status = "✓" if check['valid'] else "✗"
        print(f"  [{status}] {check['file']}: {check['size']}")
    if validation['issues']:
        print(f"\n⚠️ 发现问题:")
        for issue in validation['issues']:
            print(f"  - {issue}")
        print(f"\n常见原因:")
        print(f"  - HTML解析问题: 检查 render_slides.py 的 parse_html_for_cyberpunk_slides 函数")
        print(f"  - 正则表达式问题: 确保 HTML 中每个 slide 的 class 属性格式正确")
    else:
        print(f"\n✓ 所有检查通过!")

if __name__ == "__main__":
    main()