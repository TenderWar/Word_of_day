import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Шляхи
BASE_DIR = Path(__file__).parent
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "./data/bot.db"))
DICTIONARY_PATH = Path(os.getenv("DICTIONARY_PATH", "./dictionary.json"))
TTS_CACHE_DIR = Path(os.getenv("TTS_CACHE_DIR", "./tts_cache"))

# Налаштування за замовчуванням
DEFAULT_NOTIFY_TIME = os.getenv("DEFAULT_NOTIFY_TIME", "09:00")
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Europe/Kyiv")

# Створення директорій при імпорті
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
