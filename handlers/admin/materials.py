import logging
from telegram import CallbackQuery
from keyboards.admin import (
    materials_list_keyboard, material_edit_select_keyboard,
    material_edit_field_keyboard, material_category_select_keyboard,
    material_delete_select_keyboard, back_to_main_button
)
from excel_handler import get_excel_handler
from utils.formatters import format_price

logger = logging.getLogger(__name__)


async def show_materials_list(query: CallbackQuery, user_id: int, page: int = 0):
    """Показывает список материалов с пагинацией"""
    excel = get_excel_handler()
    items, total = excel.get_products_by_type('материал', page, 10)
    
    if not items:
        text = "⚙️ МАТЕРИАЛЫ\n\nНет материалов.\n\nИспользуйте «➕ Добавить» чтобы создать материал."
        await query.edit_message_text(
            text,
            reply_markup=materials_list_keyboard(user_id, [], page, 0)
        )
        return
    
    total_pages = (total + 9) // 10
    
    text = f"⚙️ МАТЕРИАЛЫ\n\n"
    text += f"Страница {page + 1} из {total_pages}\n\n"
    
    for item in items:
        text += f"🧱 {item['name']}\n"
        text += f"   Код: {item['code']}\n"
        text += f"   Категория: {item['category'] or '—'}\n"
        text += f"   Цена: {item['price']}\n\n"
    
    await query.edit_message_text(
        text,
        reply_markup=materials_list_keyboard(user_id, items, page, total_pages)
    )


async def add_material_start(query: CallbackQuery, user_id: int):
    """Начинает добавление материала - запрос названия"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.MATERIAL_ADD_NAME
    session['data'] = {}
    
    await query.edit_message_text(
        "⚙️ ДОБАВЛЕНИЕ МАТЕРИАЛА\n\n"
        "Введите название нового материала:\n"
        "(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )


async def save_material_name(update, user_id: int, name: str):
    """Сохраняет название и запрашивает категорию"""
    from .router import get_admin_session
    from states import AdminStates
    from keyboards.admin import material_category_select_keyboard
    
    excel = get_excel_handler()
    existing = excel.get_product_by_name(name)
    
    if existing:
        await update.message.reply_text(
            "❌ Материал с таким названием уже существует.\n"
            "Введите другое название или нажмите Отмена.",
            reply_markup=back_to_main_button(user_id)
        )
        return
    
    session = get_admin_session(user_id)
    session['data']['name'] = name
    session['state'] = AdminStates.MATERIAL_ADD_CATEGORY
    
    paths = excel.get_category_paths()
    
    await update.message.reply_text(
        f"⚙️ ДОБАВЛЕНИЕ МАТЕРИАЛА\n\n"
        f"Название: {name}\n\n"
        f"Выберите категорию:",
        reply_markup=material_category_select_keyboard(user_id, paths, "mat")
    )


async def save_material_category(query: CallbackQuery, user_id: int, category: str):
    """Сохраняет категорию и запрашивает цену"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['data']['category'] = category
    session['state'] = AdminStates.MATERIAL_ADD_PRICE
    
    await query.edit_message_text(
        f"⚙️ ДОБАВЛЕНИЕ МАТЕРИАЛА\n\n"
        f"Название: {session['data']['name']}\n"
        f"Категория: {category}\n\n"
        f"Введите цену материала (ISK, по умолчанию 0):\n"
        f"(рыночная цена за 1 шт)",
        reply_markup=back_to_main_button(user_id)
    )


