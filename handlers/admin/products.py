import logging
from telegram import CallbackQuery
from keyboards.admin import (
    products_list_keyboard, product_edit_select_keyboard,
    product_edit_field_keyboard, product_category_select_keyboard,
    product_delete_select_keyboard, back_to_main_button, cancel_button
)
from excel_handler import get_excel_handler
from utils.formatters import format_price

logger = logging.getLogger(__name__)


async def show_products_list(query: CallbackQuery, user_id: int, page: int = 0):
    """Показывает список изделий с пагинацией"""
    excel = get_excel_handler()
    items, total = excel.get_products_by_type('изделие', page, 10)
    
    if not items:
        text = "🏗️ ИЗДЕЛИЯ\n\nНет изделий.\n\nИспользуйте «➕ Добавить» чтобы создать изделие."
        await query.edit_message_text(
            text,
            reply_markup=products_list_keyboard(user_id, [], page, 0)
        )
        return
    
    total_pages = (total + 9) // 10
    
    text = f"🏗️ ИЗДЕЛИЯ\n\n"
    text += f"Страница {page + 1} из {total_pages}\n\n"
    
    for item in items:
        text += f"📦 {item['name']}\n"
        text += f"   Код: {item['code']}\n"
        text += f"   Категория: {item['category'] or '—'}\n"
        text += f"   Кратность: {item['multiplicity']}\n"
        text += f"   Цена: {item['price']}\n\n"
    
    await query.edit_message_text(
        text,
        reply_markup=products_list_keyboard(user_id, items, page, total_pages)
    )


async def add_product_start(query: CallbackQuery, user_id: int):
    """Начинает добавление изделия - запрос названия"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.PRODUCT_ADD_NAME
    session['data'] = {}
    
    await query.edit_message_text(
        "🏗️ ДОБАВЛЕНИЕ ИЗДЕЛИЯ\n\n"
        "Введите название нового изделия:\n"
        "(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )


async def save_product_name(update, user_id: int, name: str):
    """Сохраняет название и запрашивает категорию"""
    from .router import get_admin_session
    from states import AdminStates
    from keyboards.admin import product_category_select_keyboard
    
    excel = get_excel_handler()
    existing = excel.get_product_by_name(name)
    
    if existing:
        await update.message.reply_text(
            "❌ Изделие с таким названием уже существует.\n"
            "Введите другое название или нажмите Отмена.",
            reply_markup=back_to_main_button(user_id)
        )
        return
    
    session = get_admin_session(user_id)
    session['data']['name'] = name
    session['state'] = AdminStates.PRODUCT_ADD_CATEGORY
    
    paths = excel.get_category_paths()
    
    await update.message.reply_text(
        f"🏗️ ДОБАВЛЕНИЕ ИЗДЕЛИЯ\n\n"
        f"Название: {name}\n\n"
        f"Выберите категорию:",
        reply_markup=product_category_select_keyboard(user_id, paths, "prod")
    )


async def save_product_category(query: CallbackQuery, user_id: int, category: str):
    """Сохраняет категорию и запрашивает кратность"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['data']['category'] = category
    session['state'] = AdminStates.PRODUCT_ADD_MULTIPLICITY
    
    await query.edit_message_text(
        f"🏗️ ДОБАВЛЕНИЕ ИЗДЕЛИЯ\n\n"
        f"Название: {session['data']['name']}\n"
        f"Категория: {category}\n\n"
        f"Введите кратность (целое число, по умолчанию 1):\n"
        f"(сколько изделий получается из одного чертежа)",
        reply_markup=back_to_main_button(user_id)
    )


async def save_product_multiplicity(update, user_id: int, text: str):
    """Сохраняет кратность и запрашивает цену производства"""
    from .router import get_admin_session
    from states import AdminStates
    from utils.validators import validate_multiplicity
    
    mult = validate_multiplicity(text)
    if mult is None:
        await update.message.reply_text(
            "❌ Введите целое положительное число.\n"
            "Попробуйте снова или нажмите Отмена.",
            reply_markup=back_to_main_button(user_id)
        )
        return
    
    session = get_admin_session(user_id)
    session['data']['multiplicity'] = mult
    session['state'] = AdminStates.PRODUCT_ADD_PRICE
    
    await update.message.reply_text(
        f"🏗️ ДОБАВЛЕНИЕ ИЗДЕЛИЯ\n\n"
        f"Название: {session['data']['name']}\n"
        f"Категория: {session['data']['category']}\n"
        f"Кратность: {mult}\n\n"
        f"Введите цену производства (ISK, по умолчанию 0):\n"
        f"(стоимость запуска одного чертежа в производство)",
        reply_markup=back_to_main_button(user_id)
    )


