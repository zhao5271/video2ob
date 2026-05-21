# 短视频转 Obsidian 笔记工具 (video2ob)

该工具可以将 **小红书**、**抖音** 或 **哔哩哔哩 (B站)** 的分享链接转换为带有时间戳、全文转录、本地视频回放以及 YAML 元数据的结构化 Obsidian 笔记。

## 核心特性
- **多平台支持**：自动识别小红书 (XHS)、抖音 (Douyin) 和 B站 (Bilibili) 链接（支持 b23.tv 短链）。
- **本地 ASR**：基于 `faster-whisper` (M1 Pro 优化)，保护隐私，无需 ASR API Key。
- **本地存储**：自动将视频下载至 Obsidian 的 `Assets/Videos` 目录，解决网页无法加载问题，支持 Media Extended 插件秒开。
- **结构化笔记**：采用 `gen-notes` 风格，自动提炼大纲、分段，并生成摘要和知识小结表。

## 快速开始

### 1. 环境准备与安装
确保已安装 `ffmpeg` 和 `yt-dlp` (可以通过 `brew install ffmpeg yt-dlp` 安装)。

```bash
git clone https://github.com/zhao5271/video2ob.git
cd video2ob
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置说明
复制 `.env.example` 为 `.env` 并填入必要信息：
- `HF_TOKEN`：Hugging Face 的 Token (用于下载 Whisper 模型)。
- `OBSIDIAN_VAULT_PATH`：您的 Obsidian 库绝对路径。

### 3. 设置别名 (Fish Shell 推荐)
```fish
alias v2ob='/Users/zhang/AI_Projects/xhs2ob/venv/bin/python /Users/zhang/AI_Projects/xhs2ob/video2ob.py'
funcsave v2ob
```
之后只需运行：`v2ob "URL"` 即可。

## Obsidian 建议配套插件
- **Media Extended**：用于支持本地视频的时间戳跳转。
- **Smart Connections / Copilot**：结合本工具生成的带元数据的 MD 文件，搭建个人 AI 知识库。
