import logging
from telegram import CallbackQuery
from keyboards.admin import (
    nodes_list_keyboard, node_edit_select_keyboard,
    node_edit_field_keyboard, node_category_select_keyboard,
    node_delete_select_keyboard, back_to_main_button,
    node_link_menu_keyboard, node_select_materials_keyboard,
    main_menu_keyboard
)
from excel_handler import get_excel_handler
from utils.formatters import format_price
from states import AdminStates

logger = logging.getLogger(__name__)


async def show_nodes_list(query: CallbackQuery, user_id: int, page: int = 0):
    """Показывает список узлов с пагинацией"""
    excel = get_excel_handler()
    items, total = excel.get_products_by_type('узел', page, 10)
    
    if not items:
        text = "🔩 УЗЛЫ\n\nНет узлов.\n\nИспользуйте «➕ Добавить» чтобы создать узел."
        await query.edit_message_text(
            text,
            reply_markup=nodes_list_keyboard(user_id, [], page, 0)
        )
        return
    
    total_pages = (total + 9) // 10
    
    text = f"🔩 УЗЛЫ\n\n"
    text += f"Страница {page + 1} из {total_pages}\n\n"
    
    for item in items:
        text += f"🔧 {item['name']}\n"
        text += f"   Код: {item['code']}\n"
        text += f"   Категория: {item['category'] or '—'}\n"
        text += f"   Кратность: {item['multiplicity']}\n"
        text += f"   Цена: {item['price']}\n\n"
    
    await query.edit_message_text(
        text,
        reply_markup=nodes_list_keyboard(user_id, items, page, total_pages)
    )