async def save_material_price(update, user_id: int, text: str):
    """Сохраняет цену и завершает добавление материала"""
    from .router import get_admin_session, clear_admin_session
    from keyboards.admin import main_menu_keyboard
    from utils.validators import validate_price
    
    price = validate_price(text)
    if price is None:
        price = 0
    
    session = get_admin_session(user_id)
    data = session['data']
    
    excel = get_excel_handler()
    success, message, code = excel.add_item(
        'материал',
        data['name'],
        data['category'],
        1,
        price
    )
    
    clear_admin_session(user_id)
    
    if success:
        await update.message.reply_text(
            f"✅ Материал '{data['name']}' добавлен!\n"
            f"Код: {code}\n\n"
            f"Что делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        await update.message.reply_text(
            f"{message}\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )


async def edit_material_select(query: CallbackQuery, user_id: int, page: int = 0):
    """Показывает список материалов для редактирования"""
    excel = get_excel_handler()
    items, total = excel.get_products_by_type('материал', page, 10)
    
    if not items:
        await query.answer("❌ Нет материалов для редактирования", show_alert=True)
        return
    
    total_pages = (total + 9) // 10
    
    text = "✏️ РЕДАКТИРОВАНИЕ МАТЕРИАЛА\n\n"
    text += "Выберите материал для редактирования:\n"
    text += f"Страница {page + 1} из {total_pages}"
    
    await query.edit_message_text(
        text,
        reply_markup=material_edit_select_keyboard(user_id, items, page, total_pages)
    )


async def edit_material_field(query: CallbackQuery, user_id: int, code: str):
    """Показывает поля для редактирования материала"""
    from .router import get_admin_session
    from states import AdminStates
    
    excel = get_excel_handler()
    material = excel.get_product_by_code(code)
    
    if not material:
        await query.answer("❌ Материал не найден", show_alert=True)
        return
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.MATERIAL_EDIT_FIELD
    session['data'] = {'code': code, 'material': material}
    
    text = f"✏️ РЕДАКТИРОВАНИЕ: {material['Наименование']}\n\n"
    text += f"Код: {code}\n"
    text += f"Текущее название: {material['Наименование']}\n"
    text += f"Текущая категория: {material.get('Категории', '—')}\n"
    text += f"Текущая цена: {material.get('Цена производства', '0 ISK')}\n\n"
    text += "Выберите поле для редактирования:"
    
    await query.edit_message_text(
        text,
        reply_markup=material_edit_field_keyboard(user_id, code)
    )


async def save_material_edit(query: CallbackQuery, user_id: int, code: str, field: str):
    """Запрашивает новое значение для поля"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.MATERIAL_EDIT_FIELD
    session['data']['edit_field'] = field
    session['data']['edit_code'] = code
    
    field_names = {
        'Наименование': 'название',
        'Цена производства': 'цену'
    }
    
    field_name = field_names.get(field, field)
    
    if field == 'Категории':
        excel = get_excel_handler()
        paths = excel.get_category_paths()
        await query.edit_message_text(
            f"✏️ РЕДАКТИРОВАНИЕ\n\n"
            f"Выберите новую категорию:",
            reply_markup=material_category_select_keyboard(user_id, paths, f"field_{code}")
        )
    else:
        await query.edit_message_text(
            f"✏️ РЕДАКТИРОВАНИЕ\n\n"
            f"Введите новое значение для поля '{field_name}':\n"
            f"(или нажмите Отмена)",
            reply_markup=back_to_main_button(user_id)
        )


async def save_material_edit_value(update, user_id: int, text: str):
    """Сохраняет отредактированное значение"""
    from .router import get_admin_session, clear_admin_session
    from keyboards.admin import main_menu_keyboard
    from utils.validators import validate_price
    
    session = get_admin_session(user_id)
    code = session['data']['edit_code']
    field = session['data']['edit_field']
    
    if field == 'Цена производства':
        value = validate_price(text)
        if value is None:
            value = 0
    else:
        value = text
    
    excel = get_excel_handler()
    success, message = excel.update_item(code, field, value)
    
    clear_admin_session(user_id)
    
    await update.message.reply_text(
        f"{message}\n\nЧто делаем дальше?",
        reply_markup=main_menu_keyboard(user_id)
    )


async def delete_material_confirm(query: CallbackQuery, user_id: int, page: int = 0):
    """Показывает список материалов для удаления"""
    excel = get_excel_handler()
    items, total = excel.get_products_by_type('материал', page, 10)
    
    if not items:
        await query.answer("❌ Нет материалов для удаления", show_alert=True)
        return
    
    total_pages = (total + 9) // 10
    
    text = "🗑️ УДАЛЕНИЕ МАТЕРИАЛА\n\n"
    text += "⚠️ ВНИМАНИЕ! Будут удалены все связанные спецификации!\n\n"
    text += "Выберите материал для удаления:\n"
    text += f"Страница {page + 1} из {total_pages}"
    
    await query.edit_message_text(
        text,
        reply_markup=material_delete_select_keyboard(user_id, items, page, total_pages)
    )


async def delete_material_execute(query: CallbackQuery, user_id: int, code: str):
    """Удаляет материал"""
    from keyboards.admin import main_menu_keyboard
    
    excel = get_excel_handler()
    material = excel.get_product_by_code(code)
    
    if not material:
        await query.answer("❌ Материал не найден", show_alert=True)
        return
    
    success, message = excel.delete_item(code)
    
    if success:
        await query.edit_message_text(
            f"✅ Материал '{material['Наименование']}' удалён.\n\n"
            f"Что делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        await query.edit_message_text(
            f"{message}\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )


async def search_materials(query: CallbackQuery, user_id: int):
    """Запрашивает поисковый запрос для материалов"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.MATERIAL_SEARCH
    session['data'] = {'type': 'материал'}
    
    await query.edit_message_text(
        "🔍 ПОИСК МАТЕРИАЛОВ\n\n"
        "Введите название или часть названия материала:\n"
        "(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )
