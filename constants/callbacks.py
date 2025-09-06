"""Константы для callback данных."""

from enum import Enum


class CallbackData(str, Enum):
    """Enum для callback данных кнопок."""
    
    # Основные действия
    TEST_READING = "test_reading"
    PREMIUM_READING = "premium_reading"
    HELP = "help"
    BACK = "back"
    PAY = "pay"
    
    # Верификация возраста
    CONFIRM_AGE = "confirm_age"
    DECLINE_AGE = "decline_age"
    
    # Дополнительные действия (для будущего расширения)
    CANCEL = "cancel"
    RETRY = "retry"
    SETTINGS = "settings"
    HISTORY = "history"
    
    @classmethod
    def get_all_callbacks(cls) -> list[str]:
        """Получить все доступные callback данные.
        
        Returns:
            Список всех callback данных.
        """
        return [callback.value for callback in cls]
    
    @classmethod
    def is_valid_callback(cls, callback: str) -> bool:
        """Проверить, является ли callback валидным.
        
        Args:
            callback: Строка callback для проверки.
            
        Returns:
            True, если callback валиден, иначе False.
        """
        return callback in cls.get_all_callbacks()