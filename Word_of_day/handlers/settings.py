import re
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, ConversationHandler, filters

from db import Database

# Стани розмови
WAITING_FOR_TIME = 1


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує налаштування користувача."""
    db: Database = context.bot_data["db"]
    user_id = update.effective_user.id

    user = await db.get_user(user_id)

    if not user:
        await update.message.reply_text("Спочатку виконай /start")
        return

    status = "увімкнена" if user["is_active"] else "вимкнена"

    text = (
        "Налаштування\n\n"
        f"Час розсилки: {user['notify_time']}\n"
        f"Часовий пояс: {user['timezone']}\n"
        f"Розсилка: {status}"
    )

    toggle_text = "Вимкнути розсилку" if user["is_active"] else "Увімкнути розсилку"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Змінити час", callback_data="settings:change_time")],
        [InlineKeyboardButton(toggle_text, callback_data="settings:toggle_notify")]
    ])

    await update.message.reply_text(text, reply_markup=keyboard)


async def handle_toggle_notify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Перемикає стан розсилки."""
    query = update.callback_query
    await query.answer()

    db: Database = context.bot_data["db"]
    user_id = update.effective_user.id

    user = await db.get_user(user_id)
    new_status = 0 if user["is_active"] else 1

    await db.update_user_settings(user_id, is_active=new_status)

    status_text = "увімкнено" if new_status else "вимкнено"
    await query.message.reply_text(f"Розсилку {status_text}.")


async def handle_change_time_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Початок зміни часу розсилки."""
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "Введи новий час розсилки у форматі ГГ:ХХ (наприклад, 09:00 або 18:30):"
    )

    return WAITING_FOR_TIME


async def handle_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє введення нового часу."""
    db: Database = context.bot_data["db"]
    user_id = update.effective_user.id

    text = update.message.text.strip()

    # Перевіряємо формат
    if not re.match(r"^\d{2}:\d{2}$", text):
        await update.message.reply_text(
            "Неправильний формат. Введи час у форматі ГГ:ХХ (наприклад, 09:00):"
        )
        return WAITING_FOR_TIME

    # Перевіряємо валідність часу
    try:
        hours, minutes = map(int, text.split(":"))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            "Неправильний час. Години: 00-23, хвилини: 00-59. Спробуй ще:"
        )
        return WAITING_FOR_TIME

    # Зберігаємо новий час
    await db.update_user_settings(user_id, notify_time=text)

    await update.message.reply_text(f"Час розсилки змінено на {text}.")

    return ConversationHandler.END


async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Скасовує зміну налаштувань."""
    await update.message.reply_text("Скасовано.")
    return ConversationHandler.END


def setup_settings_handlers(app) -> None:
    """Реєструє хендлери модуля."""
    # Показ налаштувань
    app.add_handler(MessageHandler(filters.Regex("^Налаштування$"), show_settings))

    # Перемикання розсилки
    app.add_handler(CallbackQueryHandler(handle_toggle_notify, pattern=r"^settings:toggle_notify$"))

    # Зміна часу (ConversationHandler)
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_change_time_start, pattern=r"^settings:change_time$")],
        states={
            WAITING_FOR_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time_input)
            ]
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, handle_cancel)
        ]
    )
    app.add_handler(conv_handler)
