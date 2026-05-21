import asyncio
import re
import json
import httpx
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

class BilibiliExtractor:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/"
        }

    async def get_video_info(self, url):
        print(f"Extracting Bilibili info via yt-dlp from: {url}")
        
        import subprocess
        import json
        
        # Use yt-dlp to get all info in one go
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-playlist",
            url
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {
                    "title": data.get("title", "Bilibili Video"),
                    "desc": data.get("description", ""),
                    "author": data.get("uploader", "Unknown"),
                    "video_url": url, 
                    "page_url": data.get("webpage_url", url)
                }
        except Exception as e:
            print(f"yt-dlp extraction failed: {e}")

        return await self._fallback_get_info(url)

    async def _fallback_get_info(self, url):
        if "b23.tv" in url:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
                resp = await client.get(url)
                url = str(resp.url)

        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(user_agent=self.headers["User-Agent"])
                await page.goto(url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(3)
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                title = ""
                title_tag = soup.find('meta', property="og:title") or soup.find('h1', class_="video-title")
                if title_tag:
                    title = title_tag.get('content') or title_tag.get_text()
                    title = title.replace("_哔哩哔哩_bilibili", "").strip()

                desc = ""
                desc_tag = soup.find('meta', property="og:description") or soup.find('span', class_="desc-info-text")
                if desc_tag:
                    desc = desc_tag.get('content') or desc_tag.get_text()

                author = "Unknown"
                author_tag = soup.find('meta', property="og:author") or soup.find('a', class_="up-name")
                if author_tag:
                    author = author_tag.get('content') or author_tag.get_text().strip()

                await browser.close()
                return {
                    "title": title or "Bilibili Video",
                    "desc": desc or "",
                    "author": author,
                    "video_url": url,
                    "page_url": url
                }
            except Exception as e:
                print(f"Fallback extraction failed: {e}")
                return {"title": "Bilibili Video", "desc": "", "author": "Unknown", "video_url": url, "page_url": url}

    async def download_video(self, url, output_path):
        import subprocess
        print(f"Downloading Bilibili video via yt-dlp...")
        cmd = [
            "yt-dlp",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o", output_path,
            url
        ]
        subprocess.run(cmd, check=True)
