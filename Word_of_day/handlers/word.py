from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from db import Database
from dictionary import dictionary
from services import GeminiService, TTSService


def format_word_card(content: dict, word_data: dict) -> str:
    """Форматує картку слова для відображення."""
    word = content.get("word", word_data["word"])
    transcription = content.get("transcription", word_data["transcription"])
    part_of_speech = content.get("part_of_speech", word_data["part_of_speech"])
    translations = content.get("translations", word_data["translations"])

    # Заголовок
    text = f"*{word.upper()}* [{transcription}]\n"
    text += f"_{part_of_speech}_\n\n"

    # Переклади
    text += f"Переклад: {', '.join(translations)}\n\n"

    # Значення та приклади
    meanings = content.get("meanings", [])
    if meanings:
        text += "Значення:\n"
        for meaning in meanings:
            definition = meaning.get("definition_uk", "")
            if definition:
                text += f"  {definition}\n"
            for example in meaning.get("examples", []):
                text += f"    -> _{example.get('en', '')}_\n"
                text += f"    -> {example.get('uk', '')}\n"
        text += "\n"

    # Синоніми
    synonyms = content.get("synonyms", [])
    if synonyms:
        text += f"Синоніми: {', '.join(synonyms)}\n"

    # Антоніми
    antonyms = content.get("antonyms", [])
    if antonyms:
        text += f"Антоніми: {', '.join(antonyms)}\n"

    # Порада
    usage_note = content.get("usage_note", "")
    if usage_note:
        text += f"\nПорада: {usage_note}"

    return text


def format_basic_card(word_data: dict) -> str:
    """Форматує базову картку без Gemini-контенту."""
    text = f"*{word_data['word'].upper()}* [{word_data['transcription']}]\n"
    text += f"_{word_data['part_of_speech']}_\n\n"
    text += f"Переклад: {', '.join(word_data['translations'])}"
    return text


async def show_word_of_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує наступне слово для користувача."""
    db: Database = context.bot_data["db"]
    gemini: GeminiService = context.bot_data["gemini"]
    tts: TTSService = context.bot_data["tts"]
    user_id = update.effective_user.id

    # Отримуємо наступне слово для користувача
    word_index = await db.get_next_word_index(user_id, dictionary.total_words())
    word_data = dictionary.get_word_by_index(word_index)
    word = word_data["word"]

    # Позначаємо як переглянуте
    await db.mark_word_viewed(user_id, word)

    # Показуємо повідомлення про завантаження
    message = update.message or update.callback_query.message
    loading_msg = await message.reply_text("Готую матеріали...")

    # Отримуємо контент
    content = await gemini.get_word_content(word_data)

    if content:
        text = format_word_card(content, word_data)
    else:
        text = format_basic_card(word_data)

    # Кнопки
    keyboard = []
    # Перевіряємо доступність TTS
    tts_available = await tts.is_available()
    if tts_available:
        keyboard.append([
            InlineKeyboardButton("Слухати", callback_data=f"tts:{word}"),
            InlineKeyboardButton("Почати тест", callback_data=f"quiz_start:{word}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("Почати тест", callback_data=f"quiz_start:{word}")
        ])

    # Видаляємо повідомлення про завантаження і показуємо картку
    await loading_msg.delete()
    await message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
    )


async def handle_tts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник кнопки прослуховування."""
    query = update.callback_query
    await query.answer()

    tts: TTSService = context.bot_data["tts"]

    # Отримуємо слово з callback_data
    word = query.data.split(":")[1]

    # Генеруємо аудіо
    audio_path = await tts.get_audio(word)

    if audio_path:
        with open(audio_path, "rb") as audio:
            await query.message.reply_voice(audio)
    else:
        await query.message.reply_text("На жаль, не вдалося згенерувати аудіо.")


async def cmd_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /word."""
    await show_word_of_day(update, context)


async def handle_word_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник кнопки 'Слово дня'."""
    await show_word_of_day(update, context)


def setup_word_handlers(app) -> None:
    """Реєструє хендлери модуля."""
    app.add_handler(CommandHandler("word", cmd_word))
    app.add_handler(MessageHandler(filters.Regex("^Слово дня$"), handle_word_button))
    app.add_handler(CallbackQueryHandler(handle_tts, pattern=r"^tts:"))
