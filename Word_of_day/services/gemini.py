import json
import re
import logging
from typing import Optional

from google import genai

import config
from .cache import CacheService

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self, cache: CacheService):
        self.cache = cache
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model = "gemini-2.5-flash-lite"

    def _extract_json(self, text: str) -> dict:
        """Витягує JSON з тексту відповіді."""
        # Видаляємо markdown code blocks
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        text = text.strip()

        return json.loads(text)

    async def get_word_content(self, word_data: dict) -> Optional[dict]:
        """Отримує повний розбір слова. Спочатку перевіряє кеш."""
        word = word_data["word"]

        # Перевіряємо кеш
        cached = await self.cache.get_word_content(word)
        if cached:
            return cached

        # Генеруємо через Gemini
        prompt = f"""Ти - викладач англійської мови. Надай детальний розбір слова "{word}" ({word_data['part_of_speech']}, {word_data['transcription']}).
Поверни ТІЛЬКИ валідний JSON без жодного пояснення:
{{
  "word": "...",
  "transcription": "...",
  "part_of_speech": "...",
  "translations": ["...", "..."],
  "meanings": [
    {{
      "definition_uk": "...",
      "examples": [
        {{"en": "...", "uk": "..."}},
        {{"en": "...", "uk": "..."}}
      ]
    }}
  ],
  "synonyms": ["...", "..."],
  "antonyms": ["...", "..."],
  "usage_note": "коротка порада щодо вживання (1-2 речення, українською)"
}}"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            content = self._extract_json(response.text)

            # Зберігаємо в кеш
            await self.cache.save_word_content(word, content)

            return content
        except Exception as e:
            logger.error(f"Помилка Gemini API при генерації контенту для '{word}': {e}")
            return None

    async def get_quiz_en_to_uk(self, word_data: dict) -> Optional[dict]:
        """Генерує тест EN->UK. Використовує переклади з кешованого контенту."""
        word = word_data["word"]

        # Перевіряємо кеш тесту
        cached = await self.cache.get_quiz(word, "en_to_uk")
        if cached:
            return cached

        # Отримуємо контент слова для актуальних перекладів
        content = await self.get_word_content(word_data)
        if content and content.get("translations"):
            translations = content["translations"]
        else:
            translations = word_data["translations"]

        correct_answer = translations[0]

        prompt = f"""Склади тест для англійського слова "{word}".
Правильний переклад: "{correct_answer}"

Поверни ТІЛЬКИ валідний JSON:
{{
  "question": "Як перекласти слово «{word}»?",
  "correct": "{correct_answer}",
  "options": ["{correct_answer}", "хибний1", "хибний2", "хибний3"]
}}

КРИТИЧНО ВАЖЛИВО:
- Поле "correct" = "{correct_answer}" (ТОЧНО так, без змін)
- 3 хибних варіанти мають бути АБСОЛЮТНО РІЗНИМИ словами, НЕ синонімами!
- Хибні варіанти - випадкові українські слова з ІНШОЇ тематики (наприклад: "яблуко", "стіл", "бігти")
- НЕ використовуй слова схожі за значенням до "{correct_answer}"
- Перемішай 4 варіанти у випадковому порядку"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            quiz = self._extract_json(response.text)

            # Перевіряємо що correct є в options
            if quiz["correct"] not in quiz["options"]:
                quiz["options"][0] = quiz["correct"]

            # Зберігаємо в кеш
            await self.cache.save_quiz(word, "en_to_uk", quiz)

            return quiz
        except Exception as e:
            logger.error(f"Помилка Gemini API при генерації тесту EN->UK для '{word}': {e}")
            return None

    async def get_quiz_uk_to_en(self, word_data: dict) -> Optional[dict]:
        """Генерує тест UK->EN."""
        word = word_data["word"]

        # Перевіряємо кеш
        cached = await self.cache.get_quiz(word, "uk_to_en")
        if cached:
            return cached

        # Отримуємо контент слова для актуальних перекладів
        content = await self.get_word_content(word_data)
        if content and content.get("translations"):
            translation = content["translations"][0]
        else:
            translation = word_data["translations"][0]

        prompt = f"""Склади тест: дано українське слово "{translation}", потрібно знайти англійський відповідник.
Правильна відповідь: "{word}"

Поверни ТІЛЬКИ валідний JSON:
{{
  "question": "Як перекласти «{translation}» англійською?",
  "correct": "{word}",
  "options": ["{word}", "wrong1", "wrong2", "wrong3"]
}}

КРИТИЧНО ВАЖЛИВО:
- Поле "correct" = "{word}" (ТОЧНО так, без змін)
- 3 хибних варіанти - АБСОЛЮТНО РІЗНІ англійські слова, НЕ синоніми!
- Хибні варіанти - випадкові англійські слова з ІНШОЇ тематики (наприклад: "apple", "table", "run")
- НЕ використовуй слова схожі за значенням до "{word}"
- Перемішай 4 варіанти у випадковому порядку"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            quiz = self._extract_json(response.text)

            # Перевіряємо що correct є в options
            if quiz["correct"] not in quiz["options"]:
                quiz["options"][0] = quiz["correct"]

            # Зберігаємо в кеш
            await self.cache.save_quiz(word, "uk_to_en", quiz)

            return quiz
        except Exception as e:
            logger.error(f"Помилка Gemini API при генерації тесту UK->EN для '{word}': {e}")
            return None

    async def prepare_word_of_day(self, word_data: dict) -> bool:
        """Підготовлює весь контент для слова дня (кешує заздалегідь)."""
        word = word_data["word"]
        logger.info(f"Підготовка контенту для слова '{word}'...")

        content = await self.get_word_content(word_data)
        if not content:
            logger.warning(f"Не вдалося підготувати контент для '{word}'")
            return False

        quiz_en = await self.get_quiz_en_to_uk(word_data)
        quiz_uk = await self.get_quiz_uk_to_en(word_data)

        if quiz_en and quiz_uk:
            logger.info(f"Контент для '{word}' успішно підготовлено")
            return True

        logger.warning(f"Не вдалося підготувати тести для '{word}'")
        return False