async def add_node_start(query: CallbackQuery, user_id: int):
    """Начинает добавление узла - запрос названия"""
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.NODE_ADD_NAME
    session['data'] = {}
    
    await query.edit_message_text(
        "🔩 ДОБАВЛЕНИЕ УЗЛА\n\n"
        "Введите название нового узла:\n"
        "(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )


async def save_node_name(update, user_id: int, name: str):
    """Сохраняет название и запрашивает категорию"""
    from .router import get_admin_session
    from keyboards.admin import node_category_select_keyboard
    
    excel = get_excel_handler()
    existing = excel.get_product_by_name(name)
    
    if existing:
        await update.message.reply_text(
            "❌ Узел с таким названием уже существует.\n"
            "Введите другое название или нажмите Отмена.",
            reply_markup=back_to_main_button(user_id)
        )
        return
    
    session = get_admin_session(user_id)
    session['data']['name'] = name
    session['state'] = AdminStates.NODE_ADD_CATEGORY
    
    paths = excel.get_category_paths()
    
    await update.message.reply_text(
        f"🔩 ДОБАВЛЕНИЕ УЗЛА\n\n"
        f"Название: {name}\n\n"
        f"Выберите категорию:",
        reply_markup=node_category_select_keyboard(user_id, paths, "node")
    )


async def save_node_category(query: CallbackQuery, user_id: int, category: str):
    """Сохраняет категорию и запрашивает кратность"""
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    session['data']['category'] = category
    session['state'] = AdminStates.NODE_ADD_MULTIPLICITY
    
    await query.edit_message_text(
        f"🔩 ДОБАВЛЕНИЕ УЗЛА\n\n"
        f"Название: {session['data']['name']}\n"
        f"Категория: {category}\n\n"
        f"Введите кратность (целое число, по умолчанию 1):\n"
        f"(сколько узлов получается из одного чертежа)",
        reply_markup=back_to_main_button(user_id)
    )


async def save_node_multiplicity(update, user_id: int, text: str):
    """Сохраняет кратность и запрашивает цену производства"""
    from .router import get_admin_session
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
    session['state'] = AdminStates.NODE_ADD_PRICE
    
    await update.message.reply_text(
        f"🔩 ДОБАВЛЕНИЕ УЗЛА\n\n"
        f"Название: {session['data']['name']}\n"
        f"Категория: {session['data']['category']}\n"
        f"Кратность: {mult}\n\n"
        f"Введите цену производства (ISK, по умолчанию 0):\n"
        f"(стоимость запуска одного чертежа в производство)",
        reply_markup=back_to_main_button(user_id)
    )


async def save_node_price(update, user_id: int, text: str):
    """Сохраняет цену, создаёт узел и переходит к привязке материалов"""
    from .router import get_admin_session, clear_admin_session
    from utils.validators import validate_price
    
    price = validate_price(text)
    if price is None:
        price = 0
    
    session = get_admin_session(user_id)
    data = session['data']
    
    excel = get_excel_handler()
    success, message, code = excel.add_item(
        'узел',
        data['name'],
        data['category'],
        data['multiplicity'],
        price
    )
    
    if not success:
        clear_admin_session(user_id)
        await update.message.reply_text(
            f"{message}\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
        return
    
    session['data']['code'] = code
    session['data']['pending_links'] = []
    session['data']['current_link_index'] = 0
    session['state'] = AdminStates.NODE_LINK_MENU
    
    await update.message.reply_text(
        f"✅ Узел '{data['name']}' создан!\n"
        f"Код: {code}\n\n"
        f"Теперь можно привязать материалы.\n"
        f"Выберите действие:",
        reply_markup=node_link_menu_keyboard(user_id, code)
    )


async def show_node_link_menu(query: CallbackQuery, user_id: int):
    """Показывает меню привязки для узла"""
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    code = session.get('data', {}).get('code', '')
    
    if not code:
        await query.answer("❌ Ошибка: узел не найден", show_alert=True)
        return
    
    text = "🔗 ПРИВЯЗКА МАТЕРИАЛОВ\n\n"
    text += "Выберите действие:\n"
    text += "• Привязать существующий материал\n"
    text += "• Создать новый материал (сразу привяжется)\n"
    text += "• Завершить настройку"
    
    await query.edit_message_text(
        text,
        reply_markup=node_link_menu_keyboard(user_id, code)
    )


async def node_link_material_select(query: CallbackQuery, user_id: int, page: int = 0):
    """Показывает список материалов для множественного выбора"""
    excel = get_excel_handler()
    materials, total = excel.get_products_by_type('материал', page, 10)
    
    if not materials:
        await query.answer("❌ Нет доступных материалов. Создайте новый материал.", show_alert=True)
        return
    
    from .router import get_admin_session
    session = get_admin_session(user_id)
    selected = set(session.get('data', {}).get('selected_materials', []))
    
    total_pages = (total + 9) // 10
    
    text = "🧱 ВЫБОР МАТЕРИАЛОВ\n\n"
    text += "Выберите материалы для привязки (можно несколько):\n"
    text += f"Страница {page + 1} из {total_pages}\n\n"
    
    for mat in materials:
        checkbox = "☑️" if mat['code'] in selected else "☐"
        text += f"{checkbox} {mat['name']} ({mat['code']})\n"
    
    await query.edit_message_text(
        text,
        reply_markup=node_select_materials_keyboard(user_id, materials, page, total_pages, selected)
    )


async def node_toggle_material(query: CallbackQuery, user_id: int, mat_code: str):
    """Переключает выбор материала"""
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    selected = session.get('data', {}).get('selected_materials', [])
    
    if mat_code in selected:
        selected.remove(mat_code)
    else:
        selected.append(mat_code)
    
    session['data']['selected_materials'] = selected
    await node_link_material_select(query, user_id, 0)


async def node_confirm_materials(query: CallbackQuery, user_id: int):
    """Подтверждает выбор материалов и начинает ввод количеств"""
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    selected = session.get('data', {}).get('selected_materials', [])
    
    if not selected:
        await query.answer("❌ Выберите хотя бы один материал", show_alert=True)
        return
    
    excel = get_excel_handler()
    materials_to_link = []
    for code in selected:
        mat = excel.get_product_by_code(code)
        if mat:
            materials_to_link.append({
                'code': code,
                'name': mat['Наименование']
            })
    
    session['data']['pending_links'] = materials_to_link
    session['data']['link_type'] = 'material'
    session['data']['current_link_index'] = 0
    session['data']['selected_materials'] = []
    session['state'] = AdminStates.NODE_LINK_MATERIAL_QUANTITY
    
    await _ask_next_material_quantity(query, user_id)


async def _ask_next_material_quantity(query: CallbackQuery, user_id: int):
    """Запрашивает количество для следующего материала"""
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    pending = session.get('data', {}).get('pending_links', [])
    index = session.get('data', {}).get('current_link_index', 0)
    
    if index >= len(pending):
        await show_node_link_menu(query, user_id)
        return
    
    mat = pending[index]
    
    await query.edit_message_text(
        f"🧱 КОЛИЧЕСТВО МАТЕРИАЛА ({index + 1}/{len(pending)})\n\n"
        f"Материал: {mat['name']}\n"
        f"Код: {mat['code']}\n\n"
        f"Введите количество, необходимое для производства\n"
        f"одного чертежа узла при эффективности 150%:\n"
        f"(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )


async def save_node_material_quantity(update, user_id: int, text: str):
    """Сохраняет количество материала и переходит к следующему"""
    from .router import get_admin_session
    from utils.validators import validate_float
    
    quantity = validate_float(text, min_val=0.01)
    if quantity is None:
        await update.message.reply_text(
            "❌ Введите положительное число.",
            reply_markup=back_to_main_button(user_id)
        )
        return
    
    session = get_admin_session(user_id)
    data = session['data']
    node_code = data['code']
    pending = data.get('pending_links', [])
    index = data.get('current_link_index', 0)
    
    if index < len(pending):
        mat = pending[index]
        excel = get_excel_handler()
        excel.add_specification(node_code, mat['code'], quantity)
        
        data['current_link_index'] = index + 1
        
        if data['current_link_index'] < len(pending):
            await update.message.reply_text(
                f"✅ Количество для '{mat['name']}' сохранено."
            )
            pending = data.get('pending_links', [])
            idx = data.get('current_link_index', 0)
            mat = pending[idx]
            await update.message.reply_text(
                f"🧱 КОЛИЧЕСТВО МАТЕРИАЛА ({idx + 1}/{len(pending)})\n\n"
                f"Материал: {mat['name']}\n"
                f"Код: {mat['code']}\n\n"
                f"Введите количество, необходимое для производства\n"
                f"одного чертежа узла при эффективности 150%:\n"
                f"(или нажмите Отмена)",
                reply_markup=back_to_main_button(user_id)
            )
        else:
            await update.message.reply_text(
                f"✅ Все материалы привязаны!\n\nЧто делаем дальше?",
                reply_markup=node_link_menu_keyboard(user_id, node_code)
            )
            data['pending_links'] = []
            data['current_link_index'] = 0
            data['link_type'] = None


async def node_create_material_start(query: CallbackQuery, user_id: int):
    """Начинает создание нового материала для привязки к узлу (категория = категория узла)"""
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.NODE_CREATE_MATERIAL_NAME
    session['data']['creating_for_node'] = True
    
    await query.edit_message_text(
        "🧱 СОЗДАНИЕ НОВОГО МАТЕРИАЛА\n\n"
        "Введите название нового материала:\n"
        "(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )


async def node_create_material_save_name(update, user_id: int, name: str):
    """Сохраняет название нового материала и запрашивает цену"""
    excel = get_excel_handler()
    existing = excel.get_product_by_name(name)
    
    if existing:
        await update.message.reply_text(
            "❌ Материал с таким названием уже существует.",
            reply_markup=back_to_main_button(user_id)
        )
        return
    
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    session['data']['new_material_name'] = name
    session['state'] = AdminStates.NODE_CREATE_MATERIAL_PRICE
    
    await update.message.reply_text(
        f"🧱 СОЗДАНИЕ МАТЕРИАЛА\n\n"
        f"Название: {name}\n"
        f"Категория: {session['data']['category']} (от узла)\n\n"
        f"Введите цену материала (ISK, по умолчанию 0):",
        reply_markup=back_to_main_button(user_id)
    )


async def node_create_material_save_price(update, user_id: int, text: str):
    """Сохраняет цену, создаёт материал и запрашивает количество для привязки к узлу"""
    from utils.validators import validate_price
    
    price = validate_price(text)
    if price is None:
        price = 0
    
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    data = session['data']
    
    excel = get_excel_handler()
    success, message, code = excel.add_item(
        'материал',
        data['new_material_name'],
        data['category'],
        1,
        price
    )
    
    if not success:
        await update.message.reply_text(f"{message}", reply_markup=back_to_main_button(user_id))
        return
    
    data['pending_links'] = [{'code': code, 'name': data['new_material_name']}]
    data['link_type'] = 'material'
    data['current_link_index'] = 0
    data['state'] = AdminStates.NODE_LINK_MATERIAL_QUANTITY
    
    for key in ['new_material_name', 'creating_for_node']:
        if key in data:
            del data[key]
    
    await update.message.reply_text(
        f"✅ Материал '{data['pending_links'][0]['name']}' создан!\n"
        f"Код: {code}\n\n"
        f"Введите количество, необходимое для производства\n"
        f"одного чертежа узла при эффективности 150%:",
        reply_markup=back_to_main_button(user_id)
    )


async def node_finish_setup(query: CallbackQuery, user_id: int):
    """Завершает настройку узла"""
    from .router import clear_admin_session, get_admin_session
    
    session = get_admin_session(user_id)
    node_name = session.get('data', {}).get('name', 'Узел')
    
    clear_admin_session(user_id)
    
    await query.edit_message_text(
        f"✅ Настройка узла '{node_name}' завершена!\n\n"
        f"Что делаем дальше?",
        reply_markup=main_menu_keyboard(user_id)
    )


# ==================== РЕДАКТИРОВАНИЕ И УДАЛЕНИЕ ====================

async def edit_node_select(query: CallbackQuery, user_id: int, page: int = 0):
    """Показывает список узлов для редактирования"""
    excel = get_excel_handler()
    items, total = excel.get_products_by_type('узел', page, 10)
    
    if not items:
        await query.answer("❌ Нет узлов для редактирования", show_alert=True)
        return
    
    total_pages = (total + 9) // 10
    
    text = "✏️ РЕДАКТИРОВАНИЕ УЗЛА\n\n"
    text += "Выберите узел для редактирования:\n"
    text += f"Страница {page + 1} из {total_pages}"
    
    await query.edit_message_text(
        text,
        reply_markup=node_edit_select_keyboard(user_id, items, page, total_pages)
    )


async def edit_node_field(query: CallbackQuery, user_id: int, code: str):
    """Показывает поля для редактирования узла"""
    from .router import get_admin_session
    
    excel = get_excel_handler()
    node = excel.get_product_by_code(code)
    
    if not node:
        await query.answer("❌ Узел не найден", show_alert=True)
        return
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.NODE_EDIT_FIELD
    session['data'] = {'code': code, 'node': node}
    
    text = f"✏️ РЕДАКТИРОВАНИЕ: {node['Наименование']}\n\n"
    text += f"Код: {code}\n"
    text += f"Текущее название: {node['Наименование']}\n"
    text += f"Текущая категория: {node.get('Категории', '—')}\n"
    text += f"Текущая кратность: {node.get('Кратность', 1)}\n"
    text += f"Текущая цена: {node.get('Цена производства', '0 ISK')}\n\n"
    text += "Выберите поле для редактирования:"
    
    await query.edit_message_text(
        text,
        reply_markup=node_edit_field_keyboard(user_id, code)
    )


async def save_node_edit(query: CallbackQuery, user_id: int, code: str, field: str):
    """Запрашивает новое значение для поля"""
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.NODE_EDIT_FIELD
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
            reply_markup=node_category_select_keyboard(user_id, paths, f"field_{code}")
        )
    else:
        await query.edit_message_text(
            f"✏️ РЕДАКТИРОВАНИЕ\n\n"
            f"Введите новое значение для поля '{field_name}':\n"
            f"(или нажмите Отмена)",
            reply_markup=back_to_main_button(user_id)
        )


async def save_node_edit_value(update, user_id: int, text: str):
    """Сохраняет отредактированное значение"""
    from .router import get_admin_session, clear_admin_session
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


async def delete_node_confirm(query: CallbackQuery, user_id: int, page: int = 0):
    """Показывает список узлов для удаления"""
    excel = get_excel_handler()
    items, total = excel.get_products_by_type('узел', page, 10)
    
    if not items:
        await query.answer("❌ Нет узлов для удаления", show_alert=True)
        return
    
    total_pages = (total + 9) // 10
    
    text = "🗑️ УДАЛЕНИЕ УЗЛА\n\n"
    text += "⚠️ ВНИМАНИЕ! Будут удалены все связанные спецификации!\n\n"
    text += "Выберите узел для удаления:\n"
    text += f"Страница {page + 1} из {total_pages}"
    
    await query.edit_message_text(
        text,
        reply_markup=node_delete_select_keyboard(user_id, items, page, total_pages)
    )


async def delete_node_execute(query: CallbackQuery, user_id: int, code: str):
    """Удаляет узел"""
    excel = get_excel_handler()
    node = excel.get_product_by_code(code)
    
    if not node:
        await query.answer("❌ Узел не найден", show_alert=True)
        return
    
    success, message = excel.delete_item(code)
    
    if success:
        await query.edit_message_text(
            f"✅ Узел '{node['Наименование']}' удалён.\n\n"
            f"Что делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        await query.edit_message_text(
            f"{message}\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )


async def search_nodes(query: CallbackQuery, user_id: int):
    """Запрашивает поисковый запрос для узлов"""
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.NODE_SEARCH
    session['data'] = {'type': 'узел'}
    
    await query.edit_message_text(
        "🔍 ПОИСК УЗЛОВ\n\n"
        "Введите название или часть названия узла:\n"
        "(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )
