import logging
from telegram import Update
from telegram.ext import ContextTypes
from keyboards.admin import main_menu_keyboard

logger = logging.getLogger(__name__)

async def start_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск админки"""
    user_id = update.effective_user.id
    
    await update.message.reply_text(
        "⚙️ АДМИНИСТРИРОВАНИЕ\n\n"
        "Главное меню:",
        reply_markup=main_menu_keyboard(user_id)
    )

async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений в админке"""
    # TODO: реализация
    pass

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback кнопок в админке"""
    # TODO: реализация
    pass

async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена в админке"""
    user_id = update.effective_user.id
    await update.message.reply_text(
        "❌ Действие отменено",
        reply_markup=main_menu_keyboard(user_id)
    )

async def help_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по админке"""
    await update.message.reply_text(
        "📖 ПОМОЩЬ ПО АДМИНИСТРИРОВАНИЮ\n\n"
        "В разработке...",
        parse_mode='Markdown'
    )
