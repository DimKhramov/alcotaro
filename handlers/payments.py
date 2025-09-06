import logging
from datetime import datetime
from typing import Dict, Any, Union

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import config
from constants.texts import (
    PREMIUM_READING_START, PREMIUM_READING_PAYMENT_SUCCESS,
    PREMIUM_READING_INVALID_DATE, PREMIUM_READING_PREPARING,
    PREMIUM_READING_FINAL_RESULT, CALLBACK_PAY, CALLBACK_BACK
)
from keyboards.inline import get_premium_keyboard, get_start_keyboard, get_after_reading_keyboard
from services.payment_service import PaymentService
from services.openai_service import OpenAIService
from utils.storage import UserStorage, ReadingStorage
from utils.animations import delay
from models.schemas import UserState

# Настройка логирования
logger = logging.getLogger(__name__)

# Создание роутера
router = Router(name="payments")

# Определение состояний FSM для премиум-гадания
class PremiumReadingStates(StatesGroup):
    waiting_for_payment = State()
    waiting_for_birthdate = State()
    generating_reading = State()


# Регистрация обработчиков
def register_payment_handlers(bot: Bot) -> None:
    """Регистрирует обработчики для платежей.
    
    Args:
        bot: Экземпляр бота.
    """
    # Создание сервисов
    payment_service = PaymentService(bot)
    openai_service = OpenAIService()
    
    # Хранилища данных
    user_storage = UserStorage()
    reading_storage = ReadingStorage()
    
    @router.callback_query(F.data == CALLBACK_PAY)
    async def process_payment(callback: CallbackQuery, state: FSMContext) -> None:
        """Обрабатывает запрос на оплату премиум-гадания.
        
        Args:
            callback: Объект callback запроса.
            state: Контекст состояния FSM.
        """
        try:
            # Проверяем, является ли пользователь бесплатным
            user_id = callback.from_user.id
            free_users = config.get_free_users()
            
            if user_id in free_users:
                # Для бесплатных пользователей пропускаем оплату
                await callback.message.edit_text(
                    text=PREMIUM_READING_PAYMENT_SUCCESS,
                    parse_mode="HTML"
                )
                await state.set_state(PremiumReadingStates.waiting_for_birthdate)
                return
            
            # Создаем инвойс для оплаты
            await payment_service.create_premium_reading_invoice(
                chat_id=callback.message.chat.id,
                payload=f"premium_reading_{user_id}_{datetime.now().timestamp()}"
            )
            
            # Устанавливаем состояние ожидания оплаты
            await state.set_state(PremiumReadingStates.waiting_for_payment)
            
            # Отвечаем на callback
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса на оплату: {e}")
            await callback.message.edit_text(
                text="<b>⚠️ Произошла ошибка при создании платежа</b>\n\n"
                     "Пожалуйста, попробуйте позже или обратитесь к администратору.",
                parse_mode="HTML",
                reply_markup=get_start_keyboard()
            )
            await callback.answer()
    
    @router.pre_checkout_query()
    async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
        """Обрабатывает запрос на предварительную проверку платежа.
        
        Args:
            pre_checkout_query: Объект запроса на предварительную проверку.
        """
        try:
            # Обрабатываем предварительную проверку платежа
            await payment_service.process_pre_checkout(pre_checkout_query)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке предварительной проверки платежа: {e}")
            await bot.answer_pre_checkout_query(
                pre_checkout_query_id=pre_checkout_query.id,
                ok=False,
                error_message="Произошла ошибка при обработке платежа. Пожалуйста, попробуйте позже."
            )
    
    @router.message(F.successful_payment)
    async def process_successful_payment(message: Message, state: FSMContext) -> None:
        """Обрабатывает успешный платеж.
        
        Args:
            message: Объект сообщения с информацией о платеже.
            state: Контекст состояния FSM.
        """
        try:
            # Обрабатываем успешный платеж
            await payment_service.process_successful_payment(
                chat_id=message.chat.id,
                successful_payment=message.successful_payment
            )
            
            # Обновляем состояние пользователя
            user_id = message.from_user.id
            user_state = await user_storage.get_user_state(user_id)
            if user_state is None:
                user_state = UserState(user_id=user_id)
            
            user_state.premium_readings_count += 1
            user_state.last_premium_reading_date = datetime.now().isoformat()
            
            await user_storage.save_user_state(user_state)
            
            # Отправляем сообщение с запросом даты рождения
            await message.answer(
                text=PREMIUM_READING_PAYMENT_SUCCESS,
                parse_mode="HTML"
            )
            
            # Устанавливаем состояние ожидания даты рождения
            await state.set_state(PremiumReadingStates.waiting_for_birthdate)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке успешного платежа: {e}")
            await message.answer(
                text="<b>⚠️ Произошла ошибка при обработке платежа</b>\n\n"
                     "Платеж был успешно выполнен, но произошла ошибка при обработке. "
                     "Пожалуйста, обратитесь к администратору.",
                parse_mode="HTML",
                reply_markup=get_start_keyboard()
            )
    
    @router.message(PremiumReadingStates.waiting_for_birthdate)
    async def process_birthdate(message: Message, state: FSMContext) -> None:
        """Обрабатывает ввод даты рождения для премиум-гадания.
        
        Args:
            message: Объект сообщения с датой рождения.
            state: Контекст состояния FSM.
        """
        try:
            # Проверяем формат даты
            birthdate_text = message.text.strip()
            try:
                birthdate = datetime.strptime(birthdate_text, "%d.%m.%Y")
                birthdate_str = birthdate.strftime("%d.%m.%Y")
            except ValueError:
                await message.answer(
                    text=PREMIUM_READING_INVALID_DATE,
                    parse_mode="HTML"
                )
                return
            
            # Сохраняем дату рождения в состоянии
            await state.update_data(birthdate=birthdate_str)
            
            # Отправляем сообщение о подготовке к гаданию
            await message.answer(
                text=PREMIUM_READING_PREPARING,
                parse_mode="HTML"
            )
            
            # Устанавливаем состояние генерации гадания
            await state.set_state(PremiumReadingStates.generating_reading)
            
            # Генерация премиум-гадания
            premium_reading = await openai_service.generate_tarot_reading(birthdate_str)
            
            # Логируем результат для отладки
            logger.info(f"Premium reading result: success={premium_reading.success}, error={premium_reading.error}, has_reading={premium_reading.reading is not None}")
            
            # Сохраняем гадание в хранилище
            user_id = message.from_user.id
            await reading_storage.save_reading({**premium_reading.model_dump(), "user_id": user_id})
            
            # Отправляем результаты гадания
            if premium_reading.success and premium_reading.reading:
                card_numbers = ["1", "2", "3"]
                for i, card in enumerate(premium_reading.reading.cards):
                    position_meaning = {
                        "Прошлое": "Влияния из прошлого, которые всё ещё воздействуют на ситуацию",
                        "Настоящее": "Текущая ситуация и энергии",
                        "Будущее": "Потенциальные возможности и направление развития"
                    }.get(card.position, card.position)
                
                    additional_info = ""
                    if card.position == "Будущее":
                        additional_info = "<i>Помните, что будущее не предопределено и всегда можно изменить его своими действиями.</i>"
                    
                    # Отправляем сообщение с номером карты без кнопок
                    await message.answer(
                        text=f"<b>🔮 {card_numbers[i]} карта - {card.position}: {card.name}</b>\n\n"
                             f"<b>Позиция в раскладе:</b> {position_meaning}\n\n"
                             f"<b>Интерпретация:</b>\n{card.interpretation}\n\n"
                             f"{additional_info}",
                        parse_mode="HTML"
                    )
                    
                    # Добавляем задержку между сообщениями
                    await delay(2)
                
                # Добавляем задержку перед финальным сообщением
                await delay(2)
                
                # Отправляем итоговую интерпретацию и рекомендацию напитка (после всех карт)
                drink_recommendation = (
                    f"<b>{premium_reading.reading.drink.name}</b>\n"
                    f"{premium_reading.reading.drink.description}\n\n"
                    f"<b>Ингредиенты:</b> {', '.join(premium_reading.reading.drink.ingredients)}\n"
                    f"<b>Приготовление:</b> {premium_reading.reading.drink.preparation}"
                )
                
                await message.answer(
                    text=PREMIUM_READING_FINAL_RESULT.format(
                        overall_interpretation=premium_reading.reading.overall_interpretation,
                        drink_recommendation=drink_recommendation,
                        advice=premium_reading.reading.advice
                    ),
                    parse_mode="HTML",
                    reply_markup=get_after_reading_keyboard()
                )
            else:
                # Если гадание не удалось сгенерировать
                await message.answer(
                    text="<b>⚠️ Не удалось сгенерировать гадание</b>\n\n"
                         f"Ошибка: {premium_reading.error or 'Неизвестная ошибка'}\n\n"
                         "Пожалуйста, попробуйте позже или обратитесь к администратору.",
                    parse_mode="HTML",
                    reply_markup=get_start_keyboard()
                )
            
            # Сбрасываем состояние
            await state.clear()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке даты рождения: {e}")
            await message.answer(
                text="<b>⚠️ Произошла ошибка при генерации гадания</b>\n\n"
                     "Пожалуйста, попробуйте позже или обратитесь к администратору.",
                parse_mode="HTML",
                reply_markup=get_start_keyboard()
            )
            await state.clear()
    
    @router.callback_query(PremiumReadingStates.waiting_for_payment, F.data == CALLBACK_BACK)
    @router.callback_query(PremiumReadingStates.waiting_for_birthdate, F.data == CALLBACK_BACK)
    async def cancel_premium_reading(callback: CallbackQuery, state: FSMContext) -> None:
        """Отменяет процесс премиум-гадания.
        
        Args:
            callback: Объект callback запроса.
            state: Контекст состояния FSM.
        """
        try:
            # Сбрасываем состояние
            await state.clear()
            
            # Возвращаемся в главное меню
            await callback.message.edit_text(
                text="<b>🔮 Алко Таро</b>\n\n"
                     "Вы вернулись в главное меню. Выберите действие:",
                parse_mode="HTML",
                reply_markup=get_start_keyboard()
            )
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Ошибка при отмене премиум-гадания: {e}")
            await callback.message.edit_text(
                text="<b>⚠️ Произошла ошибка</b>\n\n"
                     "Пожалуйста, попробуйте позже или обратитесь к администратору.",
                parse_mode="HTML",
                reply_markup=get_start_keyboard()
            )
            await callback.answer()
    
    # Команда для инициирования премиум-гадания
    @router.message(Command("premium"))
    @router.callback_query(F.data == "premium_reading")
    async def start_premium_reading(event: Union[Message, CallbackQuery], state: FSMContext) -> None:
        """Начинает процесс премиум-гадания.
        
        Args:
            event: Объект сообщения или callback запроса.
            state: Контекст состояния FSM.
        """
        try:
            # Формируем текст сообщения
            text = PREMIUM_READING_START.format(
                price=int(config.PREMIUM_READING_PRICE)
            )
            
            # Отправляем сообщение в зависимости от типа события
            if isinstance(event, Message):
                await event.answer(
                    text=text,
                    parse_mode="HTML",
                    reply_markup=get_premium_keyboard()
                )
            else:  # CallbackQuery
                await event.message.edit_text(
                    text=text,
                    parse_mode="HTML",
                    reply_markup=get_premium_keyboard()
                )
                await event.answer()
            
        except Exception as e:
            logger.error(f"Ошибка при начале премиум-гадания: {e}")
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