from typing import Optional

from db import Database


class CacheService:
    """In-memory кеш з fallback на SQLite."""

    def __init__(self, db: Database):
        self.db = db
        self._memory_cache: dict[str, dict] = {}

    async def get_word_content(self, word: str) -> Optional[dict]:
        """Отримує повний розбір слова з кешу."""
        # Спочатку перевіряємо in-memory
        if word in self._memory_cache and self._memory_cache[word].get("content"):
            return self._memory_cache[word]["content"]

        # Потім SQLite
        cached = await self.db.get_cached_content(word)
        if cached and cached.get("content"):
            # Зберігаємо в in-memory
            if word not in self._memory_cache:
                self._memory_cache[word] = {}
            self._memory_cache[word]["content"] = cached["content"]
            return cached["content"]

        return None

    async def save_word_content(self, word: str, content: dict) -> None:
        """Зберігає повний розбір слова в кеш."""
        if word not in self._memory_cache:
            self._memory_cache[word] = {}
        self._memory_cache[word]["content"] = content
        await self.db.save_cached_content(word, content=content)

    async def get_quiz(self, word: str, quiz_type: str) -> Optional[dict]:
        """Отримує тест з кешу."""
        cache_key = f"quiz_{quiz_type}"

        # In-memory
        if word in self._memory_cache and self._memory_cache[word].get(cache_key):
            return self._memory_cache[word][cache_key]

        # SQLite
        cached = await self.db.get_cached_content(word)
        if cached:
            quiz = cached.get(f"quiz_{quiz_type}")
            if quiz:
                if word not in self._memory_cache:
                    self._memory_cache[word] = {}
                self._memory_cache[word][cache_key] = quiz
                return quiz

        return None

    async def save_quiz(self, word: str, quiz_type: str, quiz: dict) -> None:
        """Зберігає тест в кеш."""
        cache_key = f"quiz_{quiz_type}"

        if word not in self._memory_cache:
            self._memory_cache[word] = {}
        self._memory_cache[word][cache_key] = quiz

        if quiz_type == "en_to_uk":
            await self.db.save_cached_content(word, quiz_en_to_uk=quiz)
        else:
            await self.db.save_cached_content(word, quiz_uk_to_en=quiz)

    def preload_to_memory(self, word: str, data: dict) -> None:
        """Завантажує дані в in-memory кеш без запису в БД."""
        self._memory_cache[word] = data
