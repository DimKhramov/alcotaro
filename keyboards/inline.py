from typing import List, Optional, Dict, Any, Union
from abc import ABC, abstractmethod

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pydantic import BaseModel, validator

from constants.texts import (
    BUTTON_TEST_READING, BUTTON_PREMIUM_READING, BUTTON_HELP, BUTTON_BACK, BUTTON_PAY,
    BUTTON_CONFIRM_AGE, BUTTON_DECLINE_AGE, BUTTON_NEW_READING
)
from constants.callbacks import CallbackData


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для стартового сообщения.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для тестового и премиум-гадания, а также помощи.
    """
    return StartKeyboardBuilder().create()


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для сообщения помощи.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой возврата назад.
    """
    return SimpleBackKeyboardBuilder().create()


def get_premium_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для премиум-гадания.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками оплаты и возврата назад.
    """
    return PremiumKeyboardBuilder().create()


def get_age_verification_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для подтверждения возраста.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками подтверждения и отклонения возраста.
    """
    return AgeVerificationKeyboardBuilder().create()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру только с кнопкой возврата назад.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой возврата назад.
    """
    return SimpleBackKeyboardBuilder().create()


def get_after_reading_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру после завершения гадания с кнопкой для нового гадания.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для нового гадания и основными опциями.
    """
    return AfterReadingKeyboardBuilder().create()


class BaseKeyboardBuilder(ABC):
    """Базовый класс для создания клавиатур с общими методами."""
    
    def __init__(self):
        self.builder = InlineKeyboardBuilder()
    
    def add_button(self, text: str, callback_data: str) -> 'BaseKeyboardBuilder':
        """Добавляет кнопку в клавиатуру.
        
        Args:
            text: Текст кнопки.
            callback_data: Callback данные.
            
        Returns:
            Экземпляр builder для цепочки вызовов.
        """
        if not CallbackData.is_valid_callback(callback_data):
            raise ValueError(f"Недопустимый callback data: {callback_data}")
        
        self.builder.row(InlineKeyboardButton(text=text, callback_data=callback_data))
        return self
    
    def add_row(self, *buttons: tuple[str, str]) -> 'BaseKeyboardBuilder':
        """Добавляет ряд кнопок.
        
        Args:
            *buttons: Кортежи (text, callback_data) для кнопок.
            
        Returns:
            Экземпляр builder для цепочки вызовов.
        """
        row_buttons = []
        for text, callback_data in buttons:
            if not CallbackData.is_valid_callback(callback_data):
                raise ValueError(f"Недопустимый callback data: {callback_data}")
            row_buttons.append(InlineKeyboardButton(text=text, callback_data=callback_data))
        
        self.builder.row(*row_buttons)
        return self
    
    def add_back_button(self) -> 'BaseKeyboardBuilder':
        """Добавляет кнопку "Назад".
        
        Returns:
            Экземпляр builder для цепочки вызовов.
        """
        return self.add_button(BUTTON_BACK, CallbackData.BACK)
    
    def build(self) -> InlineKeyboardMarkup:
        """Создает финальную клавиатуру.
        
        Returns:
            Готовая клавиатура.
        """
        return self.builder.as_markup()
    
    @abstractmethod
    def create(self) -> InlineKeyboardMarkup:
        """Абстрактный метод для создания специфичной клавиатуры."""
        pass


class StartKeyboardBuilder(BaseKeyboardBuilder):
    """Builder для стартовой клавиатуры."""
    
    def create(self) -> InlineKeyboardMarkup:
        """Создает стартовую клавиатуру."""
        return (self
                .add_button(BUTTON_TEST_READING, CallbackData.TEST_READING)
                .add_button(BUTTON_PREMIUM_READING, CallbackData.PREMIUM_READING)
                .add_button(BUTTON_HELP, CallbackData.HELP)
                .build())


class PremiumKeyboardBuilder(BaseKeyboardBuilder):
    """Builder для премиум клавиатуры."""
    
    def create(self) -> InlineKeyboardMarkup:
        """Создает премиум клавиатуру."""
        return (self
                .add_button(BUTTON_PAY, CallbackData.PAY)
                .add_back_button()
                .build())


class AgeVerificationKeyboardBuilder(BaseKeyboardBuilder):
    """Builder для клавиатуры подтверждения возраста."""
    
    def create(self) -> InlineKeyboardMarkup:
        """Создает клавиатуру подтверждения возраста."""
        return (self
                .add_button(BUTTON_CONFIRM_AGE, CallbackData.CONFIRM_AGE)
                .add_button(BUTTON_DECLINE_AGE, CallbackData.DECLINE_AGE)
                .build())


class SimpleBackKeyboardBuilder(BaseKeyboardBuilder):
    """Builder для простой клавиатуры с кнопкой "Назад"."""
    
    def create(self) -> InlineKeyboardMarkup:
        """Создает простую клавиатуру с кнопкой назад."""
        return self.add_back_button().build()


class KeyboardButtonData(BaseModel):
    """Модель для валидации данных кнопки клавиатуры."""
    text: str
    callback_data: str
    
    @validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Текст кнопки не может быть пустым')
        if len(v) > 64:
            raise ValueError('Текст кнопки не может превышать 64 символа')
        return v.strip()
    
    @validator('callback_data')
    def validate_callback_data(cls, v):
        if not v or not v.strip():
            raise ValueError('Callback data не может быть пустым')
        if len(v) > 64:
            raise ValueError('Callback data не может превышать 64 символа')
        if not CallbackData.is_valid_callback(v):
            raise ValueError(f'Недопустимый callback data: {v}')
        return v.strip()


class CustomKeyboardBuilder(BaseKeyboardBuilder):
    """Builder для создания кастомных клавиатур."""
    
    def __init__(self, buttons: List[KeyboardButtonData]):
        super().__init__()
        self.buttons = buttons
        self._validate_buttons()
    
    def _validate_buttons(self) -> None:
        """Валидирует список кнопок.
        
        Raises:
            ValueError: Если список кнопок некорректен.
        """
        if not self.buttons:
            raise ValueError("Список кнопок не может быть пустым")
        
        if len(self.buttons) > 10:
            raise ValueError("Максимальное количество кнопок: 10")
    
    def create(self) -> InlineKeyboardMarkup:
        """Создает кастомную клавиатуру.
        
        Returns:
            Готовая клавиатура с кастомными кнопками.
        """
        for button in self.buttons:
            self.add_button(button.text, button.callback_data)
        
        return self.build()


class AfterReadingKeyboardBuilder(BaseKeyboardBuilder):
    """Builder для клавиатуры после завершения гадания."""
    
    def create(self) -> InlineKeyboardMarkup:
        """Создает клавиатуру после завершения гадания."""
        return (self
                .add_button(BUTTON_NEW_READING, CallbackData.PREMIUM_READING)
                .add_button(BUTTON_TEST_READING, CallbackData.TEST_READING)
                .add_button(BUTTON_HELP, CallbackData.HELP)
                .build())


def get_custom_keyboard(buttons: List[KeyboardButtonData]) -> InlineKeyboardMarkup:
    """Создает кастомную клавиатуру из списка кнопок.
    
    Args:
        buttons: Список данных кнопок для создания клавиатуры.
        
    Returns:
        Клавиатура с переданными кнопками.
        
    Raises:
        ValueError: Если список кнопок пуст или содержит более 10 кнопок.
        ValueError: Если callback_data кнопки не является валидным значением CallbackData.
    """
    return CustomKeyboardBuilder(buttons).create()