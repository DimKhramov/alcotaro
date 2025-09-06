import logging
from datetime import datetime
from typing import Union, Optional

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from config import config
from constants.texts import (
    WELCOME_MESSAGE, HELP_MESSAGE, DISCLAIMER, TEST_READING_START,
    TEST_READING_RESULT, TEST_READING_LIMIT_REACHED, AGE_VERIFICATION,
    CALLBACK_TEST_READING, CALLBACK_HELP, CALLBACK_BACK,
    CALLBACK_CONFIRM_AGE, CALLBACK_DECLINE_AGE
)
from keyboards.inline import (
    get_start_keyboard, get_help_keyboard, get_back_keyboard,
    get_age_verification_keyboard, get_after_reading_keyboard
)
from services.openai_service import OpenAIService
from utils.storage import UserStorage, ReadingStorage
from utils.animations import delay
from models.schemas import UserState

# Настройка логирования
logger = logging.getLogger(__name__)

# Helper to safely answer callback queries
async def safe_callback_answer(event: CallbackQuery) -> None:
    try:
        await event.answer()
    except TelegramBadRequest:
        pass

# Создание роутера
router = Router(name="tarot")

# Определение состояний FSM для верификации возраста
class AgeVerificationStates(StatesGroup):
    waiting_for_confirmation = State()


