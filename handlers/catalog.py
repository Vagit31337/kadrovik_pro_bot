import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)
PRODUCTS_FILE = 'data/products.json'

def load_products():
    try:
        with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Ошибка загрузки товаров: {e}")
        return {"categories": []}

async def show_categories(update: Update, context: CallbackContext) -> None:
    products = load_products()
    buttons = []
    for category in products["categories"]:
        buttons.append([InlineKeyboardButton(category["name"], callback_data=f"category_{category['id']}")])
    
    # Добавляем кнопку корзины
    buttons.append([InlineKeyboardButton("🛒 Корзина", callback_data="view_cart")])
    buttons.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    
    query = update.callback_query
    await query.edit_message_text(
        "📚 Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_items(update: Update, context: CallbackContext) -> None:
    category_id = update.callback_query.data.split("_", 1)[1]
    products = load_products()
    
    category = next((cat for cat in products["categories"] if cat["id"] == category_id), None)
    if not category:
        await update.callback_query.answer("Категория не найдена!")
        return
    
    buttons = []
    for item in category["items"]:
        buttons.append([InlineKeyboardButton(f"{item['name']} - {item['price']}₽", callback_data=f"item_{item['id']}")])
    
    # Добавляем кнопку корзины
    buttons.append([InlineKeyboardButton("🛒 Корзина", callback_data="view_cart")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="catalog")])
    
    await update.callback_query.edit_message_text(
        f"Товары в категории {category['name']}:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def item_details(update: Update, context: CallbackContext) -> None:
    item_id = update.callback_query.data.split("_", 1)[1]
    products = load_products()
    
    item = None
    category_with_item = None
    for category in products["categories"]:
        for product in category["items"]:
            if product["id"] == item_id:
                item = product
                category_with_item = category
                break
        if item: 
            break
    
    if not item:
        await update.callback_query.answer("Товар не найден!")
        return
    
    text = (
        f"📝 *{item['name']}*\n\n"
        f"Цена: *{item['price']}₽*\n\n"
        "Добавить в корзину?"
    )
    
    buttons = [
        [InlineKeyboardButton("🛒 Добавить в корзину", callback_data=f"add_{item_id}")],
        [InlineKeyboardButton("🛒 Корзина", callback_data="view_cart")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"category_{category_with_item['id']}")]
    ]
    
    await update.callback_query.edit_message_text(
        text, 
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )