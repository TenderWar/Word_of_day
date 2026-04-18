import json
from datetime import date
from typing import Optional

import config


class Dictionary:
    def __init__(self):
        self._words: list[dict] = []
        self._epoch = date(2024, 1, 1)  # Базова дата для розрахунку індексу

    def load(self) -> None:
        """Завантажує словник з JSON-файлу."""
        with open(config.DICTIONARY_PATH, "r", encoding="utf-8") as f:
            self._words = json.load(f)

        if not self._words:
            raise ValueError("Словник порожній")

    @property
    def words(self) -> list[dict]:
        return self._words

    def get_word_of_the_day(self, target_date: date = None) -> dict:
        """Повертає слово дня за детермінованим алгоритмом."""
        if not self._words:
            raise ValueError("Словник не завантажено")

        target_date = target_date or date.today()
        days_since_epoch = (target_date - self._epoch).days
        index = days_since_epoch % len(self._words)

        return self._words[index]

    def get_word_by_index(self, index: int) -> dict:
        """Повертає слово за індексом."""
        if not self._words:
            raise ValueError("Словник не завантажено")

        return self._words[index % len(self._words)]

    def total_words(self) -> int:
        """Повертає загальну кількість слів."""
        return len(self._words)

    def get_word_by_text(self, word_text: str) -> Optional[dict]:
        """Знаходить слово за текстом."""
        for word in self._words:
            if word["word"].lower() == word_text.lower():
                return word
        return None


# Глобальний екземпляр
dictionary = Dictionary()