# Регистрация обработчиков
def register_tarot_handlers(bot: Bot) -> None:
    """Регистрирует обработчики для команд бота.
    
    Args:
        bot: Экземпляр бота.
    """
    # Создание сервисов
    openai_service = OpenAIService()
    
    # Хранилища данных
    user_storage = UserStorage()
    reading_storage = ReadingStorage()
    
    @router.message(CommandStart())
    async def command_start(message: Message, state: FSMContext) -> None:
        """Обрабатывает команду /start.
        
        Args:
            message: Объект сообщения.
            state: Контекст состояния FSM.
        """
        try:
            # Получаем состояние пользователя
            user_id = message.from_user.id
            user_state = await user_storage.get_user_state(user_id)
            
            # Если пользователь новый или не подтвердил возраст
            if user_state is None or not user_state.age_confirmed:
                # Создаем нового пользователя, если его нет
                if user_state is None:
                    user_state = UserState(user_id=user_id)
                    await user_storage.save_user_state(user_state)
                
                # Отправляем запрос на подтверждение возраста
                await message.answer(
                    text=AGE_VERIFICATION,
                    parse_mode="HTML",
                    reply_markup=get_age_verification_keyboard()
                )
                
                # Устанавливаем состояние ожидания подтверждения возраста
                await state.set_state(AgeVerificationStates.waiting_for_confirmation)
                return
            
            # Отправляем приветственное сообщение
            await message.answer(
                text=WELCOME_MESSAGE.format(disclaimer=DISCLAIMER),
                parse_mode="HTML",
                reply_markup=get_start_keyboard()
            )
            
            # Сбрасываем состояние
            await state.clear()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке команды /start: {e}")
            await message.answer(
                text="<b>⚠️ Произошла ошибка</b>\n\n"
                     "Пожалуйста, попробуйте позже или обратитесь к администратору.",
                parse_mode="HTML"
            )
    
    @router.callback_query(AgeVerificationStates.waiting_for_confirmation, F.data == CALLBACK_CONFIRM_AGE)
    async def confirm_age(callback: CallbackQuery, state: FSMContext) -> None:
        """Обрабатывает подтверждение возраста.
        
        Args:
            callback: Объект callback запроса.
            state: Контекст состояния FSM.
        """
        try:
            # Обновляем состояние пользователя
            user_id = callback.from_user.id
            user_state = await user_storage.get_user_state(user_id)
            
            if user_state is None:
                user_state = UserState(user_id=user_id)
            
            user_state.confirm_age()
            await user_storage.save_user_state(user_state)
            
            # Отправляем приветственное сообщение
            await callback.message.edit_text(
                text=WELCOME_MESSAGE.format(disclaimer=DISCLAIMER),
                parse_mode="HTML",
                reply_markup=get_start_keyboard()
            )
            
            # Сбрасываем состояние
            await state.clear()
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Ошибка при подтверждении возраста: {e}")
            await callback.message.edit_text(
                text="<b>⚠️ Произошла ошибка</b>\n\n"
                     "Пожалуйста, попробуйте позже или обратитесь к администратору.",
                parse_mode="HTML"
            )
            await callback.answer()
    
    @router.callback_query(AgeVerificationStates.waiting_for_confirmation, F.data == CALLBACK_DECLINE_AGE)
    async def decline_age(callback: CallbackQuery, state: FSMContext) -> None:
        """Обрабатывает отклонение подтверждения возраста.
        
        Args:
            callback: Объект callback запроса.
            state: Контекст состояния FSM.
        """
        try:
            # Отправляем сообщение о невозможности использования бота
            await callback.message.edit_text(
                text="<b>⚠️ Ограничение по возрасту</b>\n\n"
                     "К сожалению, вы не можете использовать этого бота, "
                     "так как он предназначен только для лиц старше 18 лет.",
                parse_mode="HTML"
            )
            
            # Сбрасываем состояние
            await state.clear()
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Ошибка при отклонении подтверждения возраста: {e}")
            await callback.message.edit_text(
                text="<b>⚠️ Произошла ошибка</b>\n\n"
                     "Пожалуйста, попробуйте позже или обратитесь к администратору.",
                parse_mode="HTML"
            )
            await callback.answer()
    
    @router.message(Command("help"))
    @router.callback_query(F.data == CALLBACK_HELP)
    async def command_help(event: Union[Message, CallbackQuery]) -> None:
        """Обрабатывает команду /help.
        
        Args:
            event: Объект сообщения или callback запроса.
        """
        try:
            # Формируем текст сообщения
            text = HELP_MESSAGE.format(disclaimer=DISCLAIMER)
            
            # Отправляем сообщение в зависимости от типа события
            if isinstance(event, Message):
                await event.answer(
                    text=text,
                    parse_mode="HTML",
                    reply_markup=get_help_keyboard()
                )
            else:  # CallbackQuery
                await event.message.answer(
                    text=text,
                    parse_mode="HTML",
                    reply_markup=get_help_keyboard()
                )
                await safe_callback_answer(event)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке команды /help: {e}")
            error_text = "<b>⚠️ Произошла ошибка</b>\n\n" \
                         "Пожалуйста, попробуйте позже или обратитесь к администратору."
            
            if isinstance(event, Message):
                await event.answer(
                    text=error_text,
                    parse_mode="HTML"
                )
            else:  # CallbackQuery
                await event.message.answer(
                    text=error_text,
                    parse_mode="HTML"
                )
                await event.answer()
    
    @router.message(Command("test"))
    @router.callback_query(F.data == CALLBACK_TEST_READING)
    async def start_test_reading(event: Union[Message, CallbackQuery]) -> None:
        """Начинает процесс тестового гадания.
        
        Args:
            event: Объект сообщения или callback запроса.
        """
        try:
            # Получаем ID пользователя
            user_id = event.from_user.id
            
            # Проверяем, подтвердил ли пользователь возраст
            user_state = await user_storage.get_user_state(user_id)
            if user_state is None or not user_state.age_confirmed:
                # Отправляем запрос на подтверждение возраста
                text = AGE_VERIFICATION
                if isinstance(event, Message):
                    await event.answer(
                        text=text,
                        parse_mode="HTML",
                        reply_markup=get_age_verification_keyboard()
                    )
                else:  # CallbackQuery
                    await event.message.edit_text(
                        text=text,
                        parse_mode="HTML",
                        reply_markup=get_age_verification_keyboard()
                    )
                    await safe_callback_answer(event)
                return
            
            # Проверяем, не превышен ли лимит бесплатных гаданий
            free_users = config.get_free_users()
            if not user_state.can_do_test_reading(config.FREE_TEST_LIMIT, free_users):
                text = TEST_READING_LIMIT_REACHED.format(limit=config.FREE_TEST_LIMIT)
                if isinstance(event, Message):
                    await event.answer(
                        text=text,
                        parse_mode="HTML",
                        reply_markup=get_back_keyboard()
                    )
                else:  # CallbackQuery
                    await event.message.edit_text(
                        text=text,
                        parse_mode="HTML",
                        reply_markup=get_back_keyboard()
                    )
                    await safe_callback_answer(event)
                return
            
            # Отправляем сообщение о начале гадания
            if isinstance(event, Message):
                await event.answer(
                    text=TEST_READING_START,
                    parse_mode="HTML"
                )
            else:  # CallbackQuery
                await event.message.edit_text(
                    text=TEST_READING_START,
                    parse_mode="HTML"
                )
                await safe_callback_answer(event)
            
            # Отправляем отдельное сообщение о подготовке к гаданию
            preparing_message = await bot.send_message(
                chat_id=event.from_user.id if isinstance(event, Message) else event.message.chat.id,
                text="<b>🔮 Подготовка к гаданию...</b>",
                parse_mode="HTML"
            )
            await delay(2)
            
            # Отправляем отдельное сообщение о выборе карты
            selecting_message = await bot.send_message(
                chat_id=event.from_user.id if isinstance(event, Message) else event.message.chat.id,
                text="<b>🔮 Выбираю карту...</b>",
                parse_mode="HTML"
            )
            await delay(2)
            
            # Отправляем отдельное сообщение о размышлении
            thinking_message = await bot.send_message(
                chat_id=event.from_user.id if isinstance(event, Message) else event.message.chat.id,
                text="<b>🤔 Размышляю над картой...</b>",
                parse_mode="HTML"
            )
            await delay(2)
            
            # Генерация тестового гадания
            test_reading = await openai_service.generate_test_reading()

            # Проверяем, успешно ли сгенерирован ответ OpenAI
            if not getattr(test_reading, "success", True):
                await bot.send_message(
                    chat_id=thinking_message.chat.id,
                    text=f"<b>⚠️ Не удалось получить ответ от карт\n</b>{getattr(test_reading, 'error', 'Попробуйте позже.')}",
                    parse_mode="HTML",
                    reply_markup=get_start_keyboard()
                )
                return

            # Сохраняем гадание в хранилище
            await reading_storage.save_reading({**test_reading.model_dump(), "user_id": user_id})

            # Обновляем счетчик тестовых гаданий пользователя
            user_state.increment_test_readings()
            await user_storage.save_user_state(user_state)

            # Формируем текст результата гадания
            # Ответ от OpenAI может быть в двух форматах:
            # 1. Новый: поля card, drink, interpretation находятся на верхнем уровне
            # 2. Старый: внутри reading, где card находится в reading.cards[0]

            card_obj = getattr(test_reading, "card", None)
            drink_obj = getattr(test_reading, "drink", None)
            interpretation = getattr(test_reading, "interpretation", None)

            # Если поля отсутствуют, пробуем извлечь их из test_reading.reading
            if card_obj is None and getattr(test_reading, "reading", None):
                inner = test_reading.reading
                if getattr(inner, "cards", None):
                    card_obj = inner.cards[0]
                interpretation = interpretation or getattr(inner, "general_interpretation", None)

            # Формируем строку названия карты
            if not card_obj:
                raise ValueError("Ответ OpenAI не содержит информацию о карте")

            # Обрабатываем card_obj как словарь или объект
            if isinstance(card_obj, dict):
                card_name = card_obj.get("name", "Неизвестная карта")
                if card_obj.get("suit"):
                    card_name += f" ({card_obj.get('suit')})"
            else:
                card_name = f"{card_obj.name}"
                if getattr(card_obj, "suit", None):
                    card_name += f" ({card_obj.suit})"

            # Рекомендация напитка
            if drink_obj is None:
                alcohol_rec = None
                if isinstance(card_obj, dict):
                    alcohol_rec = card_obj.get("alcohol_recommendation")
                else:
                    alcohol_rec = getattr(card_obj, "alcohol_recommendation", None)
                
                if alcohol_rec:
                    drink_obj = type("_Drink", (), {"name": "Напиток", "description": alcohol_rec})()

            if drink_obj:
                if isinstance(drink_obj, dict):
                    drink_name = drink_obj.get("name", "Напиток")
                    drink_desc = drink_obj.get("description", "")
                else:
                    drink_name = getattr(drink_obj, "name", "Напиток")
                    drink_desc = getattr(drink_obj, "description", "")
                
                drink_recommendation = (
                    f"<b>{drink_name}</b>\n"
                    f"{drink_desc}"
                )
            else:
                drink_recommendation = ""

            interpretation = interpretation or "—"
            
            # Отправляем результат гадания как отдельное сообщение
            await bot.send_message(
                chat_id=thinking_message.chat.id,
                text=TEST_READING_RESULT.format(
                    card_name=card_name,
                    interpretation=interpretation,
                    drink_recommendation=drink_recommendation
                ),
                parse_mode="HTML",
                reply_markup=get_after_reading_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Ошибка при начале тестового гадания: {e}")
            error_text = "<b>⚠️ Произошла ошибка</b>\n\n" \
                         "Пожалуйста, попробуйте позже или обратитесь к администратору."
            
            if isinstance(event, Message):
                await event.answer(
                    text=error_text,
                    parse_mode="HTML",
                    reply_markup=get_start_keyboard()
                )
            else:  # CallbackQuery
                await event.message.edit_text(
                    text=error_text,
                    parse_mode="HTML",
                    reply_markup=get_start_keyboard()
                )
                await event.answer()
    
    @router.callback_query(F.data == CALLBACK_BACK)
    async def go_back(callback: CallbackQuery) -> None:
        """Обрабатывает возврат в главное меню.
        
        Args:
            callback: Объект callback запроса.
        """
        try:
            # Возвращаемся в главное меню
            await callback.message.edit_text(
                text=WELCOME_MESSAGE.format(disclaimer=DISCLAIMER),
                parse_mode="HTML",
                reply_markup=get_start_keyboard()
            )
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Ошибка при возврате в главное меню: {e}")
            await callback.message.edit_text(
                text="<b>⚠️ Произошла ошибка</b>\n\n"
                     "Пожалуйста, попробуйте позже или обратитесь к администратору.",
                parse_mode="HTML",
                reply_markup=get_start_keyboard()
            )
            await callback.answer()