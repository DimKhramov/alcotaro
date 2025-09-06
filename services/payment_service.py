import logging
from typing import Optional, Dict, Any, List, Union

from aiogram import Bot
from aiogram.types import LabeledPrice, PreCheckoutQuery, SuccessfulPayment

from config import config

# Настройка логирования
logger = logging.getLogger(__name__)


class PaymentService:
    """Сервис для работы с платежами через Telegram Bot API."""
    
    def __init__(self, bot: Bot):
        """Инициализация сервиса.
        
        Args:
            bot: Экземпляр бота Telegram.
        """
        self.bot = bot
        # Для Telegram Stars не нужен provider_token
        self.provider_token = ""  # Пустая строка для Telegram Stars
        self.currency = "XTR"  # Telegram Stars
    
    async def create_invoice(
        self,
        chat_id: int,
        title: str,
        description: str,
        payload: str,
        prices: List[LabeledPrice],
        photo_url: Optional[str] = None,
        need_name: bool = False,
        need_phone_number: bool = False,
        need_email: bool = False,
        need_shipping_address: bool = False,
        is_flexible: bool = False,
        disable_notification: bool = False,
        protect_content: bool = True,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: bool = True,
        max_tip_amount: Optional[int] = None,
        suggested_tip_amounts: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Создает инвойс для оплаты.
        
        Args:
            chat_id: ID чата.
            title: Название товара.
            description: Описание товара.
            payload: Полезная нагрузка (идентификатор платежа).
            prices: Список цен.
            photo_url: URL фотографии товара (опционально).
            need_name: Требуется ли имя пользователя.
            need_phone_number: Требуется ли номер телефона.
            need_email: Требуется ли email.
            need_shipping_address: Требуется ли адрес доставки.
            is_flexible: Гибкая ли цена.
            disable_notification: Отключить уведомление.
            protect_content: Защитить контент.
            reply_to_message_id: ID сообщения для ответа.
            allow_sending_without_reply: Разрешить отправку без ответа.
            max_tip_amount: Максимальная сумма чаевых.
            suggested_tip_amounts: Предлагаемые суммы чаевых.
            
        Returns:
            Объект инвойса.
            
        Raises:
            Exception: Если не удалось создать инвойс.
        """
        try:
            return await self.bot.send_invoice(
                chat_id=chat_id,
                title=title,
                description=description,
                payload=payload,
                provider_token=self.provider_token,
                currency=self.currency,
                prices=prices,
                photo_url=photo_url,
                need_name=need_name,
                need_phone_number=need_phone_number,
                need_email=need_email,
                need_shipping_address=need_shipping_address,
                is_flexible=is_flexible,
                disable_notification=disable_notification,
                protect_content=protect_content,
                reply_to_message_id=reply_to_message_id,
                allow_sending_without_reply=allow_sending_without_reply,
                max_tip_amount=max_tip_amount,
                suggested_tip_amounts=suggested_tip_amounts,
            )
        except Exception as e:
            logger.error(f"Ошибка при создании инвойса: {e}")
            raise
    
    async def create_premium_reading_invoice(
        self, chat_id: int, payload: str = "premium_reading"
    ) -> Dict[str, Any]:
        """Создает инвойс для оплаты премиум-гадания через Telegram Stars.
        
        Args:
            chat_id: ID чата.
            payload: Полезная нагрузка (идентификатор платежа).
            
        Returns:
            Объект инвойса.
        """
        title = "Премиум-гадание на картах Таро"
        description = "Полный расклад карт Таро с детальной интерпретацией и рекомендациями по алкоголю"
        # Для Telegram Stars цена указывается напрямую (без умножения на 100)
        price = int(config.PREMIUM_READING_PRICE)
        
        return await self.create_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            prices=[LabeledPrice(label=title, amount=price)],
            photo_url="https://example.com/tarot_premium.jpg",  # Замените на реальный URL
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False,
        )
    
    async def process_pre_checkout(self, pre_checkout_query: PreCheckoutQuery) -> bool:
        """Обрабатывает запрос на предварительную проверку платежа.
        
        Args:
            pre_checkout_query: Объект запроса на предварительную проверку.
            
        Returns:
            True, если проверка прошла успешно, иначе False.
        """
        try:
            # Здесь можно добавить дополнительную логику проверки
            # Например, проверку наличия товара, валидацию данных и т.д.
            
            # Подтверждаем предварительную проверку
            await self.bot.answer_pre_checkout_query(
                pre_checkout_query_id=pre_checkout_query.id,
                ok=True
            )
            
            logger.info(
                f"Предварительная проверка платежа успешна: "
                f"user_id={pre_checkout_query.from_user.id}, "
                f"payload={pre_checkout_query.invoice_payload}, "
                f"amount={pre_checkout_query.total_amount / 100} {pre_checkout_query.currency}"
            )
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при обработке предварительной проверки платежа: {e}")
            
            # Отклоняем предварительную проверку с сообщением об ошибке
            try:
                await self.bot.answer_pre_checkout_query(
                    pre_checkout_query_id=pre_checkout_query.id,
                    ok=False,
                    error_message="Произошла ошибка при обработке платежа. Пожалуйста, попробуйте позже."
                )
            except Exception as inner_e:
                logger.error(f"Ошибка при отклонении предварительной проверки: {inner_e}")
            
            return False
    
    async def process_successful_payment(
        self, chat_id: int, successful_payment: SuccessfulPayment
    ) -> bool:
        """Обрабатывает успешный платеж.
        
        Args:
            chat_id: ID чата.
            successful_payment: Объект успешного платежа.
            
        Returns:
            True, если обработка прошла успешно, иначе False.
        """
        try:
            # Логируем информацию о платеже
            logger.info(
                f"Успешный платеж: "
                f"payload={successful_payment.invoice_payload}, "
                f"amount={successful_payment.total_amount / 100} {successful_payment.currency}"
            )
            
            # Здесь можно добавить дополнительную логику обработки платежа
            # Например, сохранение информации о платеже в базу данных,
            # активацию премиум-функций для пользователя и т.д.
            
            # Отправляем сообщение о успешной оплате
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"<b>✅ Оплата успешно выполнена!</b>\n\n"
                     f"Сумма: {successful_payment.total_amount / 100} {successful_payment.currency}\n"
                     f"Спасибо за покупку! Теперь вы можете воспользоваться премиум-гаданием.",
                parse_mode="HTML"
            )
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при обработке успешного платежа: {e}")
            return False