async def save_product_price(update, user_id: int, text: str):
    """Сохраняет цену и завершает добавление изделия"""
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
        'изделие',
        data['name'],
        data['category'],
        data['multiplicity'],
        price
    )
    
    clear_admin_session(user_id)
    
    if success:
        await update.message.reply_text(
            f"✅ Изделие '{data['name']}' добавлено!\n"
            f"Код: {code}\n\n"
            f"Что делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        await update.message.reply_text(
            f"{message}\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )


async def edit_product_select(query: CallbackQuery, user_id: int, page: int = 0):
    """Показывает список изделий для редактирования"""
    excel = get_excel_handler()
    items, total = excel.get_products_by_type('изделие', page, 10)
    
    if not items:
        await query.answer("❌ Нет изделий для редактирования", show_alert=True)
        return
    
    total_pages = (total + 9) // 10
    
    text = "✏️ РЕДАКТИРОВАНИЕ ИЗДЕЛИЯ\n\n"
    text += "Выберите изделие для редактирования:\n"
    text += f"Страница {page + 1} из {total_pages}"
    
    await query.edit_message_text(
        text,
        reply_markup=product_edit_select_keyboard(user_id, items, page, total_pages)
    )


async def edit_product_field(query: CallbackQuery, user_id: int, code: str):
    """Показывает поля для редактирования изделия"""
    from .router import get_admin_session
    from states import AdminStates
    
    excel = get_excel_handler()
    product = excel.get_product_by_code(code)
    
    if not product:
        await query.answer("❌ Изделие не найдено", show_alert=True)
        return
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.PRODUCT_EDIT_FIELD
    session['data'] = {'code': code, 'product': product}
    
    text = f"✏️ РЕДАКТИРОВАНИЕ: {product['Наименование']}\n\n"
    text += f"Код: {code}\n"
    text += f"Текущее название: {product['Наименование']}\n"
    text += f"Текущая категория: {product.get('Категории', '—')}\n"
    text += f"Текущая кратность: {product.get('Кратность', 1)}\n"
    text += f"Текущая цена: {product.get('Цена производства', '0 ISK')}\n\n"
    text += "Выберите поле для редактирования:"
    
    await query.edit_message_text(
        text,
        reply_markup=product_edit_field_keyboard(user_id, code)
    )


async def save_product_edit(query: CallbackQuery, user_id: int, code: str, field: str):
    """Запрашивает новое значение для поля"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.PRODUCT_EDIT_FIELD
    session['data']['edit_field'] = field
    session['data']['edit_code'] = code
    
    field_names = {
        'Наименование': 'название',
        'Кратность': 'кратность',
        'Цена производства': 'цену производства'
    }
    
    field_name = field_names.get(field, field)
    
    if field == 'Категории':
        excel = get_excel_handler()
        paths = excel.get_category_paths()
        await query.edit_message_text(
            f"✏️ РЕДАКТИРОВАНИЕ\n\n"
            f"Выберите новую категорию:",
            reply_markup=product_category_select_keyboard(user_id, paths, f"field_{code}")
        )
    else:
        await query.edit_message_text(
            f"✏️ РЕДАКТИРОВАНИЕ\n\n"
            f"Введите новое значение для поля '{field_name}':\n"
            f"(или нажмите Отмена)",
            reply_markup=back_to_main_button(user_id)
        )


async def save_product_edit_value(update, user_id: int, text: str):
    """Сохраняет отредактированное значение"""
    from .router import get_admin_session, clear_admin_session
    from keyboards.admin import main_menu_keyboard
    from utils.validators import validate_price, validate_multiplicity
    
    session = get_admin_session(user_id)
    code = session['data']['edit_code']
    field = session['data']['edit_field']
    
    if field == 'Кратность':
        value = validate_multiplicity(text)
        if value is None:
            await update.message.reply_text(
                "❌ Введите целое положительное число.",
                reply_markup=back_to_main_button(user_id)
            )
            return
    elif field == 'Цена производства':
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


async def delete_product_confirm(query: CallbackQuery, user_id: int, page: int = 0):
    """Показывает список изделий для удаления"""
    excel = get_excel_handler()
    items, total = excel.get_products_by_type('изделие', page, 10)
    
    if not items:
        await query.answer("❌ Нет изделий для удаления", show_alert=True)
        return
    
    total_pages = (total + 9) // 10
    
    text = "🗑️ УДАЛЕНИЕ ИЗДЕЛИЯ\n\n"
    text += "⚠️ ВНИМАНИЕ! Будут удалены все связанные спецификации!\n\n"
    text += "Выберите изделие для удаления:\n"
    text += f"Страница {page + 1} из {total_pages}"
    
    await query.edit_message_text(
        text,
        reply_markup=product_delete_select_keyboard(user_id, items, page, total_pages)
    )


async def delete_product_execute(query: CallbackQuery, user_id: int, code: str):
    """Удаляет изделие"""
    from keyboards.admin import main_menu_keyboard
    
    excel = get_excel_handler()
    product = excel.get_product_by_code(code)
    
    if not product:
        await query.answer("❌ Изделие не найдено", show_alert=True)
        return
    
    success, message = excel.delete_item(code)
    
    if success:
        await query.edit_message_text(
            f"✅ Изделие '{product['Наименование']}' удалено.\n\n"
            f"Что делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        await query.edit_message_text(
            f"{message}\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )


async def search_products(query: CallbackQuery, user_id: int):
    """Запрашивает поисковый запрос для изделий"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.PRODUCT_SEARCH
    session['data'] = {'type': 'изделие'}
    
    await query.edit_message_text(
        "🔍 ПОИСК ИЗДЕЛИЙ\n\n"
        "Введите название или часть названия изделия:\n"
        "(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )
