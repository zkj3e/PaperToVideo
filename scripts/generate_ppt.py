import os
import sys
import json
from openai import OpenAI

def load_config():
    """从配置文件加载 API Key"""
    config_path = os.path.join(os.path.dirname(__file__), ".runninghub_config.json")
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    return {}

config = load_config()
deepseek_key = config.get("deepseek_api_key", "") or os.getenv("DEEPSEEK_API_KEY", "")

if not deepseek_key:
    print("错误: 未配置 DeepSeek API Key")
    print("请在 scripts/.runninghub_config.json 中添加 deepseek_api_key")
    sys.exit(1)

os.environ["OPENAI_API_KEY"] = deepseek_key

client = OpenAI(
    api_key=deepseek_key,
    base_url="https://api.deepseek.com"
)

def get_audio_duration(audio_path: str) -> float:
    """使用 ffprobe 获取音频时长（秒）"""
    import subprocess
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def generate_ppt(original_text: str, num_pages: int) -> str:
    prompt = f"""You are a professional AI presentation generator. Generate a cyberpunk-style HTML slideshow based on the user's text.

【User Text】
{original_text}

【Requirements】
- Number of slides: {num_pages} pages
- Dimensions: 1280x720
- No navigation buttons, no page numbers
- Only dot indicators at the bottom (clickable to switch)
- Support keyboard left/right arrows
- Cyberpunk visual style (neon borders, frosted glass, grid background, cyan/magenta colors)
- Each page contains: badge, title, 3-4 concise bullet points, a quote, right-side visual area (real images from free image libraries like Unsplash/Pexels with high quality + brief image caption)
- IMPORTANT: Detect the language of the user's text and generate ALL content (titles, bullet points, quotes, captions, UI elements) in the SAME language. If the text is in English, generate everything in English; if Chinese, generate in Chinese; etc.
- Image fallback: Use high-quality images from any reliable free image library (Unsplash, Pexels, Pixabay, etc. - use ?w=800 for higher resolution), and set onerror callback to display a cyberpunk-themed emoji (like 🤖, 🌃, 💻, 🚀, 🔮) when image fails to load. The emoji should be displayed with a neon glow effect.
- Output must be complete, self-contained HTML code wrapped in ```html```

Generate code that can run directly in a browser."""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a senior frontend engineer + PPT designer. Output HTML code following the specification. Detect the input language and generate all content in that same language. Do not add extra explanations."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=8000
    )

    html_code = response.choices[0].message.content
    # 提取 ```html ... ``` 之间的内容
    if "```html" in html_code:
        html_code = html_code.split("```html")[1].split("```")[0].strip()
    return html_code

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 generate_ppt.py <文本文件路径> [音频文件路径]")
        print("  若提供音频文件，自动按每分钟4页计算页数")
        sys.exit(1)
    
    txt_path = sys.argv[1]
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    # 计算页数：每分钟4页
    pages = 5
    if len(sys.argv) >= 3:
        audio_path = sys.argv[2]
        if os.path.exists(audio_path):
            duration = get_audio_duration(audio_path)
            pages = max(1, int(duration / 60 * 4))
    
    print(f"文本长度: {len(text)} 字符, 生成 {pages} 页 PPT")
    result = generate_ppt(text, pages)
    
    output_path = txt_path.replace(".txt", ".html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"已生成 {output_path}")