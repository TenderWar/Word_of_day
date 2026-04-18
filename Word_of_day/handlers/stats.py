from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from db import Database


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує статистику користувача."""
    db: Database = context.bot_data["db"]
    user_id = update.effective_user.id

    stats = await db.get_user_stats(user_id)

    text = (
        "Твоя статистика\n\n"
        f"Днів навчання: {stats['days_learning']}\n"
        f"Слів вивчено: {stats['words_learned']}\n"
        f"Правильних відповідей: {stats['correct_answers']} / {stats['total_answers']}\n"
        f"Точність: {stats['accuracy']}%\n"
        f"Всього балів: {stats['total_points']}\n\n"
        f"Серія: {stats['streak']} днів поспіль"
    )

    await update.message.reply_text(text)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /stats."""
    await show_stats(update, context)


async def handle_stats_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник кнопки 'Статистика'."""
    await show_stats(update, context)


def setup_stats_handlers(app) -> None:
    """Реєструє хендлери модуля."""
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(MessageHandler(filters.Regex("^Статистика$"), handle_stats_button))
