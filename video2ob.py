import asyncio
import sys
import os
from dotenv import load_dotenv

# Import our existing components
from xhs2ob import XHS2Obsidian
from douyin2ob import Douyin2Obsidian
from bilibili2ob import Bilibili2Obsidian

# Configuration
OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", "./output")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python video2ob.py <url>")
        print("Supported platforms: Xiaohongshu (xhs), Douyin, Bilibili")
        return

    url = sys.argv[1]
    
    # Simple platform detection
    if "xiaohongshu.com" in url or "xhslink.com" in url:
        print("Detected platform: Xiaohongshu")
        app = XHS2Obsidian(OBSIDIAN_VAULT_PATH)
    elif "douyin.com" in url or "iesdouyin.com" in url:
        print("Detected platform: Douyin")
        app = Douyin2Obsidian(OBSIDIAN_VAULT_PATH)
    elif "bilibili.com" in url or "b23.tv" in url:
        print("Detected platform: Bilibili")
        app = Bilibili2Obsidian(OBSIDIAN_VAULT_PATH)
    else:
        print("Unknown platform. Attempting generic Douyin extractor as fallback...")
        app = Douyin2Obsidian(OBSIDIAN_VAULT_PATH)

    try:
        await app.process(url)
    except Exception as e:
        print(f"Error processing video: {e}")

if __name__ == "__main__":
    # Ensure dependencies are loaded
    load_dotenv()
    asyncio.run(main())
