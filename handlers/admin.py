import logging
from telegram import Update
from telegram.ext import ContextTypes
from keyboards.admin import main_menu_keyboard, cancel_button
from handlers.auth import is_admin

logger = logging.getLogger(__name__)


async def start_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск админки"""
    user_id = update.effective_user.id
    
    # Проверяем права
    if not is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет доступа к администрированию.")
        return
    
    await update.message.reply_text(
        "⚙️ АДМИНИСТРИРОВАНИЕ\n\n"
        "Главное меню:",
        reply_markup=main_menu_keyboard(user_id)
    )


async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений в админке"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет доступа.")
        return
    
    # TODO: реализация админки
    await update.message.reply_text(
        "⚙️ Режим администрирования в разработке.\n\n"
        "Доступные команды:\n"
        "/cancel — отмена\n"
        "/help — справка\n"
        "/start — вернуться в калькулятор",
        reply_markup=cancel_button(user_id)
    )


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback кнопок в админке"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if not is_admin(user_id):
        await query.answer("⛔ У вас нет доступа", show_alert=True)
        return
    
    # TODO: реализация админки
    await query.edit_message_text(
        "⚙️ Режим администрирования в разработке.\n\n"
        "Функции будут добавлены позже.",
        reply_markup=cancel_button(user_id)
    )


async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена в админке"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет доступа.")
        return
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "❌ Действие отменено",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        await update.message.reply_text(
            "❌ Действие отменено",
            reply_markup=main_menu_keyboard(user_id)
        )


async def help_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по админке"""
    help_text = """📖 ПОМОЩЬ ПО АДМИНИСТРИРОВАНИЮ

📋 КАТЕГОРИИ:
• Просмотр, добавление категорий

🏗️ ИЗДЕЛИЯ:
• Просмотр, добавление, редактирование, удаление изделий
• Управление составом (привязка узлов и материалов)

🔩 УЗЛЫ:
• Просмотр, добавление, редактирование, удаление узлов

⚙️ МАТЕРИАЛЫ:
• Просмотр, добавление, редактирование, удаление материалов

👥 АДМИНИСТРАТОРЫ:
• Добавление/удаление администраторов (только для главного админа)

🔧 КОМАНДЫ:
/start — вернуться в калькулятор
/cancel — отмена текущего действия
/help — эта справка

❗ ВАЖНО:
• Все изменения сохраняются в Excel файл автоматически
• Удаление элемента удаляет все связанные спецификации"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(help_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(help_text, parse_mode='Markdown')
