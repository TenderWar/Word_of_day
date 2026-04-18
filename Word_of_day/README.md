# Word of Day Bot

Telegram-бот для щоденного вивчення англійських слів з AI-генерацією контенту.

## Можливості

- Щоденне нове слово з повним розбором (переклад, транскрипція, приклади, синоніми)
- Тести для закріплення (EN→UK, UK→EN)
- Озвучення слів (Text-to-Speech)
- Статистика прогресу
- Автоматична розсилка о встановлений час
- Кешування контенту для економії API-запитів

## Технології

| Компонент | Технологія |
|-----------|------------|
| Мова | Python 3.11+ |
| Telegram | python-telegram-bot 22+ |
| AI | Google Gemini 2.5 Flash |
| TTS | gTTS (Google Text-to-Speech) |
| База даних | SQLite + aiosqlite |
| Планувальник | APScheduler |

## Встановлення

### 1. Клонування репозиторію

```bash
git clone https://github.com/SKP-Freelance/Word_of_day.git
cd Word_of_day
```

### 2. Створення віртуального середовища (опціонально)

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Встановлення залежностей

```bash
pip install -r requirements.txt
```

### 4. Налаштування

Скопіюйте `.env.example` в `.env` і заповніть:

```env
TELEGRAM_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
DATABASE_PATH=./data/bot.db
DICTIONARY_PATH=./dictionary.json
TTS_CACHE_DIR=./tts_cache
DEFAULT_NOTIFY_TIME=09:00
DEFAULT_TIMEZONE=Europe/Kyiv
```

**Отримання токенів:**
- Telegram: створіть бота через [@BotFather](https://t.me/BotFather)
- Gemini: отримайте ключ на [Google AI Studio](https://aistudio.google.com/apikey)

### 5. Запуск

**Windows:**
```bash
start_bot.bat
```

**Linux/Mac:**
```bash
python main.py
```

## Структура проекту

```
Word_of_day/
├── main.py              # Точка входу
├── config.py            # Конфігурація з .env
├── scheduler.py         # Щоденна розсилка
├── dictionary.py        # Робота зі словником
├── dictionary.json      # Словник (30 слів)
├── handlers/
│   ├── start.py         # /start, /help
│   ├── word.py          # Показ слова, TTS
│   ├── quiz.py          # Тести
│   ├── stats.py         # Статистика
│   └── settings.py      # Налаштування
├── services/
│   ├── gemini.py        # Gemini API
│   ├── tts.py           # Text-to-Speech
│   └── cache.py         # Кешування
└── db/
    ├── schema.sql       # Схема БД
    └── repository.py    # Запити до БД
```

## Команди бота

| Команда | Опис |
|---------|------|
| `/start` | Початок роботи |
| `/word` | Нове слово |
| `/stats` | Статистика |
| `/help` | Допомога |

## Меню

- **Слово дня** — отримати нове слово з розбором і тестом
- **Статистика** — переглянути прогрес навчання
- **Налаштування** — змінити час розсилки

## База даних

SQLite з таблицями:
- `users` — користувачі та їх налаштування
- `word_sessions` — історія переглядів слів
- `quiz_answers` — відповіді на тести
- `gemini_cache` — кеш згенерованого контенту

## Словник

Файл `dictionary.json` містить слова у форматі:

```json
{
  "word": "resilience",
  "transcription": "/rɪˈzɪliəns/",
  "translations": ["стійкість", "пружність"],
  "part_of_speech": "noun"
}
```

Для додавання нових слів просто розширте цей файл.

## Ліцензія

MIT
