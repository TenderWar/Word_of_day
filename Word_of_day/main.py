import logging
import asyncio

from telegram.ext import Application

import config
from db import Database
from dictionary import dictionary
from services import GeminiService, TTSService, CacheService
from scheduler import NotificationScheduler
from handlers import (
    setup_start_handlers,
    setup_word_handlers,
    setup_quiz_handlers,
    setup_stats_handlers,
    setup_settings_handlers,
)

# Налаштування логування
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Ініціалізація після запуску бота."""
    # Підключення до БД
    db = Database()
    await db.connect()
    application.bot_data["db"] = db

    # Ініціалізація сервісів
    cache = CacheService(db)
    gemini = GeminiService(cache)
    tts = TTSService()

    application.bot_data["cache"] = cache
    application.bot_data["gemini"] = gemini
    application.bot_data["tts"] = tts

    # Запуск планувальника
    scheduler = NotificationScheduler(application.bot, db, gemini)
    await scheduler.start()
    application.bot_data["scheduler"] = scheduler

    logger.info("Bot uspishno zapushcheno")


async def post_shutdown(application: Application) -> None:
    """Очистка при зупинці бота."""
    # Зупинка планувальника
    scheduler = application.bot_data.get("scheduler")
    if scheduler:
        scheduler.stop()

    # Закриття БД
    db = application.bot_data.get("db")
    if db:
        await db.close()

    logger.info("Bot zupyneno")


def main() -> None:
    """Точка входу."""
    # Перевірка конфігурації
    if not config.TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN ne vstanovleno v .env")

    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY ne vstanovleno v .env")

    # Завантаження словника
    try:
        dictionary.load()
        logger.info(f"Slovnyk zavantazheno: {len(dictionary.words)} sliv")
    except Exception as e:
        logger.error(f"Pomylka zavantazhennia slovnyka: {e}")
        raise

    # Створення додатку
    application = (
        Application.builder()
        .token(config.TELEGRAM_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Реєстрація хендлерів
    setup_start_handlers(application)
    setup_word_handlers(application)
    setup_quiz_handlers(application)
    setup_stats_handlers(application)
    setup_settings_handlers(application)

    # Запуск бота
    logger.info("Zapusk bota...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
