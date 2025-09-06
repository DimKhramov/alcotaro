import asyncio
import logging
from typing import List, Optional, Union, Callable, Any

from aiogram import Bot
from aiogram.types import Message

from config import config

# Настройка логирования
logger = logging.getLogger(__name__)


async def delay(seconds: float) -> None:
    """Создает задержку указанной продолжительности.
    
    Args:
        seconds: Продолжительность задержки в секундах.
    """
    await asyncio.sleep(seconds)


async def edit_message_animation(
    message: Message,
    frames: List[str],
    interval: float = config.ANIMATION_DELAY_SHORT,
    final_text: Optional[str] = None,
    parse_mode: str = "HTML"
) -> Message:
    """Анимирует сообщение, последовательно изменяя его текст.
    
    Args:
        message: Объект сообщения для анимации.
        frames: Список кадров (текстов) для анимации.
        interval: Интервал между кадрами в секундах.
        final_text: Финальный текст сообщения (если отличается от последнего кадра).
        parse_mode: Режим форматирования текста.
        
    Returns:
        Объект сообщения после анимации.
    """
    try:
        # Показываем каждый кадр анимации
        for frame in frames:
            await message.edit_text(frame, parse_mode=parse_mode)
            await delay(interval)
        
        # Если указан финальный текст, отображаем его
        if final_text and final_text != frames[-1]:
            return await message.edit_text(final_text, parse_mode=parse_mode)
        
        return message
    except Exception as e:
        logger.error(f"Ошибка при анимации сообщения: {e}")
        # В случае ошибки пытаемся отобразить финальный текст
        if final_text:
            try:
                return await message.edit_text(final_text, parse_mode=parse_mode)
            except Exception as inner_e:
                logger.error(f"Ошибка при отображении финального текста: {inner_e}")
        
        return message


async def animate_thinking(
    message: Message,
    frames_count: int = 5,
    interval: float = config.ANIMATION_DELAY_SHORT
) -> Message:
    """Создает анимацию размышления.
    
    Args:
        message: Объект сообщения для анимации.
        frames_count: Количество кадров анимации.
        interval: Интервал между кадрами в секундах.
        
    Returns:
        Объект сообщения после анимации.
    """
    # Создаем кадры анимации
    frames = [
        f"<b>🤔 Размышляю...</b>\n{'.' * (i % 4 + 1)}" 
        for i in range(frames_count)
    ]
    
    # Запускаем анимацию
    return await edit_message_animation(
        message=message,
        frames=frames,
        interval=interval
    )


async def animate_preparing_reading(
    message: Message,
    frames_count: int = 5,
    interval: float = config.ANIMATION_DELAY_MEDIUM
) -> Message:
    """Создает анимацию подготовки к гаданию.
    
    Args:
        message: Объект сообщения для анимации.
        frames_count: Количество кадров анимации.
        interval: Интервал между кадрами в секундах.
        
    Returns:
        Объект сообщения после анимации.
    """
    # Создаем кадры анимации
    frames = [
        f"<b>🔮 Подготовка к гаданию...</b>\n{'.' * (i % 4 + 1)}" 
        for i in range(frames_count)
    ]
    
    # Запускаем анимацию
    return await edit_message_animation(
        message=message,
        frames=frames,
        interval=interval
    )


async def animate_selecting_card(
    message: Message,
    card_name: str,
    frames_count: int = 5,
    interval: float = config.ANIMATION_DELAY_MEDIUM
) -> Message:
    """Создает анимацию выбора карты Таро.
    
    Args:
        message: Объект сообщения для анимации.
        card_name: Название выбранной карты.
        frames_count: Количество кадров анимации.
        interval: Интервал между кадрами в секундах.
        
    Returns:
        Объект сообщения после анимации.
    """
    # Создаем кадры анимации
    frames = [
        f"<b>🔮 Выбор карты...</b>\n{'.' * (i % 4 + 1)}" 
        for i in range(frames_count - 1)
    ]
    
    # Добавляем кадр с названием карты
    frames.append(f"<b>🔮 Выбрана карта:</b> <i>{card_name}</i>")
    
    # Запускаем анимацию
    return await edit_message_animation(
        message=message,
        frames=frames,
        interval=interval
    )


async def tarot_card_animation(
    message: Message,
    final_text: str,
    card_name: str = "Карта Таро",
    frames_count: int = 5,
    interval: float = config.ANIMATION_DELAY_MEDIUM
) -> Message:
    """Создает анимацию выбора карты Таро.
    
    Args:
        message: Объект сообщения для анимации.
        final_text: Финальный текст сообщения с результатом.
        card_name: Название карты для анимации.
        frames_count: Количество кадров анимации.
        interval: Интервал между кадрами в секундах.
        
    Returns:
        Объект сообщения после анимации.
    """
    # Создаем кадры анимации
    frames = [
        f"<b>🔮 Выбор карты...</b>\n{'.' * (i % 4 + 1)}" 
        for i in range(frames_count - 1)
    ]
    
    # Добавляем кадр с названием карты
    frames.append(f"<b>🔮 Выбрана карта:</b> <i>{card_name}</i>")
    
    # Запускаем анимацию
    return await edit_message_animation(
        message=message,
        frames=frames,
        interval=interval,
        final_text=final_text
    )


async def reading_preparation_animation(
    message: Message,
    final_text: str,
    frames_count: int = 6,
    interval: float = config.ANIMATION_DELAY_MEDIUM
) -> Message:
    """Создает анимацию подготовки к гаданию.
    
    Args:
        message: Объект сообщения для анимации.
        final_text: Финальный текст сообщения с результатом.
        frames_count: Количество кадров анимации.
        interval: Интервал между кадрами в секундах.
        
    Returns:
        Объект сообщения после анимации.
    """
    # Эмодзи для анимации
    emojis = ["🔮", "🧙‍♂️", "✨", "🍸", "🥃", "🍷", "🍹"]
    
    # Создаем кадры анимации
    frames = [
        f"<b>{emojis[i % len(emojis)]} Подготовка к гаданию...</b>\n{'.' * (i % 4 + 1)}" 
        for i in range(frames_count - 1)
    ]
    
    # Добавляем последний кадр
    frames.append("<b>✨ Гадание готово!</b>")
    
    # Запускаем анимацию
    return await edit_message_animation(
        message=message,
        frames=frames,
        interval=interval,
        final_text=final_text
    )


async def thinking_animation(
    message: Message,
    final_text: str,
    prefix: str = "Думаю",
    frames_count: int = 5,
    interval: float = config.ANIMATION_DELAY_SHORT
) -> Message:
    """Создает анимацию "думающего" сообщения.
    
    Args:
        message: Объект сообщения для анимации.
        final_text: Финальный текст сообщения.
        prefix: Префикс для анимации.
        frames_count: Количество кадров анимации.
        interval: Интервал между кадрами в секундах.
        
    Returns:
        Объект сообщения после анимации.
    """
    # Создаем кадры анимации
    frames = [
        f"<b>{prefix}{'.' * (i % 4 + 1)}</b>" 
        for i in range(frames_count)
    ]
    
    # Запускаем анимацию
    return await edit_message_animation(
        message=message,
        frames=frames,
        interval=interval,
        final_text=final_text
    )