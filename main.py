import os
import json
import time
import logging
import asyncio
import re
from datetime import datetime
import pytz
import feedparser
import httpx
from google import genai
from groq import Groq
from openai import OpenAI
from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv, set_key
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))
TIMEZONE = os.getenv("TIMEZONE", "UTC")
AI_PRIORITY = [p.strip().lower() for p in os.getenv("AI_PRIORITY", "sambanova,groq,gemini").split(",")]
CAT_API_KEY = os.getenv("CAT_API_KEY")

# API Keys
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
SAMBANOVA_KEY = os.getenv("SAMBANOVA_API_KEY")
SAMBANOVA_MODEL = os.getenv("SAMBANOVA_MODEL", "DeepSeek-V3.1")

# State and Repos
STATE_FILE = "state.json"
REPOS = {
    "Proxmox Backup": os.getenv("PROXMOX_BACKUP_RSS"),
    "PVE Manager": os.getenv("PVE_MANAGER_RSS")
}

AI_CLIENTS = {}

def init_ai_clients():
    if GEMINI_KEY and "AIza" in GEMINI_KEY:
        try:
            AI_CLIENTS['gemini'] = genai.Client(api_key=GEMINI_KEY)
        except: pass
    if GROQ_KEY and "gsk_" in GROQ_KEY:
        try: AI_CLIENTS['groq'] = Groq(api_key=GROQ_KEY)
        except: pass
    if SAMBANOVA_KEY and "-" in SAMBANOVA_KEY:
        try:
            AI_CLIENTS['sambanova'] = OpenAI(api_key=SAMBANOVA_KEY, base_url="https://api.sambanova.ai/v1")
        except: pass

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f: return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=4)

def format_date(date_str):
    try:
        dt = parsedate_to_datetime(date_str)
        local_tz = pytz.timezone(TIMEZONE)
        return dt.astimezone(local_tz).strftime("%d/%m/%Y %H:%M")
    except: return date_str

def is_version_bump(title, diff_text):
    # Detecta específicamente "bump version to X.Y.Z" o variaciones similares con números
    if re.search(r"bump version (to )?[\d\.\-]+", title, re.IGNORECASE):
        return True
    
    # También detecta cambios directos en archivos de versión (como el archivo VERSION de proxmox)
    if diff_text and (re.search(r"\+VERSION\s*=\s*[\d\.\-]+", diff_text) or re.search(r"\+version:\s*[\d\.\-]+", diff_text)):
        return True
        
    return False

async def get_cat_image():
    """Fetch a random cat image URL from The Cat API."""
    url = "https://api.thecatapi.com/v1/images/search"
    headers = {"x-api-key": CAT_API_KEY}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data[0]['url']
        except Exception as e:
            logger.error(f"Error fetching cat: {e}")
    return None

async def get_commit_diff(commit_url):
    diff_url = commit_url.replace("a=commit;", "a=commitdiff;")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(diff_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            page_body = soup.find('div', class_='page_body')
            return page_body.get_text()[:15000] if page_body else None
        except: return None

async def summarize_with_fallback(diff_text):
    prompt = (
        "Analiza este git commitdiff de Proxmox y explica brevemente en español "
        "qué cambió y cómo afecta al usuario. Sé conciso.\n\n"
        f"DIFF:\n{diff_text}"
    )
    for provider in AI_PRIORITY:
        if provider in AI_CLIENTS:
            try:
                if provider == 'gemini':
                    res = await asyncio.to_thread(
                        AI_CLIENTS['gemini'].models.generate_content,
                        model='gemini-2.0-flash',
                        contents=prompt
                    )
                    if res.text: return res.text, provider
                elif provider == 'groq':
                    res = await asyncio.to_thread(AI_CLIENTS['groq'].chat.completions.create, messages=[{"role": "user", "content": prompt}], model=GROQ_MODEL)
                    if res.choices[0].message.content: return res.choices[0].message.content, provider
                elif provider == 'sambanova':
                    res = await asyncio.to_thread(AI_CLIENTS['sambanova'].chat.completions.create, messages=[{"role": "user", "content": prompt}], model=SAMBANOVA_MODEL)
                    if res.choices[0].message.content: return res.choices[0].message.content, provider
            except: continue
    return "Resumen no disponible.", "None"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    state = context.bot_data["state"]
    state["chat_id"] = chat_id
    save_state(state)
    
    # Attempt to update .env as well for persistence
    try:
        set_key(".env", "TELEGRAM_CHAT_ID", chat_id)
    except Exception as e:
        logger.error(f"Could not update .env: {e}")
        
    await update.message.reply_text(
        f"✅ ¡Bot vinculado exitosamente a este chat!\n"
        f"ID del Chat: {chat_id}\n\n"
        f"Comenzaré a monitorear Proxmox y enviaré las notificaciones aquí."
    )

async def check_updates_task(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    state = context.bot_data["state"]
    chat_id = state.get("chat_id") or os.getenv("TELEGRAM_CHAT_ID")
    
    if not chat_id:
        return # Skip if no chat ID is set yet
        
    for repo_name, rss_url in REPOS.items():
        feed = feedparser.parse(rss_url)
        if not feed.entries: continue
        last_seen = state.get(repo_name)
        
        to_process = []
        for e in feed.entries:
            if e.id == last_seen: break
            to_process.append(e)
        to_process.reverse()

        for entry in to_process:
            diff_text = await get_commit_diff(entry.link)
            summary, provider = await summarize_with_fallback(diff_text)
            is_bump = is_version_bump(entry.title, diff_text)
            local_time = format_date(entry.published)
            
            # Clean format
            header = "🌟 NUEVA VERSIÓN" if is_bump else "🔹 Novedad en Proxmox"
            message = (
                f"{header}\n"
                f"Repo: {repo_name}\n"
                f"Commit: {entry.title}\n"
                f"Autor: {entry.author if 'author' in entry else '?'}\n"
                f"Fecha: {local_time}\n\n"
                f"Análisis ({provider.upper()}):\n{summary}\n\n"
                f"Link: {entry.link}"
            )

            try:
                if is_bump:
                    cat_url = await get_cat_image()
                    if cat_url:
                        await bot.send_photo(chat_id=chat_id, photo=cat_url, caption=message[:1024], parse_mode=None)
                    else:
                        await bot.send_message(chat_id=chat_id, text=message, parse_mode=None)
                else:
                    await bot.send_message(chat_id=chat_id, text=message, parse_mode=None)
                
                state[repo_name] = entry.id
                save_state(state)
            except Exception as e:
                logger.error(f"Send error: {e}")

def main():
    init_ai_clients()
    state = load_state()
    for repo_name, rss_url in REPOS.items():
        if repo_name not in state:
            feed = feedparser.parse(rss_url)
            if feed.entries: state[repo_name] = feed.entries[0].id
    save_state(state)
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.bot_data["state"] = state
    app.add_handler(CommandHandler("start", start_command))
    
    app.job_queue.run_repeating(check_updates_task, interval=CHECK_INTERVAL, first=5)
    
    logger.info("Bot activo y esperando comandos...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
