import logging
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from keyboards.admin import main_menu_keyboard, cancel_button
from handlers.auth import is_admin
from handlers.admin.router import admin_router, get_admin_session, clear_admin_session
from states import AdminStates

logger = logging.getLogger(__name__)


async def _send_admin_message(update_obj, text: str, reply_markup=None, parse_mode: str = None):
    """
    Универсальная функция отправки сообщения в админке
    Поддерживает Update, CallbackQuery и Message
    """
    if isinstance(update_obj, Update):
        if update_obj.callback_query:
            await update_obj.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        elif update_obj.message:
            await update_obj.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            logger.error(f"Update не содержит message или callback_query")
    elif isinstance(update_obj, CallbackQuery):
        await update_obj.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    elif hasattr(update_obj, 'reply_text'):
        await update_obj.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    else:
        logger.error(f"Не удалось отправить сообщение в админке: неизвестный тип {type(update_obj)}")


async def start_admin(update_obj, context: ContextTypes.DEFAULT_TYPE):
    """Запуск админки (работает как из сообщения, так и из callback)"""
    # Определяем user_id в зависимости от типа объекта
    if isinstance(update_obj, Update):
        if update_obj.callback_query:
            user_id = update_obj.callback_query.from_user.id
            query = update_obj.callback_query
        else:
            user_id = update_obj.effective_user.id
            query = None
    elif isinstance(update_obj, CallbackQuery):
        user_id = update_obj.from_user.id
        query = update_obj
    else:
        user_id = update_obj.effective_user.id
        query = None
    
    # Проверяем права
    if not is_admin(user_id):
        await _send_admin_message(update_obj, "⛔ У вас нет доступа к администрированию.")
        return
    
    # Очищаем предыдущую сессию
    clear_admin_session(user_id)
    
    text = "⚙️ АДМИНИСТРИРОВАНИЕ\n\nГлавное меню:"
    reply_markup = main_menu_keyboard(user_id)
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await _send_admin_message(update_obj, text, reply_markup=reply_markup)


