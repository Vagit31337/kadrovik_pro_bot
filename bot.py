import logging
from config import BOT_TOKEN
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    CallbackContext,
    ConversationHandler,
    filters
)
from handlers import catalog, cart, payments, admin

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Главное меню
async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    text = (
        f"👋 Привет, {user.first_name}!\n"
        "Я помогу приобрести бланки приказов. Используй кнопки ниже:"
    )
    buttons = [
        [InlineKeyboardButton("📁 Каталог", callback_data="catalog")],
        [InlineKeyboardButton("🛒 Корзина", callback_data="view_cart")]
    ]
    
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

def main() -> None:
    # Используем токен из конфига
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin.admin_start))
    
    # Обработчики callback
    application.add_handler(CallbackQueryHandler(start, pattern="main_menu"))
    application.add_handler(CallbackQueryHandler(catalog.show_categories, pattern="catalog"))
    application.add_handler(CallbackQueryHandler(catalog.show_items, pattern="category_"))
    application.add_handler(CallbackQueryHandler(catalog.item_details, pattern="item_"))
    
    application.add_handler(CallbackQueryHandler(cart.view_cart, pattern="view_cart"))
    application.add_handler(CallbackQueryHandler(cart.add_to_cart, pattern="add_"))
    application.add_handler(CallbackQueryHandler(cart.clear_cart, pattern="clear_cart"))
    
    application.add_handler(CallbackQueryHandler(payments.checkout, pattern="checkout"))
    application.add_handler(CallbackQueryHandler(payments.confirm_payment, pattern="confirm_payment"))
    
    # Обработка чеков
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.ALL,
        payments.handle_receipt
    ))
    
    # Админ-панель
    application.add_handler(CallbackQueryHandler(admin.admin_add_product_start, pattern="admin_add_product"))
    application.add_handler(CallbackQueryHandler(admin.admin_remove_product, pattern="admin_remove_product"))
    application.add_handler(CallbackQueryHandler(admin.admin_view_orders, pattern="admin_view_orders"))
    application.add_handler(CallbackQueryHandler(admin.admin_confirm_remove, pattern="remove_"))
    application.add_handler(CallbackQueryHandler(admin.cancel, pattern="cancel|admin_back"))
    
    # ConversationHandler для добавления товара
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.admin_add_product_start, pattern="admin_add_product")],
        states={
            admin.CATEGORY: [
                CallbackQueryHandler(admin.admin_add_product_category),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin.admin_add_product_name)
            ],
            admin.NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin.admin_add_product_price)
            ],
            admin.PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin.admin_add_product_file)
            ],
            admin.FILE: [
                MessageHandler(filters.Document.ALL, admin.admin_add_product_file)
            ]
        },
        fallbacks=[CommandHandler('cancel', admin.cancel)],
        allow_reentry=True
    )
    application.add_handler(conv_handler)

    # Запуск бота
    logger.info("Бот запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()