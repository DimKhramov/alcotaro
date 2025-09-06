# Алко Таро - Telegram бот

Телеграм-бот «Алко Таро» с интеграцией OpenAI (ChatGPT) для гаданий на картах Таро с рекомендациями алкогольных напитков.

## Описание проекта

Бот предлагает два типа гаданий:
1. **Тестовое гадание** - бесплатное гадание с одной картой Таро и рекомендацией напитка (ограниченное количество раз)
2. **Премиум гадание** - платное гадание с тремя картами Таро, подробной интерпретацией и рекомендациями напитков

## Структура проекта

```
/project_root
  ├── bot.py                     # точка входа: инициализация бота, роутеров и запуск
  ├── pyproject.toml             # настройки инструментов разработки
  ├── requirements.txt           # зависимости проекта
  ├── .env.example               # пример переменных окружения
  ├── config.py                  # pydantic-класс с конфигом (загружает .env)
  ├── constants/
  │     ├── texts.py             # все тексты/шаблоны (HTML), константы цен, кнопки
  │     └── prompts.py           # все промпты для GPT
  ├── handlers/
  │     ├── tarot.py             # хендлеры для /start, теста, start_reading, premium
  │     └── payments.py          # обработчики payment/confirm
  ├── services/
  │     ├── openai_service.py    # единая точка работы с OpenAI + retry + JSON parse
  │     └── payment_service.py   # обёртка для create_invoice / precheckout / success
  ├── keyboards/
  │     └── inline.py            # фабрики inline-клавиатур
  ├── utils/
  │     ├── storage.py           # абстракция хранилища (JSON atomic write + asyncio.Lock)
  │     └── animations.py        # реализация анимаций (edit_text) и helper для delays
  ├── models/
  │     └── schemas.py           # Pydantic-модели: Card, Reading, PremiumReading
  ├── tests/
  │     ├── test_openai_service.py
  │     ├── test_handlers.py
  │     └── test_storage.py
  └── .github/workflows/ci.yml    # тесты, линт и форматирование
```

## Требования

- Python 3.11 или выше
- Токен Telegram бота (получить у [@BotFather](https://t.me/BotFather))
- API ключ OpenAI (получить на [платформе OpenAI](https://platform.openai.com/))
- Токен провайдера платежей Telegram (для премиум-гаданий)

## Деплой на Replit

### Быстрый старт

1. **Импорт из GitHub:**
   - Перейдите на [Replit](https://replit.com)
   - Нажмите "Create Repl" → "Import from GitHub"
   - Вставьте URL вашего репозитория

2. **Настройка переменных окружения:**
   - В Replit откройте вкладку "Secrets" (замок в левой панели)
   - Добавьте все переменные из `.env.example`:
     - `BOT_TOKEN` - токен вашего Telegram бота
     - `OPENAI_API_KEY` - ключ OpenAI API
     - `YOOKASSA_SHOP_ID` - ID магазина ЮKassa (опционально)
     - `YOOKASSA_SECRET_KEY` - секретный ключ ЮKassa (опционально)
     - Остальные переменные можно оставить по умолчанию

3. **Запуск:**
   - Нажмите кнопку "Run"
   - Бот автоматически установит зависимости и запустится

### Бесплатное 24/7 хостинг на Replit

**⚠️ Важно:** В бесплатной версии Replit проекты засыпают через некоторое время бездействия. Вот как это обойти:

#### Метод 1: UptimeRobot (Рекомендуется)

1. **Получите URL вашего Repl:**
   - После запуска бота скопируйте URL из адресной строки браузера
   - Формат: `https://your-repl-name.your-username.repl.co`
   - Откройте этот URL в новой вкладке - должно появиться "Bot is alive!"

2. **Настройте UptimeRobot:**
   - Зарегистрируйтесь на [UptimeRobot](https://uptimerobot.com) (бесплатно)
   - Создайте новый монитор:
     - Monitor Type: HTTP(s)
     - Friendly Name: Ваше название
     - URL: URL вашего Repl
     - Monitoring Interval: 5 минут
   - Сохраните монитор

3. **Результат:**
   - UptimeRobot будет "пинговать" ваш бот каждые 5 минут
   - Это предотвратит засыпание Repl
   - Бот будет работать 24/7 бесплатно

#### Метод 2: Альтернативные сервисы мониторинга

Если UptimeRobot не работает, попробуйте:
- [Pulsetic](https://pulsetic.com) - бесплатный план доступен
- [StatusCake](https://www.statuscake.com) - бесплатный мониторинг
- [Pingdom](https://www.pingdom.com) - ограниченный бесплатный план

#### Ограничения бесплатного хостинга

- Бот может перезапускаться каждый час
- Возможны кратковременные отключения
- Общие IP-адреса могут вызывать rate limiting от Discord/Telegram
- Для стабильной работы рекомендуется платный план

#### Платные опции Replit

- **Replit Core ($25/месяц):** Включает $10 кредитов для деплоя
- **Reserved VM ($20+/месяц):** Выделенная виртуальная машина с 99.9% uptime
- **Autoscale Deployments:** Автомасштабирование по требованию

## Локальная установка и настройка

### 1. Клонирование репозитория

```bash
git clone https://github.com/yourusername/alcobot.git
cd alcobot
```

### 2. Создание виртуального окружения

```bash
python -m venv venv

# Активация в Windows
venv\Scripts\activate

# Активация в Linux/MacOS
source venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка переменных окружения

Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

Отредактируйте файл `.env`, указав свои значения:

```
# Базовые настройки
DEBUG=False

# Telegram Bot
BOT_TOKEN=your_telegram_bot_token_here
WEBHOOK_URL=https://example.com/webhook  # Только для продакшена с вебхуками
WEBHOOK_PATH=/webhook                    # Только для продакшена с вебхуками
WEBAPP_HOST=0.0.0.0                      # Только для продакшена с вебхуками
WEBAPP_PORT=8000                         # Только для продакшена с вебхуками

# Платежи через Telegram Stars
PAYMENT_PROVIDER_TOKEN=  # Не используется для Telegram Stars
PREMIUM_READING_PRICE=50.0  # Цена в Telegram Stars
CURRENCY=XTR  # Telegram Stars

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.7

# Ограничения
FREE_TEST_LIMIT=1
# Список ID пользователей с бесплатным доступом (через запятую)
FREE_USERS=123456789,987654321

# Анимации
ANIMATION_DELAY_SHORT=0.5
ANIMATION_DELAY_MEDIUM=1.0
ANIMATION_DELAY_LONG=2.0
```

## Запуск бота

### Локальный запуск (режим long polling)

```bash
python bot.py
```

### Запуск с вебхуками (для продакшена)

Для запуска с вебхуками необходимо настроить переменные окружения `WEBHOOK_URL`, `WEBHOOK_PATH`, `WEBAPP_HOST` и `WEBAPP_PORT` в файле `.env`.

## Тестирование

### Запуск тестов

```bash
pytest
```

### Запуск тестов с отчетом о покрытии

```bash
pytest --cov=. --cov-report=html
```

## Форматирование и проверка кода

### Форматирование кода с помощью Black

```bash
black .
```

### Проверка кода с помощью Ruff

```bash
ruff check .
```

### Проверка типов с помощью MyPy

```bash
mypy .
```

## Примеры использования API OpenAI

### Пример запроса для тестового гадания

```python
from services.openai_service import OpenAIService

async def example():
    openai_service = OpenAIService()
    test_reading = await openai_service.generate_test_reading()
    print(f"Карта: {test_reading.card.name}")
    print(f"Интерпретация: {test_reading.interpretation}")
    print(f"Рекомендуемый напиток: {test_reading.drink.name}")
```

### Пример запроса для премиум гадания

```python
from services.openai_service import OpenAIService

async def example():
    openai_service = OpenAIService()
    premium_reading = await openai_service.generate_tarot_reading("01.01.1990")
    print(f"Карты: {', '.join([card.name for card in premium_reading.cards])}")
    print(f"Общая интерпретация: {premium_reading.interpretation}")
    print(f"Рекомендуемые напитки: {', '.join([drink.name for drink in premium_reading.drink_recommendations])}")
```

## Лицензия

MIT

## Дисклеймер

Бот не поощряет чрезмерное употребление алкоголя. Все рекомендации носят развлекательный характер. Бот предназначен только для лиц старше 18 лет.