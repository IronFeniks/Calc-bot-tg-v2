from .router import admin_router
from .categories import (
    show_categories_list,
    add_category_start,
    add_category_parent,
    add_category_save,
    edit_category_select,
    edit_category_name,
    edit_category_save,
    delete_category_confirm,
    delete_category_execute
)
from .products import (
    show_products_list,
    add_product_start,
    save_product_name,
    save_product_category,
    save_product_multiplicity,
    save_product_price,
    edit_product_select,
    edit_product_field,
    save_product_edit,
    delete_product_confirm,
    delete_product_execute,
    search_products
)
from .nodes import (
    show_nodes_list,
    add_node_start,
    save_node_name,
    save_node_category,
    save_node_multiplicity,
    save_node_price,
    edit_node_select,
    edit_node_field,
    save_node_edit,
    delete_node_confirm,
    delete_node_execute,
    search_nodes
)
from .materials import (
    show_materials_list,
    add_material_start,
    save_material_name,
    save_material_category,
    save_material_price,
    edit_material_select,
    edit_material_field,
    save_material_edit,
    delete_material_confirm,
    delete_material_execute,
    search_materials
)
from .specifications import (
    spec_select_parent,
    show_spec_menu,
    link_node_select,
    link_node_quantity,
    link_node_save,
    link_material_select,
    link_material_quantity,
    link_material_save,
    unlink_spec_confirm,
    unlink_spec_execute
)
from .admins import (
    show_admins_list,
    add_admin_start,
    add_admin_save,
    delete_admin_confirm,
    delete_admin_execute,
    toggle_admin_execute
)
from .search import (
    search_start,
    search_execute,
    show_search_results
)

# Импортируем основные функции админки из admin.py (которые были там раньше)
import logging
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from keyboards.admin import main_menu_keyboard, cancel_button
from handlers.auth import is_admin
from handlers.admin.router import admin_router, get_admin_session, clear_admin_session
from states import AdminStates

logger = logging.getLogger(__name__)


async def _send_admin_message(update_obj, text: str, reply_markup=None, parse_mode: str = None):
    """Универсальная функция отправки сообщения в админке"""
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
    """Запуск админки"""
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
    
    if not is_admin(user_id):
        await _send_admin_message(update_obj, "⛔ У вас нет доступа к администрированию.")
        return
    
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
    
    if state == AdminStates.CATEGORY_ADD_NAME:
        await add_category_save(update, user_id, text)
    elif state == AdminStates.CATEGORY_EDIT_NAME:
        await edit_category_save(update, user_id, text)
    elif state == AdminStates.PRODUCT_ADD_NAME:
        await save_product_name(update, user_id, text)
    elif state == AdminStates.PRODUCT_ADD_MULTIPLICITY:
        await save_product_multiplicity(update, user_id, text)
    elif state == AdminStates.PRODUCT_ADD_PRICE:
        await save_product_price(update, user_id, text)
    elif state == AdminStates.PRODUCT_SEARCH:
        await search_execute(update, user_id, text)
    elif state == AdminStates.NODE_ADD_NAME:
        await save_node_name(update, user_id, text)
    elif state == AdminStates.NODE_ADD_MULTIPLICITY:
        await save_node_multiplicity(update, user_id, text)
    elif state == AdminStates.NODE_ADD_PRICE:
        await save_node_price(update, user_id, text)
    elif state == AdminStates.NODE_SEARCH:
        await search_execute(update, user_id, text)
    elif state == AdminStates.MATERIAL_ADD_NAME:
        await save_material_name(update, user_id, text)
    elif state == AdminStates.MATERIAL_ADD_PRICE:
        await save_material_price(update, user_id, text)
    elif state == AdminStates.MATERIAL_SEARCH:
        await search_execute(update, user_id, text)
    elif state == AdminStates.SPEC_LINK_NODE_QUANTITY:
        await link_node_save(update, user_id, text)
    elif state == AdminStates.SPEC_LINK_MATERIAL_QUANTITY:
        await link_material_save(update, user_id, text)
    elif state == AdminStates.ADMIN_ADD_ID:
        await add_admin_save(update, user_id, text)
    elif state == AdminStates.SEARCH_QUERY:
        await search_execute(update, user_id, text)
    else:
        await update.message.reply_text(
            "⚙️ АДМИНИСТРИРОВАНИЕ\n\nГлавное меню:",
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
    
    if data.startswith(f"user_{user_id}_"):
        action = data.replace(f"user_{user_id}_", "")
    else:
        action = data
    
    logger.info(f"🔧 Админ callback: action = {action}")
    
    if action == "cancel":
        clear_admin_session(user_id)
        from handlers.calculator.handlers import start_calculator
        await start_calculator(query, context, is_topic=False, lock=None)
        return
    
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
• Добавление/переименование/удаление

🏗️ ИЗДЕЛИЯ, 🔩 УЗЛЫ, ⚙️ МАТЕРИАЛЫ:
• Просмотр, добавление, редактирование, удаление
• Поиск по названию

🔗 СПЕЦИФИКАЦИИ:
• Привязка узлов и материалов
• Указание количества

👥 АДМИНИСТРАТОРЫ:
• Только для главного админа

🔧 КОМАНДЫ:
/start — калькулятор
/cancel — отмена
/help — справка"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(help_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(help_text, parse_mode='Markdown')


__all__ = [
    'admin_router',
    'start_admin',
    'admin_text_handler',
    'admin_callback_handler',
    'cancel_admin',
    'help_admin',
    # Categories
    'show_categories_list',
    'add_category_start',
    'add_category_parent',
    'add_category_save',
    'edit_category_select',
    'edit_category_name',
    'edit_category_save',
    'delete_category_confirm',
    'delete_category_execute',
    # Products
    'show_products_list',
    'add_product_start',
    'save_product_name',
    'save_product_category',
    'save_product_multiplicity',
    'save_product_price',
    'edit_product_select',
    'edit_product_field',
    'save_product_edit',
    'delete_product_confirm',
    'delete_product_execute',
    'search_products',
    # Nodes
    'show_nodes_list',
    'add_node_start',
    'save_node_name',
    'save_node_category',
    'save_node_multiplicity',
    'save_node_price',
    'edit_node_select',
    'edit_node_field',
    'save_node_edit',
    'delete_node_confirm',
    'delete_node_execute',
    'search_nodes',
    # Materials
    'show_materials_list',
    'add_material_start',
    'save_material_name',
    'save_material_category',
    'save_material_price',
    'edit_material_select',
    'edit_material_field',
    'save_material_edit',
    'delete_material_confirm',
    'delete_material_execute',
    'search_materials',
    # Specifications
    'spec_select_parent',
    'show_spec_menu',
    'link_node_select',
    'link_node_quantity',
    'link_node_save',
    'link_material_select',
    'link_material_quantity',
    'link_material_save',
    'unlink_spec_confirm',
    'unlink_spec_execute',
    # Admins
    'show_admins_list',
    'add_admin_start',
    'add_admin_save',
    'delete_admin_confirm',
    'delete_admin_execute',
    'toggle_admin_execute',
    # Search
    'search_start',
    'search_execute',
    'show_search_results'
]
