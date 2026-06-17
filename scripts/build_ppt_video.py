#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据音频时长生成均分时长的 PPT 视频片段

用法:
    python3 scripts/build_ppt_video.py <png目录> <音频文件> <输出目录>

示例:
    python3 scripts/build_ppt_video.py "workspace/文章2/ppt_frames_browser" "workspace/文章2/数字人音频.flac" "workspace/文章2/ppt_video"
"""

import subprocess
import os
import sys
import json
from pathlib import Path

def get_audio_duration(audio_path: str) -> float:
    """使用 ffprobe 获取音频时长（秒）"""
    result = subprocess.run([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json',
        audio_path
    ], capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data['format']['duration'])

def count_png_files(png_dir: Path) -> int:
    """计算 PNG 文件数量"""
    return len(list(png_dir.glob('slide_*.png')))

def build_ppt_video(png_dir: str, audio_path: str, output_dir: str):
    """生成均分时长的 PPT 视频"""
    png_dir = Path(png_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 获取音频时长
    audio_duration = get_audio_duration(audio_path)
    print(f"音频时长: {audio_duration:.2f} 秒")

    # 计算幻灯片数量
    num_slides = count_png_files(png_dir)
    if num_slides == 0:
        print(f"错误: 在 {png_dir} 中未找到 slide_*.png 文件")
        sys.exit(1)
    print(f"幻灯片数量: {num_slides}")

    # 计算每张幻灯片时长
    duration_per_slide = audio_duration / num_slides
    print(f"每张幻灯片时长: {duration_per_slide:.2f} 秒")

    # 为每张幻灯片生成视频片段
    for i in range(1, num_slides + 1):
        slide_path = png_dir / f"slide_{i:02d}.png"
        segment_path = output_dir / f"segment_{i:02d}.mp4"

        if not slide_path.exists():
            print(f"警告: {slide_path} 不存在，跳过")
            continue

        subprocess.run([
            'ffmpeg', '-y',
            '-loop', '1',
            '-i', str(slide_path),
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '20',
            '-t', str(duration_per_slide),
            '-pix_fmt', 'yuv420p',
            '-r', '30',
            '-vf', f'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1',
            str(segment_path)
        ], capture_output=True)
        print(f"完成幻灯片 {i}/{num_slides}")

    print(f"\n视频片段已生成: {output_dir}")
    return num_slides, duration_per_slide

def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    png_dir = sys.argv[1]
    audio_path = sys.argv[2]
    output_dir = sys.argv[3]

    if not os.path.exists(png_dir):
        print(f"错误: PNG 目录不存在: {png_dir}")
        sys.exit(1)

    if not os.path.exists(audio_path):
        print(f"错误: 音频文件不存在: {audio_path}")
        sys.exit(1)

    build_ppt_video(png_dir, audio_path, output_dir)

if __name__ == "__main__":
    main()
