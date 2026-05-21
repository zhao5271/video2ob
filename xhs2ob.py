import asyncio
import os
import sys
import datetime
import json
from dotenv import load_dotenv
from extractor import XHSExtractor
from transcriber import Transcriber, format_timestamp

# Load environment variables (like HF_TOKEN)
load_dotenv()

# Configuration
OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", "./output")
MODEL_SIZE = "large-v3-turbo" # Balanced for M1 Pro

class XHS2Obsidian:
    def __init__(self, vault_path):
        self.vault_path = vault_path
        self.extractor = XHSExtractor()
        self.transcriber = Transcriber(model_size=MODEL_SIZE)

    async def process(self, url):
        # 1. Extract Info
        info = await self.extractor.get_video_info(url)
        if not info["video_url"]:
            print("Error: Could not find video URL.")
            return

        # 2. Setup Paths
        assets_dir = os.path.join(self.vault_path, "Assets", "Videos")
        os.makedirs(assets_dir, exist_ok=True)
        
        safe_base_name = self.get_safe_filename(info).replace(".md", "")
        video_filename = f"{safe_base_name}.mp4"
        video_path = os.path.join(assets_dir, video_filename)

        # 3. Download Video (Permanently to Vault)
        if not os.path.exists(video_path):
            print(f"Downloading video to assets: {video_filename}...")
            await self.extractor.download_video(info["video_url"], video_path)
        else:
            print(f"Video already exists in assets: {video_filename}")

        # 4. Transcribe (Using the local vault video)
        temp_audio = "temp_audio.wav"
        self.transcriber.extract_audio(video_path, temp_audio)
        segments = self.transcriber.transcribe(temp_audio)

        # 5. Format Markdown (Linking to local video)
        md_content = self.generate_md(info, segments, video_filename)

        # 6. Save to Obsidian
        filename = f"{safe_base_name}.md"
        output_path = os.path.join(self.vault_path, filename)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        print(f"\nDone! Note saved to: {output_path}")

        # Cleanup temp audio
        if os.path.exists(temp_audio): os.remove(temp_audio)

    def generate_md(self, info, segments, video_filename):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # YAML Properties (Obsidian Standard)
        yaml = [
            "---",
            f"title: \"{info['title']}\"",
            f"date: {now}",
            f"author: \"{info['author']}\"",
            f"source: \"{info['page_url']}\"",
            f"video_file: \"[[Assets/Videos/{video_filename}]]\"",
            "tags: [xiaohongshu, video-note, AI笔记]",
            f"category: AI笔记",
            "---\n"
        ]
        
        # Header with Abstract
        body = [
            f"# {info['title']}\n",
            "> [!ABSTRACT] 内容摘要",
            f"> {info['desc'] if info['desc'] else '本视频由 ' + info['author'] + ' 分享。'}\n",
            "## 📽️ 本地视频回放",
            f"![[{video_filename}]]\n",
            "---",
            "\n## 📝 结构化笔记内容\n"
        ]
        
        # Smart Aggregation and Titling
        blocks = []
        if segments:
            current_block = {"start": segments[0]["start"], "text": ""}
            for i, s in enumerate(segments):
                text = s["text"].strip()
                if not text: continue
                
                time_gap = s["start"] - segments[i-1]["end"] if i > 0 else 0
                # Heuristic for new section: gap > 4s or typical step keywords
                is_new_step = any(kw in text[:20] for kw in ["第一", "第二", "第三", "最后", "首先", "总结", "注意"])
                
                if (time_gap > 4.0 or is_new_step or len(current_block["text"]) > 500) and current_block["text"]:
                    blocks.append(current_block)
                    current_block = {"start": s["start"], "text": text}
                else:
                    current_block["text"] = (current_block["text"] + " " + text).strip()
            blocks.append(current_block)

        # Build Body with Title Logic
        for i, b in enumerate(blocks):
            ts = format_timestamp(b['start'])
            link = f"{video_filename}#t={int(b['start'])}"
            
            # Try to extract a short title from the first sentence
            first_sentence = b['text'].split('。')[0]
            if len(first_sentence) < 30 and any(kw in first_sentence for kw in ["步", "首先", "介绍", "安装", "配置", "总结"]):
                body.append(f"### [[{link}|{ts}]] {first_sentence}\n")
                # Remove the title from text to avoid duplication
                remaining_text = b['text'][len(first_sentence)+1:].strip()
                if remaining_text: body.append(f"{remaining_text}\n")
            else:
                body.append(f"### [[{link}|{ts}]] 节点记录\n")
                body.append(f"{b['text']}\n")
            
        # Add Knowledge Summary Table Placeholder
        body.append("\n## 🎯 知识小结")
        body.append("| 关键环节 | 核心要点 |")
        body.append("| :--- | :--- |")
        body.append("| 配置 | (请在此补充) |")
        body.append("| 操作 | (请在此补充) |\n")

        body.append("## 资料来源")
        body.append(f"- [小红书原视频]({info['page_url']}) - 访问日期：{datetime.datetime.now().strftime('%Y-%m-%d')}")
            
        return "\n".join(yaml + body)

    def get_safe_filename(self, info):
        title = info['title'] or "Untitled"
        # Remove illegal characters for filenames
        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-')]).strip()
        safe_title = safe_title[:50] # Limit length
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        return f"{date_str}_{safe_title}.md"

async def main():
    if len(sys.argv) < 2:
        print("Usage: python xhs2ob.py <xhs_url>")
        return
    
    url = sys.argv[1]
    app = XHS2Obsidian(OBSIDIAN_VAULT_PATH)
    await app.process(url)

if __name__ == "__main__":
    asyncio.run(main())
