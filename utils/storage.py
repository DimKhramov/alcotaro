import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, TypeVar, Generic, Type, Union

from pydantic import BaseModel

from config import config

# Настройка логирования
logger = logging.getLogger(__name__)

# Тип для дженерика
T = TypeVar('T', bound=BaseModel)


class Storage(Generic[T]):
    """Абстрактное хранилище данных с атомарной записью и блокировками."""
    
    def __init__(self, model_class: Type[T], file_path: Union[str, Path]):
        """Инициализация хранилища.
        
        Args:
            model_class: Класс модели данных (Pydantic).
            file_path: Путь к файлу хранилища.
        """
        self.model_class = model_class
        self.file_path = Path(file_path)
        self.lock = asyncio.Lock()
        self._ensure_dir_exists()
    
    def _ensure_dir_exists(self) -> None:
        """Убедиться, что директория для файла существует."""
        os.makedirs(self.file_path.parent, exist_ok=True)
    
    async def _read_data(self) -> Dict[str, Any]:
        """Прочитать данные из файла.
        
        Returns:
            Словарь с данными из файла или пустой словарь, если файл не существует.
        """
        try:
            if not self.file_path.exists():
                return {}
            
            async with self.lock:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Ошибка при чтении данных из {self.file_path}: {e}")
            return {}
    
    async def _write_data(self, data: Dict[str, Any]) -> bool:
        """Записать данные в файл атомарно.
        
        Args:
            data: Словарь с данными для записи.
            
        Returns:
            True, если запись прошла успешно, иначе False.
        """
        try:
            async with self.lock:
                # Создаем временный файл
                temp_file = self.file_path.with_suffix('.tmp')
                
                # Записываем данные во временный файл
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=self._json_serializer)
                
                # Атомарно заменяем оригинальный файл временным
                os.replace(temp_file, self.file_path)
                
                return True
        except Exception as e:
            logger.error(f"Ошибка при записи данных в {self.file_path}: {e}")
            return False
    
    def _json_serializer(self, obj: Any) -> Any:
        """Сериализатор для объектов, которые не могут быть сериализованы в JSON.
        
        Args:
            obj: Объект для сериализации.
            
        Returns:
            Сериализованный объект.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        raise TypeError(f"Объект типа {type(obj)} не может быть сериализован в JSON")


class UserStorage(Storage[BaseModel]):
    """Хранилище данных пользователей."""
    
    def __init__(self):
        """Инициализация хранилища пользователей."""
        super().__init__(BaseModel, config.BASE_DIR / "data" / "users.json")
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить данные пользователя по ID.
        
        Args:
            user_id: ID пользователя.
            
        Returns:
            Словарь с данными пользователя или None, если пользователь не найден.
        """
        data = await self._read_data()
        return data.get(str(user_id))
    
    async def save_user(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """Сохранить данные пользователя.
        
        Args:
            user_id: ID пользователя.
            user_data: Данные пользователя.
            
        Returns:
            True, если сохранение прошло успешно, иначе False.
        """
        data = await self._read_data()
        data[str(user_id)] = user_data
        return await self._write_data(data)
    
    async def update_user(self, user_id: int, **kwargs) -> bool:
        """Обновить данные пользователя.
        
        Args:
            user_id: ID пользователя.
            **kwargs: Данные для обновления.
            
        Returns:
            True, если обновление прошло успешно, иначе False.
        """
        data = await self._read_data()
        user_data = data.get(str(user_id), {})
        user_data.update(kwargs)
        user_data['updated_at'] = datetime.now().isoformat()
        data[str(user_id)] = user_data
        return await self._write_data(data)
    
    async def increment_test_readings_count(self, user_id: int) -> int:
        """Увеличить счетчик тестовых гаданий пользователя.
        
        Args:
            user_id: ID пользователя.
            
        Returns:
            Новое значение счетчика.
        """
        user_state = await self.get_user_state(user_id)
        if user_state is None:
            from models.schemas import UserState
            user_state = UserState(user_id=user_id)
        
        user_state.increment_test_readings()
        await self.save_user_state(user_state)
        return user_state.test_readings_count
    
    async def increment_premium_readings_count(self, user_id: int) -> int:
        """Увеличить счетчик премиум-гаданий пользователя.
        
        Args:
            user_id: ID пользователя.
            
        Returns:
            Новое значение счетчика.
        """
        user_state = await self.get_user_state(user_id)
        if user_state is None:
            from models.schemas import UserState
            user_state = UserState(user_id=user_id)
        
        user_state.increment_premium_readings()
        await self.save_user_state(user_state)
        return user_state.premium_readings_count
    
    async def set_age_confirmed(self, user_id: int, confirmed: bool = True) -> bool:
        """Установить флаг подтверждения возраста.
        
        Args:
            user_id: ID пользователя.
            confirmed: Значение флага.
            
        Returns:
            True, если установка прошла успешно, иначе False.
        """
        user_state = await self.get_user_state(user_id)
        if user_state is None:
            from models.schemas import UserState
            user_state = UserState(user_id=user_id)
        
        if confirmed:
            user_state.confirm_age()
        else:
            user_state.age_confirmed = False
            user_state.update_timestamp()
        
        return await self.save_user_state(user_state)
    
    async def set_last_reading_id(self, user_id: int, reading_id: str) -> bool:
        """Установить ID последнего гадания.
        
        Args:
            user_id: ID пользователя.
            reading_id: ID гадания.
            
        Returns:
            True, если установка прошла успешно, иначе False.
        """
        user_state = await self.get_user_state(user_id)
        if user_state is None:
            from models.schemas import UserState
            user_state = UserState(user_id=user_id)
        
        user_state.set_last_reading(reading_id)
        return await self.save_user_state(user_state)
    
    async def get_user_state(self, user_id: int) -> Optional['UserState']:
        """Получить состояние пользователя.
        
        Args:
            user_id: ID пользователя.
            
        Returns:
            Объект состояния пользователя или None, если пользователь не найден.
        """
        from models.schemas import UserState
        
        user_data = await self.get_user(user_id)
        if not user_data:
            return None
        
        try:
            return UserState(**user_data)
        except Exception as e:
            logger.error(f"Ошибка при создании объекта UserState: {e}")
            return None
    
    async def save_user_state(self, user_state: 'UserState') -> bool:
        """Сохранить состояние пользователя.
        
        Args:
            user_state: Объект состояния пользователя.
            
        Returns:
            True, если сохранение прошло успешно, иначе False.
        """
        user_data = user_state.model_dump()
        return await self.save_user(user_state.user_id, user_data)


class ReadingStorage(Storage[BaseModel]):
    """Хранилище данных гаданий."""
    
    def __init__(self):
        """Инициализация хранилища гаданий."""
        super().__init__(BaseModel, config.BASE_DIR / "data" / "readings.json")
    
    async def get_reading(self, reading_id: str) -> Optional[Dict[str, Any]]:
        """Получить данные гадания по ID.
        
        Args:
            reading_id: ID гадания.
            
        Returns:
            Словарь с данными гадания или None, если гадание не найдено.
        """
        data = await self._read_data()
        return data.get(reading_id)
    
    async def save_reading(self, reading_data: Dict[str, Any]) -> str:
        """Сохранить данные гадания.
        
        Args:
            reading_data: Данные гадания.
            
        Returns:
            ID сохраненного гадания.
        """
        data = await self._read_data()
        reading_id = reading_data.get('id', str(uuid.uuid4()))
        reading_data['id'] = reading_id
        data[reading_id] = reading_data
        await self._write_data(data)
        return reading_id
    
    async def get_user_readings(self, user_id: int) -> Dict[str, Dict[str, Any]]:
        """Получить все гадания пользователя.
        
        Args:
            user_id: ID пользователя.
            
        Returns:
            Словарь с гаданиями пользователя.
        """
        data = await self._read_data()
        return {k: v for k, v in data.items() if v.get('user_id') == user_id}


# Создаем экземпляры хранилищ
user_storage = UserStorage()
reading_storage = ReadingStorage()