async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений в админке"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет доступа.")
        return
    
    session = get_admin_session(user_id)
    state = session.get('state', AdminStates.MAIN_MENU)
    
    logger.info(f"📝 Админ-текст от {user_id}: '{text}', состояние={state}")
    
    # Обработка в зависимости от состояния
    if state == AdminStates.CATEGORY_ADD_NAME:
        from handlers.admin.categories import add_category_save
        await add_category_save(update, user_id, text)
        return
    
    elif state == AdminStates.CATEGORY_EDIT_NAME:
        from handlers.admin.categories import edit_category_save
        await edit_category_save(update, user_id, text)
        return
    
    elif state == AdminStates.PRODUCT_ADD_NAME:
        from handlers.admin.products import save_product_name
        await save_product_name(update, user_id, text)
        return
    
    elif state == AdminStates.PRODUCT_ADD_MULTIPLICITY:
        from handlers.admin.products import save_product_multiplicity
        await save_product_multiplicity(update, user_id, text)
        return
    
    elif state == AdminStates.PRODUCT_ADD_PRICE:
        from handlers.admin.products import save_product_price
        await save_product_price(update, user_id, text)
        return
    
    elif state == AdminStates.PRODUCT_EDIT_NAME:
        from handlers.admin.products import save_product_edit_value
        await save_product_edit_value(update, user_id, text)
        return
    
    elif state == AdminStates.PRODUCT_EDIT_MULTIPLICITY:
        from handlers.admin.products import save_product_edit_value
        await save_product_edit_value(update, user_id, text)
        return
    
    elif state == AdminStates.PRODUCT_EDIT_PRICE:
        from handlers.admin.products import save_product_edit_value
        await save_product_edit_value(update, user_id, text)
        return
    
    elif state == AdminStates.PRODUCT_SEARCH:
        from handlers.admin.search import search_execute
        await search_execute(update, user_id, text)
        return
    
    elif state == AdminStates.NODE_ADD_NAME:
        from handlers.admin.nodes import save_node_name
        await save_node_name(update, user_id, text)
        return
    
    elif state == AdminStates.NODE_ADD_MULTIPLICITY:
        from handlers.admin.nodes import save_node_multiplicity
        await save_node_multiplicity(update, user_id, text)
        return
    
    elif state == AdminStates.NODE_ADD_PRICE:
        from handlers.admin.nodes import save_node_price
        await save_node_price(update, user_id, text)
        return
    
    elif state == AdminStates.NODE_EDIT_NAME:
        from handlers.admin.nodes import save_node_edit_value
        await save_node_edit_value(update, user_id, text)
        return
    
    elif state == AdminStates.NODE_EDIT_MULTIPLICITY:
        from handlers.admin.nodes import save_node_edit_value
        await save_node_edit_value(update, user_id, text)
        return
    
    elif state == AdminStates.NODE_EDIT_PRICE:
        from handlers.admin.nodes import save_node_edit_value
        await save_node_edit_value(update, user_id, text)
        return
    
    elif state == AdminStates.NODE_SEARCH:
        from handlers.admin.search import search_execute
        await search_execute(update, user_id, text)
        return
    
    elif state == AdminStates.MATERIAL_ADD_NAME:
        from handlers.admin.materials import save_material_name
        await save_material_name(update, user_id, text)
        return
    
    elif state == AdminStates.MATERIAL_ADD_PRICE:
        from handlers.admin.materials import save_material_price
        await save_material_price(update, user_id, text)
        return
    
    elif state == AdminStates.MATERIAL_EDIT_NAME:
        from handlers.admin.materials import save_material_edit_value
        await save_material_edit_value(update, user_id, text)
        return
    
    elif state == AdminStates.MATERIAL_EDIT_PRICE:
        from handlers.admin.materials import save_material_edit_value
        await save_material_edit_value(update, user_id, text)
        return
    
    elif state == AdminStates.MATERIAL_SEARCH:
        from handlers.admin.search import search_execute
        await search_execute(update, user_id, text)
        return
    
    elif state == AdminStates.SPEC_LINK_NODE_QUANTITY:
        from handlers.admin.specifications import link_node_save
        await link_node_save(update, user_id, text)
        return
    
    elif state == AdminStates.SPEC_LINK_MATERIAL_QUANTITY:
        from handlers.admin.specifications import link_material_save
        await link_material_save(update, user_id, text)
        return
    
    elif state == AdminStates.ADMIN_ADD_ID:
        from handlers.admin.admins import add_admin_save
        await add_admin_save(update, user_id, text)
        return
    
    elif state == AdminStates.SEARCH_QUERY:
        from handlers.admin.search import search_execute
        await search_execute(update, user_id, text)
        return
    
    else:
        # По умолчанию - показать главное меню
        await update.message.reply_text(
            "⚙️ АДМИНИСТРИРОВАНИЕ\n\n"
            "Главное меню:",
            reply_markup=main_menu_keyboard(user_id)
        )


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback кнопок в админке"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("⛔ У вас нет доступа", show_alert=True)
        return
    
    # Извлекаем действие
    if data.startswith(f"user_{user_id}_"):
        action = data.replace(f"user_{user_id}_", "")
    else:
        action = data
    
    logger.info(f"🔧 Админ callback: action = {action}")
    
    # Обработка отмены
    if action == "cancel":
        clear_admin_session(user_id)
        from handlers.calculator.handlers import start_calculator
        await start_calculator(query, context, is_topic=False, lock=None)
        return
    
    # Передаём в роутер
    await admin_router(query, user_id, action, context)


async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена в админке"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет доступа.")
        return
    
    clear_admin_session(user_id)
    
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
• Просмотр дерева категорий
• Добавление категорий (выбор родителя)
• Переименование категорий
• Удаление пустых категорий

🏗️ ИЗДЕЛИЯ:
• Просмотр списка с пагинацией
• Добавление (название, категория, кратность, цена)
• Редактирование всех полей
• Удаление (каскадно удаляет спецификации)
• Поиск по названию

🔩 УЗЛЫ:
• Аналогично изделиям

⚙️ МАТЕРИАЛЫ:
• Аналогично, но без кратности

🔗 СПЕЦИФИКАЦИИ:
• Привязка узлов к изделиям
• Привязка материалов к изделиям и узлам
• Указание количества
• Удаление связей

👥 АДМИНИСТРАТОРЫ:
• Только для главного админа
• Добавление/удаление/активация

🔍 ПОИСК:
• Поиск по всей номенклатуре
• Поиск по названию или коду

🔧 КОМАНДЫ:
/start — вернуться в калькулятор
/cancel — отмена текущего действия
/help — эта справка

❗ ВАЖНО:
• Все изменения сохраняются в Excel автоматически
• Удаление элемента удаляет все связанные спецификации"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(help_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(help_text, parse_mode='Markdown')
