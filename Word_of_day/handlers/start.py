from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from db import Database


# Головне меню
MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["Слово дня", "Статистика"],
        ["Налаштування"]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /start."""
    db: Database = context.bot_data["db"]
    user = update.effective_user

    # Реєструємо користувача
    await db.create_user(user.id, user.username or user.first_name)

    text = (
        "Привіт, студент!\n\n"
        "Це бот «Слово дня» для вивчення англійської мови.\n\n"
        "Щодня ти отримуєш одне нове слово з повним розбором:\n"
        "- Переклад та транскрипція\n"
        "- Приклади вживання\n"
        "- Синоніми та антоніми\n"
        "- Тести для закріплення\n\n"
        "Скористайся меню нижче, щоб почати!"
    )

    await update.message.reply_text(text, reply_markup=MAIN_MENU)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /help."""
    text = (
        "Слово дня — бот для вивчення англійської мови\n\n"
        "Команди:\n"
        "/start — Почати роботу з ботом\n"
        "/word — Отримати слово дня\n"
        "/stats — Твоя статистика\n"
        "/help — Допомога\n\n"
        "Щодня о встановлений час ти отримуєш нове слово. "
        "Після перегляду слова можеш пройти тест для закріплення."
    )

    await update.message.reply_text(text)


def setup_start_handlers(app) -> None:
    """Реєструє хендлери модуля."""
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
