import json
import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)
# Замените на ваш Telegram ID
ADMIN_ID = 999077284

async def checkout(update: Update, context: CallbackContext) -> None:
    from .cart import get_user_cart
    
    user_id = update.callback_query.from_user.id
    cart = get_user_cart(user_id)
    
    if not cart:
        await update.callback_query.answer("🛒 Ваша корзина пуста!")
        return
    
    total = sum(item["price"] * item["quantity"] for item in cart)
    
    # Реквизиты для оплаты (замените на свои)
    payment_details = (
        "💳 *Реквизиты для оплаты:*\n\n"
        "Сбербанк: `1234 5678 9012 3456`\n"
        "Тинькофф: `9876 5432 1098 7654`\n"
        "QIWI: `+79991234567`\n\n"
        "💠 Обязательно укажите в комментарии:\n"
        f"`ORDER_{user_id}`"
    )
    
    buttons = [
        [InlineKeyboardButton("✅ Я оплатил", callback_data="confirm_payment")],
        [InlineKeyboardButton("🔙 Назад", callback_data="view_cart")]
    ]
    
    await update.callback_query.edit_message_text(
        f"✅ Заказ оформлен!\nСумма к оплате: *{total}₽*\n\n{payment_details}",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

async def confirm_payment(update: Update, context: CallbackContext) -> None:
    await update.callback_query.edit_message_text(
        "📎 Пожалуйста, загрузите фото или скан чека об оплате.\n\n"
        "❗ Важно: чек должен содержать:\n"
        "- Реквизиты получателя\n"
        "- Сумму платежа\n"
        "- Дату и время операции"
    )

async def handle_receipt(update: Update, context: CallbackContext) -> None:
    from .cart import get_user_cart, clear_user_cart
    
    user = update.message.from_user
    user_id = user.id
    cart = get_user_cart(user_id)
    
    if not cart:
        await update.message.reply_text("❌ Ваша корзина пуста! Оформите заказ заново.")
        return
    
    # Проверяем тип контента: фото или документ
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    else:
        await update.message.reply_text("❌ Пожалуйста, отправьте фото или документ!")
        return
    
    # Формируем информацию о заказе
    total = sum(item["price"] * item["quantity"] for item in cart)
    order_details = "\n".join(
        f"- {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽"
        for item in cart
    )
    
    # Сохраняем заказ
    order_data = {
        "user_id": user_id,
        "username": user.username or user.full_name,
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "items": cart.copy(),
        "total": total,
        "status": "pending",
        "receipt_file_id": file_id
    }
    
    # Сохраняем в orders.json
    orders = {}
    try:
        with open('data/orders.json', 'r', encoding='utf-8') as f:
            content = f.read()
            if content.strip():
                orders = json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    
    orders[str(user_id)] = order_data
    
    try:
        with open('data/orders.json', 'w', encoding='utf-8') as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения заказа: {e}")
        await update.message.reply_text("❌ Ошибка обработки заказа!")
        return
    
    # Отправляем уведомление админу
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"🚀 НОВЫЙ ЗАКАЗ!\n\n"
            f"👤 Пользователь: @{user.username} ({user.full_name})\n"
            f"🆔 ID: {user_id}\n\n"
            f"📦 Состав заказа:\n{order_details}\n\n"
            f"💎 Итого: {total}₽"
        )
        
        # Пересылаем чек админу
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=file_id,
                caption="Чек об оплате"
            )
        else:
            await context.bot.send_document(
                chat_id=ADMIN_ID,
                document=file_id,
                caption="Чек об оплате"
            )
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления админу: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка при обработке чека. Попробуйте позже.")
        return
    
    # Очищаем корзину и завершаем процесс
    clear_user_cart(user_id)
    await update.message.reply_text(
        "✅ Чек успешно получен! Ваш заказ передан на обработку.\n\n"
        "⌛ Файлы будут отправлены вам в течение 15 минут после проверки платежа."
    )