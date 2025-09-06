import json
import logging
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional, Union, List, Type, TypeVar
from enum import Enum

from openai import OpenAI, APIError, RateLimitError, APIConnectionError, AuthenticationError, PermissionDeniedError
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

from config import config
from models.schemas import (
    TestReadingResponse, TarotReadingResponse, TarotMessageResponse,
    TestReading, PremiumReading, Card, CardSuit
)
from constants.prompts import (
    TEST_READING_SYSTEM_PROMPT, TEST_READING_USER_PROMPT,
    TAROT_READING_SYSTEM_PROMPT, TAROT_READING_USER_PROMPT,
    TAROT_MESSAGE_SYSTEM_PROMPT, TAROT_MESSAGE_USER_PROMPT
)

# Настройка логирования
logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Типы ошибок для категоризации."""
    API_ERROR = "api_error"
    RATE_LIMIT = "rate_limit"
    CONNECTION_ERROR = "connection_error"
    AUTHENTICATION_ERROR = "authentication_error"
    PERMISSION_ERROR = "permission_error"
    VALIDATION_ERROR = "validation_error"
    JSON_PARSE_ERROR = "json_parse_error"
    UNKNOWN_ERROR = "unknown_error"


class OpenAIMetrics:
    """Класс для сбора метрик работы с OpenAI API."""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.error_counts = {error_type.value: 0 for error_type in ErrorType}
        self.total_response_time = 0.0
        self.average_response_time = 0.0
    
    def record_request(self, success: bool, response_time: float, error_type: Optional[ErrorType] = None):
        """Записывает метрики запроса."""
        self.total_requests += 1
        self.total_response_time += response_time
        self.average_response_time = self.total_response_time / self.total_requests
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error_type:
                self.error_counts[error_type.value] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / max(self.total_requests, 1) * 100,
            "average_response_time": round(self.average_response_time, 3),
            "error_counts": self.error_counts
        }

# Тип для дженерика
T = TypeVar('T', bound=BaseModel)


class OpenAIService:
    """Сервис для работы с OpenAI API."""
    
    def __init__(self):
        """Инициализация сервиса."""
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL
        self.max_tokens = config.OPENAI_MAX_TOKENS
        self.temperature = config.OPENAI_TEMPERATURE
        self.metrics = OpenAIMetrics()
        logger.info("OpenAI сервис инициализирован")
    
    def _categorize_error(self, error: Exception) -> ErrorType:
        """Категоризирует тип ошибки."""
        if isinstance(error, RateLimitError):
            return ErrorType.RATE_LIMIT
        elif isinstance(error, APIConnectionError):
            return ErrorType.CONNECTION_ERROR
        elif isinstance(error, AuthenticationError):
            return ErrorType.AUTHENTICATION_ERROR
        elif isinstance(error, PermissionDeniedError):
            return ErrorType.PERMISSION_ERROR
        elif isinstance(error, APIError):
            return ErrorType.API_ERROR
        elif isinstance(error, ValidationError):
            return ErrorType.VALIDATION_ERROR
        elif isinstance(error, json.JSONDecodeError):
            return ErrorType.JSON_PARSE_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    def _log_error_details(self, error: Exception, context: Dict[str, Any]):
        """Логирует детальную информацию об ошибке."""
        error_type = self._categorize_error(error)
        
        error_details = {
            "error_type": error_type.value,
            "error_message": str(error),
            "error_class": error.__class__.__name__,
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4())
        }
        
        # Добавляем специфичные детали для разных типов ошибок
        if isinstance(error, APIError):
            error_details.update({
                "status_code": getattr(error, 'status_code', None),
                "error_code": getattr(error, 'code', None),
                "error_param": getattr(error, 'param', None)
            })
        
        logger.error(f"OpenAI API Error: {json.dumps(error_details, ensure_ascii=False, indent=2)}")
        return error_type
    
    def get_metrics(self) -> Dict[str, Any]:
        """Возвращает метрики сервиса."""
        return self.metrics.get_stats()
    
    @retry(
        retry=retry_if_exception_type((APIError, RateLimitError, APIConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _make_request(
        self, system_prompt: str, user_prompt: str, **kwargs
    ) -> Dict[str, Any]:
        """Выполняет запрос к OpenAI API с повторными попытками.
        
        Args:
            system_prompt: Системный промпт.
            user_prompt: Пользовательский промпт.
            **kwargs: Дополнительные параметры для форматирования промпта.
            
        Returns:
            Ответ от OpenAI API.
            
        Raises:
            Exception: Если все попытки запроса завершились неудачно.
        """
        start_time = time.time()
        request_context = {
            "system_prompt_length": len(system_prompt),
            "user_prompt_length": len(user_prompt),
            "kwargs": {k: str(v)[:100] for k, v in kwargs.items()},  # Ограничиваем длину для логов
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        
        # Форматируем промпты с переданными параметрами
        try:
            if kwargs:
                # Используем безопасное форматирование, которое не затрагивает двойные фигурные скобки
                formatted_system_prompt = system_prompt
                formatted_user_prompt = user_prompt
                for key, value in kwargs.items():
                    formatted_system_prompt = formatted_system_prompt.replace(f"{{{key}}}", str(value))
                    formatted_user_prompt = formatted_user_prompt.replace(f"{{{key}}}", str(value))
            else:
                # Если параметры не переданы, избегаем форматирования, чтобы сохранить фигурные скобки JSON
                formatted_system_prompt = system_prompt
                formatted_user_prompt = user_prompt
        except KeyError as e:
            error_type = self._log_error_details(
                ValueError(f"Отсутствует параметр для форматирования промпта: {e}"),
                request_context
            )
            self.metrics.record_request(False, time.time() - start_time, error_type)
            raise
            
        # Логируем промпты (без конфиденциальных данных)
        logger.debug(f"System prompt: {formatted_system_prompt}")
        logger.debug(f"User prompt: {formatted_user_prompt}")
        logger.debug(f"Отправка запроса к OpenAI API: {request_context}")
        
        try:
            # Выполняем запрос к API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": formatted_system_prompt},
                    {"role": "user", "content": formatted_user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            # Получаем текст ответа
            response_text = response.choices[0].message.content
            
            if not response_text:
                error = ValueError("Пустой ответ от OpenAI API")
                error_type = self._log_error_details(error, request_context)
                self.metrics.record_request(False, time.time() - start_time, error_type)
                raise error
            
            # Парсим JSON
            try:
                parsed_response = json.loads(response_text)
                if not isinstance(parsed_response, dict):
                    raise ValueError("Ответ не является JSON-объектом")
                response_time = time.time() - start_time
                self.metrics.record_request(True, response_time)
                
                logger.debug(f"Успешный запрос к OpenAI API за {response_time:.3f}s")
                return parsed_response
                
            except json.JSONDecodeError as e:
                error_context = request_context.copy()
                error_context["response_text"] = response_text[:500]  # Первые 500 символов
                error_type = self._log_error_details(e, error_context)
                self.metrics.record_request(False, time.time() - start_time, error_type)
                raise ValueError(f"Невалидный JSON в ответе: {e}")
                
        except (APIError, RateLimitError, APIConnectionError, AuthenticationError, PermissionDeniedError) as e:
            error_type = self._log_error_details(e, request_context)
            self.metrics.record_request(False, time.time() - start_time, error_type)
            raise
        except Exception as e:
            error_type = self._log_error_details(e, request_context)
            self.metrics.record_request(False, time.time() - start_time, error_type)
            raise
    
    async def _parse_response(
        self, response_data: Dict[str, Any], response_model: Type[T], fallback: T
    ) -> T:
        """Парсит ответ от OpenAI API в модель данных.
        
        Args:
            response_data: Данные ответа.
            response_model: Модель данных для парсинга.
            fallback: Запасной вариант ответа в случае ошибки.
            
        Returns:
            Экземпляр модели данных.
        """
        try:
            return response_model.model_validate(response_data)
        except ValidationError as e:
            logger.error(f"Ошибка валидации ответа: {e}\nОтвет: {response_data}")
            return fallback
    
    async def generate_test_reading(self) -> TestReadingResponse:
        """Генерирует тестовое гадание.
        
        Returns:
            Ответ с тестовым гаданием.
        """
        operation_start = time.time()
        operation_context = {
            "operation": "generate_test_reading",
            "timestamp": datetime.now().isoformat()
        }
        
        # Создаем запасной вариант ответа
        fallback = TestReadingResponse(
            success=False,
            error="Не удалось сгенерировать тестовое гадание"
        )
        
        try:
            logger.info("Начало генерации тестового гадания")
            
            # Выполняем запрос к API
            response_data = await self._make_request(
                system_prompt=TEST_READING_SYSTEM_PROMPT,
                user_prompt=TEST_READING_USER_PROMPT
            )
            
            # Парсим ответ
            result = await self._parse_response(response_data, TestReadingResponse, fallback)
            
            operation_time = time.time() - operation_start
            if result.success:
                logger.info(f"Тестовое гадание успешно сгенерировано за {operation_time:.3f}s")
            else:
                logger.warning(f"Тестовое гадание сгенерировано с ошибками за {operation_time:.3f}s: {result.error}")
            
            return result
            
        except Exception as e:
            operation_time = time.time() - operation_start
            error_type = self._log_error_details(e, operation_context)
            logger.error(f"Критическая ошибка при генерации тестового гадания за {operation_time:.3f}s")
            
            # Обновляем fallback с более детальной информацией об ошибке
            fallback.error = f"Техническая ошибка: {error_type.value}"
            return fallback
    
    async def generate_tarot_reading(
        self, birthdate: Optional[str] = None, question: Optional[str] = None
    ) -> TarotReadingResponse:
        """Генерирует премиум-гадание на картах Таро.
        
        Args:
            birthdate: Дата рождения пользователя (опционально).
            question: Вопрос пользователя (опционально).
            
        Returns:
            Ответ с премиум-гаданием.
        """
        operation_start = time.time()
        operation_context = {
            "operation": "generate_tarot_reading",
            "has_birthdate": birthdate is not None,
            "has_question": question is not None,
            "birthdate_length": len(birthdate) if birthdate else 0,
            "question_length": len(question) if question else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Создаем запасной вариант ответа
        fallback = TarotReadingResponse(
            success=False,
            error="Не удалось сгенерировать гадание на картах Таро"
        )
        
        try:
            logger.info(f"Начало генерации таро-гадания: birthdate={bool(birthdate)}, question={bool(question)}")
            
            # Выполняем запрос к API
            response_data = await self._make_request(
                system_prompt=TAROT_READING_SYSTEM_PROMPT,
                user_prompt=TAROT_READING_USER_PROMPT,
                birthdate=birthdate or "Неизвестно",
                question=question or "Общий прогноз"
            )
            
            # Логируем сырой ответ от OpenAI для отладки
            logger.info(f"Raw OpenAI response: {response_data}")
            
            # Парсим ответ
            result = await self._parse_response(response_data, TarotReadingResponse, fallback)
            
            operation_time = time.time() - operation_start
            if result.success:
                logger.info(f"Таро-гадание успешно сгенерировано за {operation_time:.3f}s")
            else:
                logger.warning(f"Таро-гадание сгенерировано с ошибками за {operation_time:.3f}s: {result.error}")
            
            return result
            
        except Exception as e:
            operation_time = time.time() - operation_start
            error_type = self._log_error_details(e, operation_context)
            logger.error(f"Критическая ошибка при генерации таро-гадания за {operation_time:.3f}s")
            
            # Обновляем fallback с более детальной информацией об ошибке
            fallback.error = f"Техническая ошибка: {error_type.value}"
            return fallback
    
    async def generate_tarot_message(self, context: Optional[str] = None) -> TarotMessageResponse:
        """Генерирует сообщение от карт Таро.
        
        Args:
            context: Контекст для сообщения (опционально).
            
        Returns:
            Ответ с сообщением от карт Таро.
        """
        operation_start = time.time()
        operation_context = {
            "operation": "generate_tarot_message",
            "has_context": context is not None,
            "context_length": len(context) if context else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Создаем запасной вариант ответа
        fallback = TarotMessageResponse(
            success=False,
            error="Не удалось сгенерировать сообщение от карт Таро"
        )
        
        try:
            logger.info(f"Начало генерации таро-сообщения: context={bool(context)}")
            
            # Выполняем запрос к API
            response_data = await self._make_request(
                system_prompt=TAROT_MESSAGE_SYSTEM_PROMPT,
                user_prompt=TAROT_MESSAGE_USER_PROMPT,
                context=context or "Общее сообщение"
            )
            
            # Парсим ответ
            result = await self._parse_response(response_data, TarotMessageResponse, fallback)
            
            operation_time = time.time() - operation_start
            if result.success:
                logger.info(f"Таро-сообщение успешно сгенерировано за {operation_time:.3f}s")
            else:
                logger.warning(f"Таро-сообщение сгенерировано с ошибками за {operation_time:.3f}s: {result.error}")
            
            return result
            
        except Exception as e:
            operation_time = time.time() - operation_start
            error_type = self._log_error_details(e, operation_context)
            logger.error(f"Критическая ошибка при генерации таро-сообщения за {operation_time:.3f}s")
            
            # Обновляем fallback с более детальной информацией об ошибке
            fallback.error = f"Техническая ошибка: {error_type.value}"
            return fallback
    
    def log_service_stats(self):
        """Логирует статистику работы сервиса."""
        stats = self.get_metrics()
        logger.info(f"OpenAI Service Stats: {json.dumps(stats, ensure_ascii=False, indent=2)}")
        return stats


# Создаем экземпляр сервиса
openai_service = OpenAIService()