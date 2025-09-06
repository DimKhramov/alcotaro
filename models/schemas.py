from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union, Set

from pydantic import BaseModel, Field, field_validator, ConfigDict


class CardSuit(str, Enum):
    """Масти карт Таро."""
    CUPS = "cups"  # Кубки
    PENTACLES = "pentacles"  # Пентакли
    SWORDS = "swords"  # Мечи
    WANDS = "wands"  # Жезлы
    MAJOR = "major"  # Старшие арканы


class Card(BaseModel):
    """Модель карты Таро."""
    name: str  # Название карты
    suit: Optional[str] = None  # Масть карты (опционально)
    position: Optional[str] = None  # Положение (прямое/перевернутое)
    description: Optional[str] = None  # Описание значения карты
    interpretation: Optional[str] = None  # Интерпретация карты
    alcohol_recommendation: Optional[str] = None  # Рекомендация по алкоголю
    image_url: Optional[str] = None  # URL изображения карты (опционально)


class Reading(BaseModel):
    """Базовая модель гадания."""
    id: str  # Уникальный идентификатор гадания
    created_at: datetime = Field(default_factory=datetime.now)  # Дата и время создания
    question: Optional[str] = None  # Вопрос пользователя (если есть)
    cards: List[Card]  # Список карт в раскладе
    general_interpretation: str  # Общая интерпретация расклада
    
    @field_validator('created_at', mode='before')
    @classmethod
    def parse_datetime(cls, value):
        """Валидатор для преобразования строки в datetime."""
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value


class TestReading(Reading):
    """Модель тестового гадания."""
    personality_traits: List[str]  # Черты личности
    advice: str  # Совет


class DrinkRecommendation(BaseModel):
    """Модель рекомендации напитка."""
    name: str  # Название напитка
    description: str  # Описание напитка
    ingredients: List[str]  # Ингредиенты
    preparation: Optional[str] = None  # Рецепт приготовления


class PremiumReading(Reading):
    """Модель премиум-гадания."""
    birthdate: Optional[str] = None  # Дата рождения пользователя
    detailed_interpretations: Dict[str, str]  # Детальные интерпретации по аспектам
    future_prediction: str  # Предсказание на будущее
    special_message: Optional[str] = None  # Особое сообщение
    drink: DrinkRecommendation  # Рекомендация напитка
    overall_interpretation: str  # Общая интерпретация
    advice: str  # Совет


class OpenAIResponse(BaseModel):
    """Базовая модель ответа от OpenAI."""
    model_config = ConfigDict(extra="allow")
    success: bool = True  # Успешность запроса
    error: Optional[str] = None  # Сообщение об ошибке (если есть)


class TestReadingResponse(OpenAIResponse):
    """Модель ответа от OpenAI для тестового гадания."""
    reading: Optional[TestReading] = None  # Тестовое гадание


class TarotReadingResponse(OpenAIResponse):
    """Модель ответа от OpenAI для премиум-гадания."""
    reading: Optional[PremiumReading] = None  # Премиум-гадание


class TarotMessageResponse(OpenAIResponse):
    """Модель ответа от OpenAI для сообщения от карт Таро."""
    message: Optional[str] = None  # Сообщение
    card: Optional[Card] = None  # Карта


class UserState(BaseModel):
    """Модель состояния пользователя."""
    user_id: int  # ID пользователя
    username: Optional[str] = None  # Имя пользователя
    test_readings_count: int = 0  # Количество выполненных тестовых гаданий
    premium_readings_count: int = 0  # Количество выполненных премиум-гаданий
    age_confirmed: bool = False  # Подтверждение возраста
    last_reading_id: Optional[str] = None  # ID последнего гадания
    last_test_reading_date: Optional[str] = None  # Дата последнего тестового гадания
    last_premium_reading_date: Optional[str] = None  # Дата последнего премиум-гадания
    created_at: datetime = Field(default_factory=datetime.now)  # Дата и время создания
    updated_at: datetime = Field(default_factory=datetime.now)  # Дата и время обновления
    
    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def parse_datetime(cls, value):
        """Валидатор для преобразования строки в datetime."""
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value
    
    def increment_test_readings(self) -> None:
        """Увеличивает счетчик тестовых гаданий."""
        self.test_readings_count += 1
        self.last_test_reading_date = datetime.now().isoformat()
        self.updated_at = datetime.now()
    
    def increment_premium_readings(self) -> None:
        """Увеличивает счетчик премиум-гаданий."""
        self.premium_readings_count += 1
        self.last_premium_reading_date = datetime.now().isoformat()
        self.updated_at = datetime.now()
    
    def confirm_age(self) -> None:
        """Подтверждает возраст пользователя."""
        self.age_confirmed = True
        self.updated_at = datetime.now()
    
    def set_last_reading(self, reading_id: str) -> None:
        """Устанавливает ID последнего гадания."""
        self.last_reading_id = reading_id
        self.updated_at = datetime.now()
    
    def get_total_readings(self) -> int:
        """Возвращает общее количество гаданий."""
        return self.test_readings_count + self.premium_readings_count
    
    def can_do_test_reading(self, limit: int, free_users: Set[int]) -> bool:
        """Проверяет, может ли пользователь сделать тестовое гадание."""
        if self.user_id in free_users:
            return True
        return self.test_readings_count < limit
    
    def is_new_user(self) -> bool:
        """Проверяет, является ли пользователь новым."""
        return self.get_total_readings() == 0
    
    def update_timestamp(self) -> None:
        """Обновляет временную метку последнего обновления."""
        self.updated_at = datetime.now()