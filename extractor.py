import asyncio
import re
import json
import httpx
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

class XHSExtractor:
    def __init__(self):
        # Using desktop UA which worked with curl
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    async def get_video_info(self, url):
        # Try httpx first
        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=30.0) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 200 and "window.__INITIAL_STATE__" in resp.text:
                    info = self._parse_html(resp.text, str(resp.url))
                    if info["video_url"]:
                        print("Successfully extracted info via httpx.")
                        return info
            except: pass

        # Fallback to curl (surprisingly effective)
        try:
            import subprocess
            cmd = ["curl", "-L", "-A", self.headers["User-Agent"], url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and "window.__INITIAL_STATE__" in result.stdout:
                print("Successfully extracted info via curl.")
                return self._parse_html(result.stdout, url)
        except: pass

        # Fallback to Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.headers["User-Agent"],
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()
            print(f"Loading URL via Playwright: {url}")
            try:
                await page.goto(url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(2)
                content = await page.content()
                info = self._parse_html(content, page.url)
            except Exception as e:
                print(f"Playwright error: {e}")
                info = {"title": "", "desc": "", "author": "", "video_url": "", "page_url": url}
            finally:
                await browser.close()
            return info

    def _parse_html(self, html, page_url):
        soup = BeautifulSoup(html, 'html.parser')
        scripts = soup.find_all('script')
        initial_state = None
        
        for s in scripts:
            script_text = s.string or s.text or ""
            if not script_text: continue
            
            target = None
            if 'window.__INITIAL_STATE__=' in script_text:
                target = 'window.__INITIAL_STATE__='
            elif 'window.__INITIAL_DATA__=' in script_text:
                target = 'window.__INITIAL_DATA__='
            
            if target:
                try:
                    content_str = script_text.split(target)[1]
                    start_idx = content_str.find('{')
                    if start_idx != -1:
                        count = 0
                        for i in range(start_idx, len(content_str)):
                            if content_str[i] == '{': count += 1
                            elif content_str[i] == '}': count -= 1
                            if count == 0:
                                json_str = content_str[start_idx:i+1]
                                # Handle non-standard JS 'undefined' in state
                                json_str = json_str.replace(':undefined', ':null')
                                initial_state = json.loads(json_str)
                                break
                except Exception as e:
                    print(f"JSON load error: {e}")
                if initial_state: break

        info = {
            "title": "",
            "desc": "",
            "author": "",
            "video_url": "",
            "page_url": page_url,
            "note_id": ""
        }

        if initial_state:
            try:
                # Common XHS state structures
                note_id = initial_state.get('note', {}).get('currentNoteId')
                if not note_id and 'noteData' in initial_state:
                    note_id = initial_state['noteData'].get('noteId') or initial_state['noteData'].get('id')
                
                info["note_id"] = note_id
                if note_id:
                    info["page_url"] = f"https://www.xiaohongshu.com/explore/{note_id}"

                note_data = initial_state.get('note', {}).get('noteDetailMap', {}).get(note_id, {}).get('note', {})
                if not note_data:
                    note_data = initial_state.get('noteData', {}) or initial_state.get('note', {})
                
                # Check for nested note
                if 'note' in note_data and isinstance(note_data['note'], dict):
                    note_data = note_data['note']

                info["title"] = note_data.get('title', '')
                info["desc"] = note_data.get('desc', '')
                info["author"] = note_data.get('user', {}).get('nickname', '')
                
                # Extract Video URL
                video = note_data.get('video', {})
                if video:
                    # Path 1: media.video.mediaList
                    media_list = video.get('media', {}).get('video', {}).get('mediaList', [])
                    if not media_list and 'stream' in video:
                        # Path 2: stream.h264
                        media_list = video.get('stream', {}).get('h264', []) or video.get('stream', {}).get('h265', [])
                    
                    if media_list:
                        # Try to find 'masterUrl' or 'url'
                        info["video_url"] = media_list[0].get('masterUrl', '') or media_list[0].get('url', '')
                
                # Deep Search Fallback
                if not info["video_url"]:
                    def find_mp4(obj):
                        if isinstance(obj, str) and (obj.startswith('http') and ('.mp4' in obj or 'video' in obj)):
                            return obj
                        if isinstance(obj, dict):
                            for v in obj.values():
                                res = find_mp4(v)
                                if res: return res
                        if isinstance(obj, list):
                            for i in obj:
                                res = find_mp4(i)
                                if res: return res
                        return None
                    info["video_url"] = find_mp4(initial_state)

            except Exception as e:
                print(f"Parsing error: {e}")

        # Final Fallback: Meta tags
        if not info["title"]:
            title_tag = soup.find('meta', property="og:title")
            if title_tag: info["title"] = title_tag.get('content', '')
        
        if not info["video_url"]:
            video_tag = soup.find('video')
            if video_tag and video_tag.get('src') and not video_tag['src'].startswith('blob:'):
                info["video_url"] = video_tag['src']

        return info

    async def download_video(self, video_url, output_path):
        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
            resp = await client.get(video_url)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            print(f"Video downloaded to: {output_path}")

async def main():
    import sys
    import os
    if len(sys.argv) < 2:
        print("Usage: python extractor.py <url> [output_path]")
        return
    
    url = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "video.mp4"
    
    extractor = XHSExtractor()
    info = await extractor.get_video_info(url)
    print(json.dumps(info, indent=2, ensure_ascii=False))
    
    if info["video_url"]:
        await extractor.download_video(info["video_url"], output_path)
    else:
        print("No video URL found.")

if __name__ == "__main__":
    asyncio.run(main())
