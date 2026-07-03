import os
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DB_PATH = os.getenv("DB_PATH", "bot_data.db")
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Asia/Kolkata"))  # IST by default

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in your .env file!")
if not GEMINI_API_KEY or GEMINI_API_KEY == "your_google_ai_studio_api_key_here":
    raise ValueError("GEMINI_API_KEY is not set in your .env file! Get one free at https://aistudio.google.com/")
