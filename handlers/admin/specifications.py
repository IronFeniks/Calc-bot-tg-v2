import logging
from telegram import CallbackQuery
from keyboards.admin import (
    spec_parent_select_keyboard, spec_menu_keyboard,
    spec_node_select_keyboard, spec_material_select_keyboard,
    back_to_main_button
)
from excel_handler import get_excel_handler

logger = logging.getLogger(__name__)


async def spec_select_parent(query: CallbackQuery, user_id: int, page: int = 0):
    """Показывает список изделий и узлов для управления спецификациями"""
    excel = get_excel_handler()
    
    # Получаем изделия и узлы
    products, _ = excel.get_products_by_type('изделие', 0, 1000)
    nodes, _ = excel.get_products_by_type('узел', 0, 1000)
    
    all_items = products + nodes
    
    if not all_items:
        await query.answer("❌ Нет изделий или узлов", show_alert=True)
        return
    
    # Пагинация
    items_per_page = 10
    total_pages = (len(all_items) + items_per_page - 1) // items_per_page
    start = page * items_per_page
    end = min(start + items_per_page, len(all_items))
    page_items = all_items[start:end]
    
    text = "🔗 СПЕЦИФИКАЦИИ\n\n"
    text += "Выберите родителя (изделие или узел):\n"
    text += f"Страница {page + 1} из {total_pages}\n\n"
    
    for item in page_items:
        icon = "🏗️" if item['type'] == 'изделие' else "🔩"
        text += f"{icon} {item['name']} ({item['code']})\n"
    
    await query.edit_message_text(
        text,
        reply_markup=spec_parent_select_keyboard(user_id, page_items, page, total_pages)
    )


async def show_spec_menu(query: CallbackQuery, user_id: int, parent_code: str):
    """Показывает меню управления спецификациями для родителя"""
    from .router import get_admin_session
    
    excel = get_excel_handler()
    parent = excel.get_product_by_code(parent_code)
    
    if not parent:
        await query.answer("❌ Родитель не найден", show_alert=True)
        return
    
    session = get_admin_session(user_id)
    session['data'] = {'parent_code': parent_code, 'parent': parent}
    
    # Получаем текущие спецификации
    specs = excel.get_specifications(parent_code)
    
    text = f"🔗 СПЕЦИФИКАЦИИ: {parent['Наименование']}\n"
    text += f"Код: {parent_code}\n"
    text += f"Тип: {parent['Тип']}\n\n"
    
    if specs:
        text += "Текущие связи:\n"
        for spec in specs:
            child = excel.get_product_by_code(spec['child'])
            if child:
                text += f"• {child['Наименование']} ({child['Тип']}) — {spec['quantity']} шт.\n"
    else:
        text += "Нет связанных элементов.\n"
    
    text += "\nВыберите действие:"
    
    await query.edit_message_text(
        text,
        reply_markup=spec_menu_keyboard(user_id, parent_code, parent['Тип'])
    )


async def link_node_select(query: CallbackQuery, user_id: int, parent_code: str, page: int = 0):
    """Показывает список узлов для привязки"""
    excel = get_excel_handler()
    nodes, total = excel.get_products_by_type('узел', page, 10)
    
    if not nodes:
        await query.answer("❌ Нет доступных узлов", show_alert=True)
        return
    
    total_pages = (total + 9) // 10
    
    text = "🔗 ПРИВЯЗКА УЗЛА\n\n"
    text += "Выберите узел для привязки:\n"
    text += f"Страница {page + 1} из {total_pages}"
    
    await query.edit_message_text(
        text,
        reply_markup=spec_node_select_keyboard(user_id, parent_code, nodes, page, total_pages)
    )


