from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler

from db import Database
from dictionary import dictionary
from services import GeminiService
from .word import format_word_card, format_basic_card


def format_quiz_keyboard(quiz: dict) -> InlineKeyboardMarkup:
    """Форматує клавіатуру тесту."""
    options = quiz.get("options", [])
    buttons = []
    labels = ["A", "B", "C", "D"]

    for i, option in enumerate(options[:4]):
        label = labels[i] if i < len(labels) else str(i + 1)
        buttons.append([InlineKeyboardButton(
            f"{label}: {option}",
            callback_data=f"answer:{i}"
        )])

    return InlineKeyboardMarkup(buttons)


async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Починає тест для слова."""
    query = update.callback_query
    await query.answer()

    db: Database = context.bot_data["db"]
    gemini: GeminiService = context.bot_data["gemini"]
    user_id = update.effective_user.id

    # Отримуємо слово з callback_data
    word = query.data.split(":")[1]
    word_data = dictionary.get_word_by_text(word)

    if not word_data:
        await query.message.reply_text("Слово не знайдено.")
        return

    # Перевіряємо чи вже проходив тест EN->UK
    already_answered = await db.has_answered_quiz_type(user_id, word, "en_to_uk")

    if already_answered:
        # Перевіряємо UK->EN
        already_uk = await db.has_answered_quiz_type(user_id, word, "uk_to_en")
        if already_uk:
            await query.message.reply_text("Ти вже пройшов тести для цього слова сьогодні!")
            return
        else:
            # Продовжуємо з UK->EN
            await show_quiz_uk_to_en(update, context, word_data)
            return

    # Показуємо тест EN->UK
    await show_quiz_en_to_uk(update, context, word_data)


async def show_quiz_en_to_uk(update: Update, context: ContextTypes.DEFAULT_TYPE, word_data: dict) -> None:
    """Показує тест EN->UK."""
    gemini: GeminiService = context.bot_data["gemini"]

    quiz = await gemini.get_quiz_en_to_uk(word_data)

    if not quiz:
        message = update.callback_query.message if update.callback_query else update.message
        await message.reply_text("На жаль, не вдалося створити тест. Спробуй пізніше.")
        return

    # Зберігаємо дані тесту в контексті користувача
    context.user_data["current_quiz"] = {
        "word": word_data["word"],
        "type": "en_to_uk",
        "correct": quiz["correct"],
        "options": quiz["options"]
    }

    text = f"Тест 1/2: EN -> UK\n\n{quiz['question']}"
    keyboard = format_quiz_keyboard(quiz)

    message = update.callback_query.message if update.callback_query else update.message
    await message.reply_text(text, reply_markup=keyboard)


async def show_quiz_uk_to_en(update: Update, context: ContextTypes.DEFAULT_TYPE, word_data: dict) -> None:
    """Показує тест UK->EN."""
    gemini: GeminiService = context.bot_data["gemini"]

    quiz = await gemini.get_quiz_uk_to_en(word_data)

    if not quiz:
        message = update.callback_query.message if update.callback_query else update.message
        await message.reply_text("На жаль, не вдалося створити тест. Спробуй пізніше.")
        return

    # Зберігаємо дані тесту в контексті користувача
    context.user_data["current_quiz"] = {
        "word": word_data["word"],
        "type": "uk_to_en",
        "correct": quiz["correct"],
        "options": quiz["options"]
    }

    text = f"Тест 2/2: UK -> EN\n\n{quiz['question']}"
    keyboard = format_quiz_keyboard(quiz)

    message = update.callback_query.message if update.callback_query else update.message
    await message.reply_text(text, reply_markup=keyboard)


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє відповідь на тест."""
    query = update.callback_query
    await query.answer()

    db: Database = context.bot_data["db"]
    gemini: GeminiService = context.bot_data["gemini"]
    user_id = update.effective_user.id

    # Отримуємо поточний тест
    current_quiz = context.user_data.get("current_quiz")
    if not current_quiz:
        await query.message.reply_text("Тест не знайдено. Почни знову.")
        return

    # Отримуємо індекс відповіді
    answer_idx = int(query.data.split(":")[1])
    options = current_quiz["options"]
    selected = options[answer_idx] if answer_idx < len(options) else None

    word = current_quiz["word"]
    quiz_type = current_quiz["type"]
    correct = current_quiz["correct"]

    # Перевіряємо відповідь
    is_correct = selected == correct

    # Зберігаємо відповідь
    await db.save_quiz_answer(user_id, word, quiz_type, is_correct)

    if is_correct:
        await query.message.reply_text("Вірно! +1 бал")
    else:
        # Показуємо правильну відповідь і картку слова
        await query.message.reply_text(f"Неправильно. Правильна відповідь: {correct}")

        # Показуємо картку слова
        word_data = dictionary.get_word_by_text(word)
        if word_data:
            content = await gemini.get_word_content(word_data)
            if content:
                text = format_word_card(content, word_data)
            else:
                text = format_basic_card(word_data)

            await query.message.reply_text(text, parse_mode="Markdown")

    # Очищаємо поточний тест
    context.user_data["current_quiz"] = None

    # Переходимо до наступного тесту або завершуємо
    if quiz_type == "en_to_uk":
        # Перевіряємо чи ще не відповідав на UK->EN
        already_uk = await db.has_answered_quiz_type(user_id, word, "uk_to_en")
        if not already_uk:
            word_data = dictionary.get_word_by_text(word)
            if word_data:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("Далі", callback_data=f"next_quiz:{word}")
                ]])
                await query.message.reply_text("Готовий до наступного тесту?", reply_markup=keyboard)
                return

    # Завершення тестування
    await show_quiz_results(update, context, word)


async def handle_next_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Переходить до наступного тесту."""
    query = update.callback_query
    await query.answer()

    word = query.data.split(":")[1]
    word_data = dictionary.get_word_by_text(word)

    if word_data:
        await show_quiz_uk_to_en(update, context, word_data)


async def show_quiz_results(update: Update, context: ContextTypes.DEFAULT_TYPE, word: str) -> None:
    """Показує результати тестування."""
    db: Database = context.bot_data["db"]
    user_id = update.effective_user.id

    # Отримуємо відповіді за сьогодні
    answers = await db.get_today_quiz_answers(user_id, word)

    correct_count = sum(1 for a in answers if a["is_correct"])
    total = len(answers)

    # Позначаємо тест завершеним
    await db.mark_quiz_completed(user_id, word)

    # Отримуємо загальну статистику
    stats = await db.get_user_stats(user_id)

    text = (
        f"Результат сьогодні:\n"
        f"Правильних: {correct_count}/{total}\n"
        f"Балів зароблено: {correct_count}\n\n"
        f"Загальна точність: {stats['accuracy']}%"
    )

    message = update.callback_query.message if update.callback_query else update.message
    await message.reply_text(text)


def setup_quiz_handlers(app) -> None:
    """Реєструє хендлери модуля."""
    app.add_handler(CallbackQueryHandler(start_quiz, pattern=r"^quiz_start:"))
    app.add_handler(CallbackQueryHandler(handle_answer, pattern=r"^answer:"))
    app.add_handler(CallbackQueryHandler(handle_next_quiz, pattern=r"^next_quiz:"))
