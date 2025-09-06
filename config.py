import os
from pathlib import Path
from typing import List, Optional, Set

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения, загружаемая из переменных окружения."""
    
    # Базовые настройки
    BASE_DIR: Path = Path(__file__).parent
    DEBUG: bool = Field(default=False)
    
    # Telegram Bot
    BOT_TOKEN: str
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_PATH: Optional[str] = None
    WEBAPP_HOST: str = "127.0.0.1"
    WEBAPP_PORT: int = 8000
    
    # Платежи через Telegram Stars
    PAYMENT_PROVIDER_TOKEN: str = ""  # Не используется для Telegram Stars
    PREMIUM_READING_PRICE: float = 50.0  # Цена в Telegram Stars
    CURRENCY: str = "XTR"  # Telegram Stars
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4-turbo"
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_TEMPERATURE: float = 0.7
    
    # Ограничения
    FREE_TEST_LIMIT: int = 3  # Количество бесплатных тестов
    FREE_USERS: str = ""  # Список ID пользователей с бесплатным доступом (через запятую)
    
    # Анимации
    ANIMATION_DELAY_SHORT: float = 0.5  # Короткая задержка в секундах
    ANIMATION_DELAY_MEDIUM: float = 1.0  # Средняя задержка в секундах
    ANIMATION_DELAY_LONG: float = 2.0  # Длинная задержка в секундах
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    def get_free_users(self) -> Set[int]:
        """Получить список ID пользователей с бесплатным доступом."""
        try:
            if self.FREE_USERS:
                # Парсим строку с ID пользователей, разделенных запятыми
                user_ids = self.FREE_USERS.split(",")
                return {int(user_id.strip()) for user_id in user_ids if user_id.strip()}
        except (ValueError, TypeError) as e:
            print(f"Ошибка при парсинге FREE_USERS: {e}")
        return set()


# Создаем экземпляр настроек
config = Settings()