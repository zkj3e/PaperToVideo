#!/usr/bin/env python3
"""SRT字幕转文章脚本"""

import sys
import os
import re

def parse_srt(srt_path: str) -> list:
    """解析SRT文件"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\d+\n', content)
    subtitles = []
    
    for block in blocks:
        if block.strip():
            lines = block.strip().split('\n')
            if len(lines) >= 2:
                text = ' '.join(lines[1:])
                subtitles.append(text)
    
    return subtitles

def subtitles_to_article(subtitles: list, lang: str = 'zh') -> str:
    """将字幕合并为文章"""
    if lang == 'zh':
        return '\n\n'.join(subtitles)
    else:
        # 英文需要在句子间加空格
        text = ' '.join(subtitles)
        # 修复句号后无空格问题
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        return text

def main():
    if len(sys.argv) < 2:
        print("用法: python3 srt_to_article.py <srt文件路径>")
        sys.exit(1)
    
    srt_path = sys.argv[1]
    if not os.path.exists(srt_path):
        print(f"文件不存在: {srt_path}")
        sys.exit(1)
    
    # 检测语言
    lang = 'zh' if srt_path.endswith('.srt') or 'zh-cn' in srt_path else 'en'
    
    # 解析并转换
    subtitles = parse_srt(srt_path)
    article = subtitles_to_article(subtitles, lang)
    
    # 输出到同级的CN或EN目录
    base_dir = os.path.dirname(srt_path)
    parent_dir = os.path.dirname(base_dir)
    
    if 'CN' in base_dir:
        output_dir = os.path.join(parent_dir, 'CN')
    elif 'EN' in base_dir:
        output_dir = os.path.join(parent_dir, 'EN')
    else:
        # 尝试创建CN目录
        output_dir = os.path.join(base_dir, 'CN')
    
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, 'article.txt')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(article)
    
    print(f"已生成: {output_path}")
    print(f"字幕数量: {len(subtitles)}, 字符数: {len(article)}")

if __name__ == '__main__':
    main()
