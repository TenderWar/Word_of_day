import logging
from pathlib import Path
from typing import Optional
import asyncio

from gtts import gTTS

import config

logger = logging.getLogger(__name__)


class TTSService:
    def __init__(self):
        self.cache_dir = config.TTS_CACHE_DIR

    def _get_cache_path(self, word: str) -> Path:
        """Повертає шлях до кешованого MP3-файлу."""
        return self.cache_dir / f"{word.lower()}.mp3"

    async def get_audio(self, word: str) -> Optional[Path]:
        """Повертає шлях до MP3-файлу зі словом. Генерує якщо немає в кеші."""
        cache_path = self._get_cache_path(word)

        # Перевіряємо кеш
        if cache_path.exists():
            return cache_path

        # Генеруємо в окремому потоці (gTTS синхронний)
        try:
            await asyncio.to_thread(self._generate_audio, word, cache_path)
            return cache_path
        except Exception as e:
            logger.error(f"Помилка TTS для слова '{word}': {e}")
            return None

    def _generate_audio(self, word: str, output_path: Path) -> None:
        """Синхронна генерація MP3 через gTTS."""
        tts = gTTS(text=word, lang="en", slow=False)
        tts.save(str(output_path))
        logger.info(f"Згенеровано аудіо для '{word}': {output_path}")

    async def is_available(self) -> bool:
        """Перевіряє доступність TTS сервісу."""
        try:
            # Тестова генерація в пам'яті
            await asyncio.to_thread(self._test_tts)
            return True
        except Exception as e:
            logger.warning(f"TTS недоступний: {e}")
            return False

    def _test_tts(self) -> None:
        """Тестовий запит до gTTS."""
        import io
        tts = gTTS(text="test", lang="en")
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
