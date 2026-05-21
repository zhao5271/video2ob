import subprocess
import json
import re
import os
import asyncio
import time

class DouyinExtractor:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"

    async def get_video_info(self, url):
        print(f"Extracting Douyin info from: {url}")
        
        # 1. Open with playwright-cli to handle redirects and dynamic content
        session = f"douyin_{int(time.time())}"
        subprocess.run(["playwright-cli", "-s", session, "open", url], capture_output=True)
        # Wait for dynamic content to load and potential video to start
        time.sleep(7) # Increased wait for stability
        
        # 2. Get Metadata via JS evaluation
        title = self.run_eval(session, "document.title")
        if title:
            title = title.split(" - 抖音")[0].split("#")[0].strip()
        
        desc = self.run_eval(session, "document.querySelector('h1')?.textContent")
        author = self.run_eval(session, "document.querySelector('[data-e2e=user-info-name]')?.textContent") or "Unknown Author"
        
        # 3. Get Video/Audio URL from Network
        video_url = None
        network_logs = subprocess.run(["playwright-cli", "-s", session, "network"], capture_output=True, text=True).stdout
        
        # Douyin video patterns (Looking for video stream)
        video_patterns = [
            r'https://[^\s|]+mime_type=video_mp4[^\s|]+',
            r'https://v\d+-[^\s|]+',
            r'https://[^\s|]+v-watermark[^\s|]+'
        ]
        
        for pattern in video_patterns:
            matches = re.findall(pattern, network_logs)
            for match in matches:
                clean_url = match.split('|')[0].split('=>')[0].strip()
                # Prioritize video over audio in this list
                if "video" in clean_url or "v-watermark" in clean_url:
                    video_url = clean_url
                    break
            if video_url: break

        # Close session
        subprocess.run(["playwright-cli", "-s", session, "close"], capture_output=True)

        return {
            "title": title or "Douyin Video",
            "desc": desc or "",
            "author": author,
            "video_url": video_url,
            "page_url": url
        }

    def run_eval(self, session, js):
        res = subprocess.run(["playwright-cli", "-s", session, "eval", js], capture_output=True, text=True).stdout
        if "### Result" in res:
            val = res.split("### Result")[1].strip()
            if val.startswith('"') and val.endswith('"'):
                return val[1:-1]
            if val == "undefined":
                return None
            return val
        return None

    async def download_video(self, url, output_path):
        print(f"Downloading Douyin video...")
        cmd = [
            "curl", "-L", "-o", output_path, url,
            "-H", f"User-Agent: {self.user_agent}",
            "-H", "Referer: https://www.douyin.com/",
            "--silent"
        ]
        subprocess.run(cmd, check=True)

if __name__ == "__main__":
    # Test
    extractor = DouyinExtractor()
    info = asyncio.run(extractor.get_video_info("https://v.douyin.com/joZtN-uQojY/"))
    print(json.dumps(info, indent=2, ensure_ascii=False))
