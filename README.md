# Prox-Noty: Proxmox Git RSS Notifier & AI Summarizer

Prox-Noty is an intelligent Telegram bot designed to monitor Proxmox repositories (or any Gitweb RSS feeds) and notify you of new commits. It goes beyond simple notifications by downloading the commit code diffs and using Artificial Intelligence to provide clear, contextualized summaries of the changes.

## Features
- 🔄 **Real-Time Polling**: Monitors Gitweb RSS feeds without needing a webhook server.
- 🧠 **AI Fallback System**: Supports multiple AI providers (SambaNova, Groq, Gemini) with a priority fallback mechanism. If one API fails, the bot seamlessly tries the next.
- 🔖 **Version Bump Detection**: Automatically detects version bumps (e.g., `bump version to 9.1.10`) and highlights them.
- 🐱 **The Cat API Integration**: Celebrates new version releases by sending a random cat image alongside the notification!
- 🕒 **Timezone Conversion**: Converts UTC repository timestamps to your preferred local timezone.

---

## 🛠️ Setup Instructions

### 1. Requirements
- Python 3.12+
- `uv` (Recommended) or `pip`

### 2. Installation
Clone the repository and install the dependencies:
```bash
uv sync # If using uv
# OR
pip install -r requirements.txt # (You can generate this if needed)
```
*(Dependencies: `python-telegram-bot`, `httpx`, `feedparser`, `beautifulsoup4`, `python-dotenv`, `google-generativeai`, `groq`, `openai`, `pytz`)*

### 3. Configuration
1. Copy the template `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in your keys. **Do not commit your `.env` to Git!**

### 4. Running the Bot
Run the bot locally or deploy it to a server/VPS:
```bash
uv run python main.py
```

---

## 🤖 AI Providers & Models Configuration

This bot is designed to be resilient. You can define your preferred order of AI execution using the `AI_PRIORITY` variable in `.env`.

> [!TIP]
> You do **not** need all three providers. If you only have one API key (e.g., Groq), just leave the others empty. The bot will automatically ignore missing keys.

### Known Issues & Troubleshooting with AI Providers

#### SambaNova (`sambanova`)
SambaNova frequently updates their free models and occasionally deprecates older ones. 
- **Error:** `410 GONE` or "The requested model is not available".
- **Fix:** SambaNova has removed the model you configured (e.g., `Meta-Llama-3.1-70B`). Go to [SambaNova Cloud](https://cloud.sambanova.ai/), check their currently available models, and update `SAMBANOVA_MODEL` in your `.env` (e.g., change to `DeepSeek-V3.1`).

#### Groq (`groq`)
Groq is extremely fast but has strict rate limits on the free tier.
- **Error:** `429 TOO MANY REQUESTS`.
- **Fix:** This usually happens if you restart the bot too many times in a short period during testing. In production (polling every 5 minutes), you should rarely hit this. If it happens, the bot will automatically fall back to the next provider.

#### Gemini (`gemini`)
Google's Gemini 2.0 Flash is a great fallback but also enforces rate limits.
- **Error:** `429 RESOURCE_EXHAUSTED`.
- **Fix:** Similar to Groq, wait a minute before sending another request.

---

## 🔖 Cat API Integration
The bot uses The Cat API to fetch a random image for "Version Bump" commits. 
Get your free API key at [TheCatAPI](https://thecatapi.com/) and paste it in `CAT_API_KEY`. If left blank or if it fails, the bot will simply send the notification as a regular text message without the image.
