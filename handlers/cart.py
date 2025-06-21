import json
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)
CART_FILE = 'data/carts.json'

def get_user_cart(user_id: int) -> list:
    """Возвращает корзину пользователя, безопасно обрабатывая ошибки"""
    if not os.path.exists(CART_FILE):
        return []
    
    try:
        with open(CART_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
                
            carts = json.loads(content)
            return carts.get(str(user_id), [])
            
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования корзины: {e}")
        return []
    
    except Exception as e:
        logger.error(f"Неизвестная ошибка при чтении корзины: {e}")
        return []

def save_user_cart(user_id: int, cart: list) -> None:
    """Сохраняет корзину пользователя, безопасно обрабатывая ошибки"""
    carts = {}
    
    # Читаем существующие данные
    try:
        if os.path.exists(CART_FILE):
            with open(CART_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    carts = json.loads(content)
    except Exception as e:
        logger.error(f"Ошибка чтения при сохранении корзины: {e}")
    
    # Обновляем корзину пользователя
    carts[str(user_id)] = cart
    
    # Сохраняем обратно
    try:
        with open(CART_FILE, 'w', encoding='utf-8') as f:
            json.dump(carts, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка записи корзины: {e}")

def clear_user_cart(user_id: int) -> None:
    save_user_cart(user_id, [])

async def view_cart(update: Update, context: CallbackContext) -> None:
    user_id = update.callback_query.from_user.id
    cart = get_user_cart(user_id)
    
    logger.info(f"Корзина для пользователя {user_id}: {cart}")
    
    if not cart:
        await update.callback_query.edit_message_text("🛒 Ваша корзина пуста!")
        return
    
    total = sum(item["price"] * item["quantity"] for item in cart)
    text = "🛒 *Ваша корзина:*\n\n"
    for item in cart:
        text += f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽\n"
    text += f"\n💎 Итого: *{total}₽*"
    
    buttons = [
        [InlineKeyboardButton("💳 Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton("🗑️ Очистить корзину", callback_data="clear_cart")],
        [InlineKeyboardButton("📁 Каталог", callback_data="catalog")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ]
    
    await update.callback_query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

async def add_to_cart(update: Update, context: CallbackContext) -> None:
    from .catalog import load_products
    
    query = update.callback_query
    await query.answer()
    item_id = query.data.split("_", 1)[1]
    user_id = query.from_user.id
    
    # Находим товар
    products = load_products()
    item = None
    for category in products.get("categories", []):
        for product in category.get("items", []):
            if product["id"] == item_id:
                item = product.copy()
                break
        if item: 
            break
    
    if not item:
        await query.answer("Товар не найден!")
        return
    
    # Добавляем в корзину
    cart = get_user_cart(user_id)
    found = False
    for i, cart_item in enumerate(cart):
        if cart_item["id"] == item_id:
            cart[i]["quantity"] += 1
            found = True
            break
    
    if not found:
        item["quantity"] = 1
        cart.append(item)
    
    save_user_cart(user_id, cart)
    await query.answer("✅ Товар добавлен в корзину!")

async def clear_cart(update: Update, context: CallbackContext) -> None:
    user_id = update.callback_query.from_user.id
    clear_user_cart(user_id)
    await update.callback_query.answer("Корзина очищена!")
    await view_cart(update, context)