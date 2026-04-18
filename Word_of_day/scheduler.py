import logging
from datetime import datetime

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from db import Database
from dictionary import dictionary
from services import GeminiService

logger = logging.getLogger(__name__)


class NotificationScheduler:
    def __init__(self, bot: Bot, db: Database, gemini: GeminiService):
        self.bot = bot
        self.db = db
        self.gemini = gemini
        self.scheduler = AsyncIOScheduler()

    async def start(self) -> None:
        """Запускає планувальник."""
        # Перевірка кожну хвилину
        self.scheduler.add_job(
            self._check_notifications,
            CronTrigger(minute="*"),
            id="check_notifications",
            replace_existing=True
        )

        # Підготовка контенту о 00:01
        self.scheduler.add_job(
            self._prepare_daily_content,
            CronTrigger(hour=0, minute=1),
            id="prepare_content",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Планувальник запущено")

        # Підготовка контенту при старті
        await self._prepare_daily_content()

    def stop(self) -> None:
        """Зупиняє планувальник."""
        self.scheduler.shutdown()
        logger.info("Планувальник зупинено")

    async def _check_notifications(self) -> None:
        """Перевіряє чи потрібно надіслати розсилку."""
        now = datetime.now(pytz.UTC)

        # Перебираємо всі можливі хвилини (HH:MM)
        for tz_name in pytz.common_timezones:
            try:
                tz = pytz.timezone(tz_name)
                local_time = now.astimezone(tz)
                current_time = local_time.strftime("%H:%M")

                # Отримуємо користувачів з цим часом розсилки
                users = await self.db.get_active_users_for_time(current_time)

                for user in users:
                    if user["timezone"] == tz_name:
                        await self._send_word_notification(user)

            except Exception as e:
                logger.debug(f"Помилка часової зони {tz_name}: {e}")

    async def _send_word_notification(self, user: dict) -> None:
        """Надсилає слово дня користувачу."""
        user_id = user["user_id"]
        word_data = dictionary.get_word_of_the_day()
        word = word_data["word"]

        # Перевіряємо чи вже переглядав сьогодні
        session = await self.db.get_today_session(user_id, word)
        if session and session["word_viewed"]:
            return

        try:
            content = await self.gemini.get_word_content(word_data)

            if content:
                text = self._format_notification(content, word_data)
            else:
                text = self._format_basic_notification(word_data)

            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="Markdown"
            )

            # Позначаємо як переглянуте
            await self.db.mark_word_viewed(user_id, word)

            # Нараховуємо бонуси за серії
            await self._check_streak_bonus(user_id)

            logger.info(f"Надіслано слово дня користувачу {user_id}")

        except Exception as e:
            logger.error(f"Помилка надсилання користувачу {user_id}: {e}")

    async def _check_streak_bonus(self, user_id: int) -> None:
        """Перевіряє і нараховує бонуси за серії."""
        stats = await self.db.get_user_stats(user_id)
        streak = stats["streak"]

        bonus_message = None

        if streak > 0 and streak % 30 == 0:
            bonus_message = f"Вітаю! {streak} днів поспіль! +10 бонусних балів!"
        elif streak > 0 and streak % 7 == 0:
            bonus_message = f"Чудово! {streak} днів поспіль! +3 бонусних бали!"

        if bonus_message:
            try:
                await self.bot.send_message(chat_id=user_id, text=bonus_message)
            except Exception as e:
                logger.error(f"Помилка надсилання бонусу {user_id}: {e}")

    def _format_notification(self, content: dict, word_data: dict) -> str:
        """Форматує повідомлення розсилки."""
        word = content.get("word", word_data["word"])
        transcription = content.get("transcription", word_data["transcription"])
        translations = content.get("translations", word_data["translations"])

        text = f"Слово дня!\n\n"
        text += f"*{word.upper()}* [{transcription}]\n\n"
        text += f"Переклад: {', '.join(translations)}\n\n"
        text += "Натисни «Слово дня» в меню, щоб побачити повний розбір та пройти тест."

        return text

    def _format_basic_notification(self, word_data: dict) -> str:
        """Форматує базове повідомлення розсилки."""
        text = f"Слово дня!\n\n"
        text += f"*{word_data['word'].upper()}* [{word_data['transcription']}]\n\n"
        text += f"Переклад: {', '.join(word_data['translations'])}\n\n"
        text += "Натисни «Слово дня» в меню, щоб побачити повний розбір."

        return text

    async def _prepare_daily_content(self) -> None:
        """Підготовлює контент для слова дня (кешування)."""
        word_data = dictionary.get_word_of_the_day()
        logger.info(f"Підготовка контенту для слова дня: {word_data['word']}")

        success = await self.gemini.prepare_word_of_day(word_data)
        if success:
            logger.info("Контент успішно підготовлено")
        else:
            logger.warning("Не вдалося підготувати весь контент")