async def link_node_quantity(query: CallbackQuery, user_id: int, parent_code: str, node_code: str):
    """Запрашивает количество для привязки узла"""
    from .router import get_admin_session
    from states import AdminStates
    
    excel = get_excel_handler()
    node = excel.get_product_by_code(node_code)
    
    if not node:
        await query.answer("❌ Узел не найден", show_alert=True)
        return
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.SPEC_LINK_NODE_QUANTITY
    session['data']['link_parent'] = parent_code
    session['data']['link_child'] = node_code
    
    await query.edit_message_text(
        f"🔗 ПРИВЯЗКА УЗЛА\n\n"
        f"Узел: {node['Наименование']}\n\n"
        f"Введите количество узлов, необходимое для производства:\n"
        f"(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )


async def link_node_save(update, user_id: int, text: str):
    """Сохраняет привязку узла"""
    from .router import get_admin_session, clear_admin_session
    from keyboards.admin import main_menu_keyboard
    from utils.validators import validate_float
    
    quantity = validate_float(text, min_val=0.01)
    if quantity is None:
        await update.message.reply_text(
            "❌ Введите положительное число.",
            reply_markup=back_to_main_button(user_id)
        )
        return
    
    session = get_admin_session(user_id)
    parent_code = session['data']['link_parent']
    node_code = session['data']['link_child']
    
    excel = get_excel_handler()
    success, message = excel.add_specification(parent_code, node_code, quantity)
    
    clear_admin_session(user_id)
    
    if success:
        await update.message.reply_text(
            f"✅ {message}\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        await update.message.reply_text(
            f"{message}\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )


async def link_material_select(query: CallbackQuery, user_id: int, parent_code: str, page: int = 0):
    """Показывает список материалов для привязки"""
    excel = get_excel_handler()
    materials, total = excel.get_products_by_type('материал', page, 10)
    
    if not materials:
        await query.answer("❌ Нет доступных материалов", show_alert=True)
        return
    
    total_pages = (total + 9) // 10
    
    text = "🔗 ПРИВЯЗКА МАТЕРИАЛА\n\n"
    text += "Выберите материал для привязки:\n"
    text += f"Страница {page + 1} из {total_pages}"
    
    await query.edit_message_text(
        text,
        reply_markup=spec_material_select_keyboard(user_id, parent_code, materials, page, total_pages)
    )


async def link_material_quantity(query: CallbackQuery, user_id: int, parent_code: str, material_code: str):
    """Запрашивает количество для привязки материала"""
    from .router import get_admin_session
    from states import AdminStates
    
    excel = get_excel_handler()
    material = excel.get_product_by_code(material_code)
    
    if not material:
        await query.answer("❌ Материал не найден", show_alert=True)
        return
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.SPEC_LINK_MATERIAL_QUANTITY
    session['data']['link_parent'] = parent_code
    session['data']['link_child'] = material_code
    
    await query.edit_message_text(
        f"🔗 ПРИВЯЗКА МАТЕРИАЛА\n\n"
        f"Материал: {material['Наименование']}\n\n"
        f"Введите количество материала, необходимое для производства:\n"
        f"(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )


async def link_material_save(update, user_id: int, text: str):
    """Сохраняет привязку материала"""
    from .router import get_admin_session, clear_admin_session
    from keyboards.admin import main_menu_keyboard
    from utils.validators import validate_float
    
    quantity = validate_float(text, min_val=0.01)
    if quantity is None:
        await update.message.reply_text(
            "❌ Введите положительное число.",
            reply_markup=back_to_main_button(user_id)
        )
        return
    
    session = get_admin_session(user_id)
    parent_code = session['data']['link_parent']
    material_code = session['data']['link_child']
    
    excel = get_excel_handler()
    success, message = excel.add_specification(parent_code, material_code, quantity)
    
    clear_admin_session(user_id)
    
    if success:
        await update.message.reply_text(
            f"✅ {message}\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        await update.message.reply_text(
            f"{message}\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )


async def unlink_spec_confirm(query: CallbackQuery, user_id: int, parent_code: str, child_code: str):
    """Подтверждает удаление связи"""
    excel = get_excel_handler()
    parent = excel.get_product_by_code(parent_code)
    child = excel.get_product_by_code(child_code)
    
    if not parent or not child:
        await query.answer("❌ Связь не найдена", show_alert=True)
        return
    
    text = f"🗑️ УДАЛЕНИЕ СВЯЗИ\n\n"
    text += f"Родитель: {parent['Наименование']}\n"
    text += f"Потомок: {child['Наименование']}\n\n"
    text += "Вы уверены, что хотите удалить эту связь?"
    
    from keyboards.admin import confirm_delete_keyboard
    await query.edit_message_text(
        text,
        reply_markup=confirm_delete_keyboard(user_id, f"spec_{parent_code}_{child_code}")
    )


async def unlink_spec_execute(query: CallbackQuery, user_id: int, parent_code: str, child_code: str):
    """Удаляет связь"""
    from keyboards.admin import main_menu_keyboard
    
    excel = get_excel_handler()
    success, message = excel.delete_specification(parent_code, child_code)
    
    if success:
        await query.edit_message_text(
            f"✅ Связь удалена.\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        await query.edit_message_text(
            f"{message}\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
