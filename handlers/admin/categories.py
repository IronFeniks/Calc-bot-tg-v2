import logging
from telegram import CallbackQuery
from keyboards.admin import (
    categories_list_keyboard, category_add_parent_keyboard,
    category_edit_select_keyboard, category_delete_select_keyboard,
    back_to_main_button
)
from excel_handler import get_excel_handler

logger = logging.getLogger(__name__)


async def show_categories_list(query: CallbackQuery, user_id: int):
    """Показывает список категорий"""
    excel = get_excel_handler()
    tree = excel.get_category_tree()
    
    text = "📋 КАТЕГОРИИ\n\n"
    
    if not tree:
        text += "Нет категорий.\n\n"
        text += "Используйте кнопку «➕ Добавить» чтобы создать категорию."
    else:
        text += _format_category_tree(tree)
    
    await query.edit_message_text(
        text,
        reply_markup=categories_list_keyboard(user_id)
    )


def _format_category_tree(tree: dict, indent: int = 0) -> str:
    """Форматирует дерево категорий для отображения"""
    lines = []
    prefix = "  " * indent
    
    for cat, data in sorted(tree.items()):
        items_count = len(data.get('_items', []))
        subcats_count = len(data.get('_subcategories', {}))
        
        line = f"{prefix}📁 {cat}"
        if items_count > 0:
            line += f" ({items_count} шт.)"
        lines.append(line)
        
        if data.get('_subcategories'):
            lines.append(_format_category_tree(data['_subcategories'], indent + 1))
    
    return "\n".join(lines)


async def add_category_start(query: CallbackQuery, user_id: int):
    """Начинает добавление категории - выбор родителя"""
    excel = get_excel_handler()
    paths = excel.get_category_paths()
    
    text = "📋 ДОБАВЛЕНИЕ КАТЕГОРИИ\n\n"
    text += "Выберите родительскую категорию или «Корень»:\n"
    text += "(категория будет создана как подкатегория выбранной)"
    
    await query.edit_message_text(
        text,
        reply_markup=category_add_parent_keyboard(user_id, paths)
    )


async def add_category_parent(query: CallbackQuery, user_id: int, parent: str):
    """Запрашивает название новой категории"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.CATEGORY_ADD_NAME
    session['data'] = {'parent': parent if parent != 'root' else ''}
    
    if parent == 'root':
        parent_text = "корне"
    else:
        parent_text = f"категории '{parent}'"
    
    await query.edit_message_text(
        f"📋 ДОБАВЛЕНИЕ КАТЕГОРИИ\n\n"
        f"Родитель: {parent_text}\n\n"
        f"Введите название новой категории:\n"
        f"(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )


async def add_category_save(update, user_id: int, name: str):
    """Сохраняет новую категорию"""
    from .router import get_admin_session, clear_admin_session
    from keyboards.admin import main_menu_keyboard
    
    session = get_admin_session(user_id)
    parent = session.get('data', {}).get('parent', '')
    
    if parent:
        full_path = f"{parent} > {name}"
    else:
        full_path = name
    
    excel = get_excel_handler()
    success, message = excel.add_category(full_path)
    
    if success:
        clear_admin_session(user_id)
        await update.message.reply_text(
            f"✅ Категория '{full_path}' добавлена.\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        await update.message.reply_text(
            f"{message}\n\nПопробуйте снова или нажмите Отмена.",
            reply_markup=back_to_main_button(user_id)
        )


async def edit_category_select(query: CallbackQuery, user_id: int):
    """Показывает список категорий для редактирования"""
    excel = get_excel_handler()
    paths = excel.get_category_paths()
    
    if not paths:
        await query.answer("❌ Нет категорий для редактирования", show_alert=True)
        return
    
    text = "✏️ РЕДАКТИРОВАНИЕ КАТЕГОРИИ\n\n"
    text += "Выберите категорию для переименования:"
    
    await query.edit_message_text(
        text,
        reply_markup=category_edit_select_keyboard(user_id, paths)
    )


async def edit_category_name(query: CallbackQuery, user_id: int, old_path: str):
    """Запрашивает новое название для категории"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.CATEGORY_EDIT_NAME
    session['data'] = {'old_path': old_path}
    
    # Получаем последнюю часть пути (имя категории)
    parts = old_path.split(" > ")
    old_name = parts[-1]
    parent = " > ".join(parts[:-1]) if len(parts) > 1 else ""
    
    await query.edit_message_text(
        f"✏️ РЕДАКТИРОВАНИЕ КАТЕГОРИИ\n\n"
        f"Текущий путь: {old_path}\n\n"
        f"Введите новое название для категории '{old_name}':\n"
        f"(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )


async def edit_category_save(update, user_id: int, new_name: str):
    """Сохраняет переименованную категорию"""
    from .router import get_admin_session, clear_admin_session
    from keyboards.admin import main_menu_keyboard
    
    session = get_admin_session(user_id)
    old_path = session.get('data', {}).get('old_path', '')
    
    parts = old_path.split(" > ")
    parent = " > ".join(parts[:-1]) if len(parts) > 1 else ""
    
    if parent:
        new_path = f"{parent} > {new_name}"
    else:
        new_path = new_name
    
    excel = get_excel_handler()
    success, message = excel.rename_category(old_path, new_path)
    
    if success:
        clear_admin_session(user_id)
        await update.message.reply_text(
            f"✅ {message}\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        await update.message.reply_text(
            f"{message}\n\nПопробуйте снова или нажмите Отмена.",
            reply_markup=back_to_main_button(user_id)
        )


async def delete_category_confirm(query: CallbackQuery, user_id: int):
    """Показывает список категорий для удаления"""
    excel = get_excel_handler()
    paths = excel.get_category_paths()
    
    if not paths:
        await query.answer("❌ Нет категорий для удаления", show_alert=True)
        return
    
    text = "🗑️ УДАЛЕНИЕ КАТЕГОРИИ\n\n"
    text += "Выберите категорию для удаления:\n"
    text += "⚠️ Удалить можно только пустую категорию!"
    
    await query.edit_message_text(
        text,
        reply_markup=category_delete_select_keyboard(user_id, paths)
    )


async def delete_category_execute(query: CallbackQuery, user_id: int, category_path: str):
    """Удаляет категорию"""
    from keyboards.admin import main_menu_keyboard
    
    excel = get_excel_handler()
    
    if not excel.is_category_empty(category_path):
        await query.answer("❌ Категория не пуста! Сначала удалите все элементы и подкатегории.", show_alert=True)
        return
    
    success, message = excel.delete_category(category_path)
    
    if success:
        await query.edit_message_text(
            f"✅ Категория '{category_path}' удалена.\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        await query.edit_message_text(
            f"{message}\n\nПопробуйте снова.",
            reply_markup=back_to_main_button(user_id)
        )
