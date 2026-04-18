import aiosqlite
from datetime import datetime, date
from pathlib import Path
from typing import Optional
import json

import config


class Database:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DATABASE_PATH
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row

        # Виконання схеми
        schema_path = Path(__file__).parent / "schema.sql"
        schema = schema_path.read_text(encoding="utf-8")
        await self._connection.executescript(schema)
        await self._connection.commit()

    async def close(self):
        if self._connection:
            await self._connection.close()

    # === Користувачі ===

    async def get_user(self, user_id: int) -> Optional[dict]:
        async with self._connection.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_user(self, user_id: int, username: str) -> None:
        await self._connection.execute(
            """
            INSERT OR IGNORE INTO users (user_id, username, joined_at, timezone, notify_time, is_active, current_word_index)
            VALUES (?, ?, ?, ?, ?, 1, 0)
            """,
            (user_id, username, datetime.now().isoformat(), config.DEFAULT_TIMEZONE, config.DEFAULT_NOTIFY_TIME)
        )
        await self._connection.commit()

    async def get_next_word_index(self, user_id: int, total_words: int) -> int:
        """Повертає індекс наступного слова і збільшує лічильник."""
        user = await self.get_user(user_id)
        if not user:
            return 0

        current_index = user.get("current_word_index", 0)
        next_index = (current_index + 1) % total_words

        await self._connection.execute(
            "UPDATE users SET current_word_index = ? WHERE user_id = ?",
            (next_index, user_id)
        )
        await self._connection.commit()

        return current_index

    async def update_user_settings(self, user_id: int, **kwargs) -> None:
        allowed_fields = {"timezone", "notify_time", "is_active"}
        fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not fields:
            return

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [user_id]

        await self._connection.execute(
            f"UPDATE users SET {set_clause} WHERE user_id = ?",
            values
        )
        await self._connection.commit()

    async def get_active_users_for_time(self, notify_time: str) -> list[dict]:
        async with self._connection.execute(
            "SELECT * FROM users WHERE is_active = 1 AND notify_time = ?",
            (notify_time,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # === Сесії слів ===

    async def get_today_session(self, user_id: int, word: str) -> Optional[dict]:
        today = date.today().isoformat()
        async with self._connection.execute(
            "SELECT * FROM word_sessions WHERE user_id = ? AND date = ?",
            (user_id, today)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_or_update_session(self, user_id: int, word: str, word_viewed: bool = False, quiz_completed: bool = False) -> None:
        today = date.today().isoformat()
        existing = await self.get_today_session(user_id, word)

        if existing:
            updates = []
            values = []
            if word_viewed and not existing["word_viewed"]:
                updates.append("word_viewed = 1")
            if quiz_completed and not existing["quiz_completed"]:
                updates.append("quiz_completed = 1")

            if updates:
                await self._connection.execute(
                    f"UPDATE word_sessions SET {', '.join(updates)} WHERE id = ?",
                    (existing["id"],)
                )
                await self._connection.commit()
        else:
            await self._connection.execute(
                """
                INSERT INTO word_sessions (user_id, word, date, word_viewed, quiz_completed)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, word, today, int(word_viewed), int(quiz_completed))
            )
            await self._connection.commit()

    async def mark_word_viewed(self, user_id: int, word: str) -> bool:
        """Позначає слово як переглянуте. Повертає True, якщо це перший перегляд."""
        session = await self.get_today_session(user_id, word)
        first_view = session is None or not session["word_viewed"]
        await self.create_or_update_session(user_id, word, word_viewed=True)
        return first_view

    async def mark_quiz_completed(self, user_id: int, word: str) -> None:
        await self.create_or_update_session(user_id, word, quiz_completed=True)

    # === Відповіді на тести ===

    async def save_quiz_answer(self, user_id: int, word: str, quiz_type: str, is_correct: bool) -> None:
        await self._connection.execute(
            """
            INSERT INTO quiz_answers (user_id, word, quiz_type, is_correct, answered_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, word, quiz_type, int(is_correct), datetime.now().isoformat())
        )
        await self._connection.commit()

    async def get_today_quiz_answers(self, user_id: int, word: str) -> list[dict]:
        today = date.today().isoformat()
        async with self._connection.execute(
            """
            SELECT * FROM quiz_answers
            WHERE user_id = ? AND word = ? AND date(answered_at) = ?
            """,
            (user_id, word, today)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def has_answered_quiz_type(self, user_id: int, word: str, quiz_type: str) -> bool:
        today = date.today().isoformat()
        async with self._connection.execute(
            """
            SELECT COUNT(*) as cnt FROM quiz_answers
            WHERE user_id = ? AND word = ? AND quiz_type = ? AND date(answered_at) = ?
            """,
            (user_id, word, quiz_type, today)
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] > 0

    # === Статистика ===

    async def get_user_stats(self, user_id: int) -> dict:
        # Кількість днів навчання
        async with self._connection.execute(
            "SELECT COUNT(DISTINCT date) as days FROM word_sessions WHERE user_id = ? AND word_viewed = 1",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            days_learning = row["days"]

        # Кількість вивчених слів (завершених тестів)
        async with self._connection.execute(
            "SELECT COUNT(DISTINCT word) as words FROM word_sessions WHERE user_id = ? AND quiz_completed = 1",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            words_learned = row["words"]

        # Статистика відповідей
        async with self._connection.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(is_correct) as correct
            FROM quiz_answers WHERE user_id = ?
            """,
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            total_answers = row["total"] or 0
            correct_answers = row["correct"] or 0

        # Серія днів поспіль
        streak = await self._calculate_streak(user_id)

        # Загальна кількість балів
        total_points = correct_answers
        # Бонуси за серії
        if streak >= 30:
            total_points += (streak // 30) * 10
        if streak >= 7:
            total_points += (streak // 7) * 3

        accuracy = (correct_answers / total_answers * 100) if total_answers > 0 else 0

        return {
            "days_learning": days_learning,
            "words_learned": words_learned,
            "total_answers": total_answers,
            "correct_answers": correct_answers,
            "accuracy": round(accuracy, 1),
            "streak": streak,
            "total_points": total_points
        }

    async def _calculate_streak(self, user_id: int) -> int:
        async with self._connection.execute(
            """
            SELECT DISTINCT date FROM word_sessions
            WHERE user_id = ? AND word_viewed = 1
            ORDER BY date DESC
            """,
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return 0

        dates = [date.fromisoformat(row["date"]) for row in rows]
        today = date.today()

        # Перевіряємо чи є сьогоднішній день або вчорашній
        if dates[0] != today and dates[0] != today.replace(day=today.day - 1):
            return 0

        streak = 1
        for i in range(1, len(dates)):
            diff = (dates[i - 1] - dates[i]).days
            if diff == 1:
                streak += 1
            else:
                break

        return streak

    # === Кеш Gemini ===

    async def get_cached_content(self, word: str) -> Optional[dict]:
        async with self._connection.execute(
            "SELECT * FROM gemini_cache WHERE word = ?", (word,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "word": row["word"],
                    "content": json.loads(row["content_json"]) if row["content_json"] else None,
                    "quiz_en_to_uk": json.loads(row["quiz_en_to_uk_json"]) if row["quiz_en_to_uk_json"] else None,
                    "quiz_uk_to_en": json.loads(row["quiz_uk_to_en_json"]) if row["quiz_uk_to_en_json"] else None,
                }
            return None

    async def save_cached_content(self, word: str, content: dict = None, quiz_en_to_uk: dict = None, quiz_uk_to_en: dict = None) -> None:
        existing = await self.get_cached_content(word)

        if existing:
            updates = []
            values = []
            if content is not None:
                updates.append("content_json = ?")
                values.append(json.dumps(content, ensure_ascii=False))
            if quiz_en_to_uk is not None:
                updates.append("quiz_en_to_uk_json = ?")
                values.append(json.dumps(quiz_en_to_uk, ensure_ascii=False))
            if quiz_uk_to_en is not None:
                updates.append("quiz_uk_to_en_json = ?")
                values.append(json.dumps(quiz_uk_to_en, ensure_ascii=False))

            if updates:
                values.append(word)
                await self._connection.execute(
                    f"UPDATE gemini_cache SET {', '.join(updates)} WHERE word = ?",
                    values
                )
        else:
            await self._connection.execute(
                """
                INSERT INTO gemini_cache (word, content_json, quiz_en_to_uk_json, quiz_uk_to_en_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    word,
                    json.dumps(content, ensure_ascii=False) if content else None,
                    json.dumps(quiz_en_to_uk, ensure_ascii=False) if quiz_en_to_uk else None,
                    json.dumps(quiz_uk_to_en, ensure_ascii=False) if quiz_uk_to_en else None,
                    datetime.now().isoformat()
                )
            )

        await self._connection.commit()
