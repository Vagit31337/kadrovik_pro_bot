import json
import logging
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, filters
from config import ADMIN_ID

logger = logging.getLogger(__name__)


# Состояния для добавления товара
CATEGORY, NAME, PRICE, FILE = range(4)

async def admin_start(update: Update, context: CallbackContext) -> None:
    from config import ADMIN_ID
    
    # Проверяем, что команду вызвал администратор
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещен!")
        
        # Логируем попытку доступа
        logger.warning(
            f"Попытка доступа к админ-панели: "
            f"ID={update.effective_user.id}, "
            f"Username=@{update.effective_user.username}"
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add_product")],
        [InlineKeyboardButton("🗑️ Удалить товар", callback_data="admin_remove_product")],
        [InlineKeyboardButton("📝 Список заказов", callback_data="admin_view_orders")]
    ]
    
    await update.message.reply_text(
        "👑 Админ-панель:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_add_product_start(update: Update, context: CallbackContext) -> int:
    if update.callback_query.from_user.id != ADMIN_ID:
        await update.callback_query.answer("❌ Доступ запрещен!")
        return ConversationHandler.END
    
    # Загружаем текущие категории
    with open('data/products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    # Создаем клавиатуру с категориями
    buttons = []
    for category in products["categories"]:
        buttons.append([InlineKeyboardButton(category["name"], callback_data=f"cat_{category['id']}")])
    
    buttons.append([InlineKeyboardButton("➕ Новая категория", callback_data="new_category")])
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    
    await update.callback_query.edit_message_text(
        "📁 Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(buttons))
    
    return CATEGORY

async def admin_add_product_category(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "new_category":
        await query.edit_message_text("📝 Введите название новой категории:")
        context.user_data['new_category'] = True
        return CATEGORY
    
    # Сохраняем выбранную категорию
    category_id = data.split('_')[1]
    context.user_data['category_id'] = category_id
    context.user_data['new_category'] = False
    
    await query.edit_message_text("📝 Введите название товара:")
    return NAME

async def admin_add_product_name(update: Update, context: CallbackContext) -> int:
    # Если это ввод новой категории
    if context.user_data.get('new_category'):
        category_name = update.message.text
        
        # Генерируем ID для новой категории
        new_category_id = f"cat_{uuid.uuid4().hex[:8]}"
        
        # Добавляем категорию в products.json
        with open('data/products.json', 'r+', encoding='utf-8') as f:
            products = json.load(f)
            products["categories"].append({
                "id": new_category_id,
                "name": category_name,
                "items": []
            })
            f.seek(0)
            json.dump(products, f, indent=2, ensure_ascii=False)
            f.truncate()
        
        context.user_data['category_id'] = new_category_id
        context.user_data['new_category'] = False
        await update.message.reply_text(f"✅ Категория '{category_name}' создана! Теперь введите название товара:")
        return NAME
    
    # Если название товара
    context.user_data['name'] = update.message.text
    await update.message.reply_text("💰 Введите цену товара (только число):")
    return PRICE

async def admin_add_product_price(update: Update, context: CallbackContext) -> int:
    try:
        price = int(update.message.text)
        context.user_data['price'] = price
        await update.message.reply_text("📎 Теперь загрузите файл товара (документ):")
        return FILE
    except ValueError:
        await update.message.reply_text("❌ Цена должна быть числом! Попробуйте снова:")
        return PRICE

async def admin_add_product_file(update: Update, context: CallbackContext) -> int:
    if not update.message.document:
        await update.message.reply_text("❌ Пожалуйста, загрузите файл как документ!")
        return FILE
    
    file_id = update.message.document.file_id
    context.user_data['file_id'] = file_id
    
    # Получаем данные из контекста
    category_id = context.user_data['category_id']
    name = context.user_data['name']
    price = context.user_data['price']
    
    # Генерируем ID для товара
    item_id = f"item_{uuid.uuid4().hex[:8]}"
    
    # Добавляем товар в products.json
    with open('data/products.json', 'r+', encoding='utf-8') as f:
        products = json.load(f)
        
        # Находим категорию
        for category in products["categories"]:
            if category["id"] == category_id:
                category["items"].append({
                    "id": item_id,
                    "name": name,
                    "price": price,
                    "file_id": file_id
                })
                break
        
        f.seek(0)
        json.dump(products, f, indent=2, ensure_ascii=False)
        f.truncate()
    
    await update.message.reply_text(f"✅ Товар '{name}' успешно добавлен!")
    return ConversationHandler.END

async def admin_remove_product(update: Update, context: CallbackContext) -> None:
    if update.callback_query.from_user.id != ADMIN_ID:
        await update.callback_query.answer("❌ Доступ запрещен!")
        return
    
    # Загружаем товары
    with open('data/products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    # Создаем клавиатуру с товарами
    buttons = []
    for category in products["categories"]:
        for item in category["items"]:
            buttons.append([
                InlineKeyboardButton(
                    f"❌ {category['name']} - {item['name']}",
                    callback_data=f"remove_{item['id']}"
                )
            ])
    
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
    
    await update.callback_query.edit_message_text(
        "🗑️ Выберите товар для удаления:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def admin_confirm_remove(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    item_id = query.data.split('_')[1]
    
    # Удаляем товар из products.json
    with open('data/products.json', 'r+', encoding='utf-8') as f:
        products = json.load(f)
        
        for category in products["categories"]:
            category["items"] = [item for item in category["items"] if item["id"] != item_id]
        
        f.seek(0)
        json.dump(products, f, indent=2, ensure_ascii=False)
        f.truncate()
    
    await query.edit_message_text("✅ Товар успешно удален!")

async def admin_view_orders(update: Update, context: CallbackContext) -> None:
    if update.callback_query.from_user.id != ADMIN_ID:
        await update.callback_query.answer("❌ Доступ запрещен!")
        return
    
    try:
        with open('data/orders.json', 'r', encoding='utf-8') as f:
            orders = json.load(f)
    except FileNotFoundError:
        await update.callback_query.edit_message_text("📭 Нет активных заказов")
        return
    
    if not orders:
        await update.callback_query.edit_message_text("📭 Нет активных заказов")
        return
    
    text = "📋 Активные заказы:\n\n"
    for user_id, order in orders.items():
        text += f"👤 Пользователь: {order.get('username', 'Unknown')} (ID: {user_id})\n"
        text += f"📅 Дата: {order.get('date', 'N/A')}\n"
        text += f"💎 Сумма: {order.get('total', 0)}₽\n"
        text += f"🔄 Статус: {order.get('status', 'pending')}\n"
        text += "------------------------\n"
    
    await update.callback_query.edit_message_text(text)

async def cancel(update: Update, context: CallbackContext) -> int:
    if update.callback_query:
        await update.callback_query.edit_message_text("❌ Операция отменена")
    else:
        await update.message.reply_text("❌ Операция отменена")
    
    context.user_data.clear()
    return ConversationHandler.END