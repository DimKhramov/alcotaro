import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from handlers.tarot import router as tarot_router, register_tarot_handlers
from handlers.payments import router as payments_router, register_payment_handlers
from keep_alive import keep_alive

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path("logs/bot.log"), encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Основная функция запуска бота."""
    # Создаем директорию для логов, если её нет
    Path("logs").mkdir(exist_ok=True)
    
    # Создаем директории для хранения данных, если их нет
    Path("data").mkdir(exist_ok=True)
    Path("data/users").mkdir(exist_ok=True)
    Path("data/readings").mkdir(exist_ok=True)
    
    # Инициализация бота и диспетчера
    from aiogram.client.default import DefaultBotProperties
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрация обработчиков
    register_tarot_handlers(bot)
    register_payment_handlers(bot)
    
    # Регистрация роутеров
    dp.include_router(tarot_router)
    dp.include_router(payments_router)
    
    # Запуск бота
    logger.info("Запуск бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Запускаем keep_alive для Replit
    keep_alive()
    
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)