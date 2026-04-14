import logging
from telegram import CallbackQuery
from keyboards.admin import (
    products_list_keyboard, product_edit_select_keyboard,
    product_edit_field_keyboard, product_category_select_keyboard,
    product_delete_select_keyboard, back_to_main_button,
    product_link_menu_keyboard, product_select_nodes_keyboard,
    product_select_materials_keyboard, main_menu_keyboard
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
    """Сохраняет цену, создаёт изделие и переходит к привязке"""
    from .router import get_admin_session, clear_admin_session
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
    
    if not success:
        clear_admin_session(user_id)
        await update.message.reply_text(
            f"{message}\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
        return
    
    # Сохраняем код изделия и переходим к привязке
    session['data']['code'] = code
    session['data']['pending_links'] = []
    session['data']['current_link_index'] = 0
    session['state'] = AdminStates.PRODUCT_LINK_MENU
    
    await update.message.reply_text(
        f"✅ Изделие '{data['name']}' создано!\n"
        f"Код: {code}\n\n"
        f"Теперь можно привязать узлы и материалы.\n"
        f"Выберите действие:",
        reply_markup=product_link_menu_keyboard(user_id, code)
    )


async def show_product_link_menu(query: CallbackQuery, user_id: int):
    """Показывает меню привязки для изделия"""
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    code = session.get('data', {}).get('code', '')
    
    if not code:
        await query.answer("❌ Ошибка: изделие не найдено", show_alert=True)
        return
    
    text = "🔗 ПРИВЯЗКА КОМПОНЕНТОВ\n\n"
    text += "Выберите действие:\n"
    text += "• Привязать существующий узел\n"
    text += "• Привязать существующий материал\n"
    text += "• Создать новый узел (сразу привяжется)\n"
    text += "• Создать новый материал (сразу привяжется)\n"
    text += "• Завершить настройку"
    
    await query.edit_message_text(
        text,
        reply_markup=product_link_menu_keyboard(user_id, code)
    )


async def product_link_node_select(query: CallbackQuery, user_id: int, page: int = 0):
    """Показывает список узлов для множественного выбора"""
    excel = get_excel_handler()
    nodes, total = excel.get_products_by_type('узел', page, 10)
    
    if not nodes:
        await query.answer("❌ Нет доступных узлов. Создайте новый узел.", show_alert=True)
        return
    
    from .router import get_admin_session
    session = get_admin_session(user_id)
    selected = set(session.get('data', {}).get('selected_nodes', []))
    
    total_pages = (total + 9) // 10
    
    text = "🔩 ВЫБОР УЗЛОВ\n\n"
    text += "Выберите узлы для привязки (можно несколько):\n"
    text += f"Страница {page + 1} из {total_pages}\n\n"
    
    for node in nodes:
        checkbox = "☑️" if node['code'] in selected else "☐"
        text += f"{checkbox} {node['name']} ({node['code']})\n"
    
    await query.edit_message_text(
        text,
        reply_markup=product_select_nodes_keyboard(user_id, nodes, page, total_pages, selected)
    )


async def product_toggle_node(query: CallbackQuery, user_id: int, node_code: str):
    """Переключает выбор узла"""
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    selected = session.get('data', {}).get('selected_nodes', [])
    
    if node_code in selected:
        selected.remove(node_code)
    else:
        selected.append(node_code)
    
    session['data']['selected_nodes'] = selected
    await product_link_node_select(query, user_id, 0)


async def product_confirm_nodes(query: CallbackQuery, user_id: int):
    """Подтверждает выбор узлов и начинает ввод количеств"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    selected = session.get('data', {}).get('selected_nodes', [])
    
    if not selected:
        await query.answer("❌ Выберите хотя бы один узел", show_alert=True)
        return
    
    # Формируем список для пошагового ввода
    excel = get_excel_handler()
    nodes_to_link = []
    for code in selected:
        node = excel.get_product_by_code(code)
        if node:
            nodes_to_link.append({
                'code': code,
                'name': node['Наименование']
            })
    
    session['data']['pending_links'] = nodes_to_link
    session['data']['link_type'] = 'node'
    session['data']['current_link_index'] = 0
    session['data']['selected_nodes'] = []  # Очищаем выбор
    session['state'] = AdminStates.PRODUCT_LINK_NODE_QUANTITY
    
    await _ask_next_node_quantity(query, user_id)


async def _ask_next_node_quantity(query: CallbackQuery, user_id: int):
    """Запрашивает количество для следующего узла"""
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    pending = session.get('data', {}).get('pending_links', [])
    index = session.get('data', {}).get('current_link_index', 0)
    
    if index >= len(pending):
        # Все узлы обработаны
        await show_product_link_menu(query, user_id)
        return
    
    node = pending[index]
    
    await query.edit_message_text(
        f"🔩 КОЛИЧЕСТВО УЗЛА ({index + 1}/{len(pending)})\n\n"
        f"Узел: {node['name']}\n"
        f"Код: {node['code']}\n\n"
        f"Введите количество, необходимое для производства\n"
        f"одного чертежа изделия при эффективности 150%:\n"
        f"(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )


async def save_node_quantity(update, user_id: int, text: str):
    """Сохраняет количество узла и переходит к следующему"""
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
    product_code = data['code']
    pending = data.get('pending_links', [])
    index = data.get('current_link_index', 0)
    
    if index < len(pending):
        node = pending[index]
        excel = get_excel_handler()
        excel.add_specification(product_code, node['code'], quantity)
        
        data['current_link_index'] = index + 1
        
        if data['current_link_index'] < len(pending):
            # Ещё есть узлы
            await update.message.reply_text(
                f"✅ Количество для '{node['name']}' сохранено."
            )
            # Продолжаем ввод
            pending = data.get('pending_links', [])
            idx = data.get('current_link_index', 0)
            node = pending[idx]
            await update.message.reply_text(
                f"🔩 КОЛИЧЕСТВО УЗЛА ({idx + 1}/{len(pending)})\n\n"
                f"Узел: {node['name']}\n"
                f"Код: {node['code']}\n\n"
                f"Введите количество, необходимое для производства\n"
                f"одного чертежа изделия при эффективности 150%:\n"
                f"(или нажмите Отмена)",
                reply_markup=back_to_main_button(user_id)
            )
        else:
            # Все узлы обработаны
            await update.message.reply_text(
                f"✅ Все узлы привязаны!\n\nЧто делаем дальше?",
                reply_markup=product_link_menu_keyboard(user_id, product_code)
            )
            data['pending_links'] = []
            data['current_link_index'] = 0
            data['link_type'] = None


async def product_link_material_select(query: CallbackQuery, user_id: int, page: int = 0):
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
        reply_markup=product_select_materials_keyboard(user_id, materials, page, total_pages, selected)
    )


async def product_toggle_material(query: CallbackQuery, user_id: int, mat_code: str):
    """Переключает выбор материала"""
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    selected = session.get('data', {}).get('selected_materials', [])
    
    if mat_code in selected:
        selected.remove(mat_code)
    else:
        selected.append(mat_code)
    
    session['data']['selected_materials'] = selected
    await product_link_material_select(query, user_id, 0)


async def product_confirm_materials(query: CallbackQuery, user_id: int):
    """Подтверждает выбор материалов и начинает ввод количеств"""
    from .router import get_admin_session
    from states import AdminStates
    
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
    session['state'] = AdminStates.PRODUCT_LINK_MATERIAL_QUANTITY
    
    await _ask_next_material_quantity(query, user_id)


async def _ask_next_material_quantity(query: CallbackQuery, user_id: int):
    """Запрашивает количество для следующего материала"""
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    pending = session.get('data', {}).get('pending_links', [])
    index = session.get('data', {}).get('current_link_index', 0)
    
    if index >= len(pending):
        await show_product_link_menu(query, user_id)
        return
    
    mat = pending[index]
    
    await query.edit_message_text(
        f"🧱 КОЛИЧЕСТВО МАТЕРИАЛА ({index + 1}/{len(pending)})\n\n"
        f"Материал: {mat['name']}\n"
        f"Код: {mat['code']}\n\n"
        f"Введите количество, необходимое для производства\n"
        f"одного чертежа изделия при эффективности 150%:\n"
        f"(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )


async def save_material_quantity(update, user_id: int, text: str):
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
    product_code = data['code']
    pending = data.get('pending_links', [])
    index = data.get('current_link_index', 0)
    
    if index < len(pending):
        mat = pending[index]
        excel = get_excel_handler()
        excel.add_specification(product_code, mat['code'], quantity)
        
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
                f"одного чертежа изделия при эффективности 150%:\n"
                f"(или нажмите Отмена)",
                reply_markup=back_to_main_button(user_id)
            )
        else:
            await update.message.reply_text(
                f"✅ Все материалы привязаны!\n\nЧто делаем дальше?",
                reply_markup=product_link_menu_keyboard(user_id, product_code)
            )
            data['pending_links'] = []
            data['current_link_index'] = 0
            data['link_type'] = None


async def product_create_node_start(query: CallbackQuery, user_id: int):
    """Начинает создание нового узла для привязки"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.PRODUCT_CREATE_NODE_NAME
    session['data']['creating_for_product'] = True
    
    await query.edit_message_text(
        "🔩 СОЗДАНИЕ НОВОГО УЗЛА\n\n"
        "Введите название нового узла:\n"
        "(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )


async def product_create_node_save_name(update, user_id: int, name: str):
    """Сохраняет название нового узла"""
    excel = get_excel_handler()
    existing = excel.get_product_by_name(name)
    
    if existing:
        await update.message.reply_text(
            "❌ Узел с таким названием уже существует.\n"
            "Введите другое название или нажмите Отмена.",
            reply_markup=back_to_main_button(user_id)
        )
        return
    
    from .router import get_admin_session
    from states import AdminStates
    from keyboards.admin import node_category_select_keyboard
    
    session = get_admin_session(user_id)
    session['data']['new_node_name'] = name
    session['state'] = AdminStates.PRODUCT_CREATE_NODE_CATEGORY
    
    paths = excel.get_category_paths()
    
    await update.message.reply_text(
        f"🔩 СОЗДАНИЕ УЗЛА\n\n"
        f"Название: {name}\n\n"
        f"Выберите категорию:",
        reply_markup=node_category_select_keyboard(user_id, paths, "prod_new_node")
    )


async def product_create_node_save_category(query: CallbackQuery, user_id: int, category: str):
    """Сохраняет категорию нового узла"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['data']['new_node_category'] = category
    session['state'] = AdminStates.PRODUCT_CREATE_NODE_MULTIPLICITY
    
    await query.edit_message_text(
        f"🔩 СОЗДАНИЕ УЗЛА\n\n"
        f"Название: {session['data']['new_node_name']}\n"
        f"Категория: {category}\n\n"
        f"Введите кратность (целое число, по умолчанию 1):",
        reply_markup=back_to_main_button(user_id)
    )


async def product_create_node_save_multiplicity(update, user_id: int, text: str):
    """Сохраняет кратность нового узла"""
    from utils.validators import validate_multiplicity
    
    mult = validate_multiplicity(text)
    if mult is None:
        await update.message.reply_text(
            "❌ Введите целое положительное число.",
            reply_markup=back_to_main_button(user_id)
        )
        return
    
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['data']['new_node_multiplicity'] = mult
    session['state'] = AdminStates.PRODUCT_CREATE_NODE_PRICE
    
    await update.message.reply_text(
        f"🔩 СОЗДАНИЕ УЗЛА\n\n"
        f"Название: {session['data']['new_node_name']}\n"
        f"Категория: {session['data']['new_node_category']}\n"
        f"Кратность: {mult}\n\n"
        f"Введите цену производства (ISK, по умолчанию 0):",
        reply_markup=back_to_main_button(user_id)
    )


async def product_create_node_save_price(update, user_id: int, text: str):
    """Сохраняет цену, создаёт узел и запрашивает количество для привязки"""
    from utils.validators import validate_price
    
    price = validate_price(text)
    if price is None:
        price = 0
    
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    data = session['data']
    
    excel = get_excel_handler()
    success, message, code = excel.add_item(
        'узел',
        data['new_node_name'],
        data['new_node_category'],
        data['new_node_multiplicity'],
        price
    )
    
    if not success:
        await update.message.reply_text(
            f"{message}",
            reply_markup=back_to_main_button(user_id)
        )
        return
    
    # Сохраняем узел для привязки и запрашиваем количество
    data['pending_links'] = [{'code': code, 'name': data['new_node_name']}]
    data['link_type'] = 'node'
    data['current_link_index'] = 0
    data['state'] = AdminStates.PRODUCT_LINK_NODE_QUANTITY
    
    # Очищаем временные данные создания
    for key in ['new_node_name', 'new_node_category', 'new_node_multiplicity', 'creating_for_product']:
        if key in data:
            del data[key]
    
    await update.message.reply_text(
        f"✅ Узел '{data['pending_links'][0]['name']}' создан!\n"
        f"Код: {code}\n\n"
        f"Введите количество, необходимое для производства\n"
        f"одного чертежа изделия при эффективности 150%:",
        reply_markup=back_to_main_button(user_id)
    )


async def product_create_material_start(query: CallbackQuery, user_id: int):
    """Начинает создание нового материала для привязки"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.PRODUCT_CREATE_MATERIAL_NAME
    session['data']['creating_for_product'] = True
    
    await query.edit_message_text(
        "🧱 СОЗДАНИЕ НОВОГО МАТЕРИАЛА\n\n"
        "Введите название нового материала:\n"
        "(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )


async def product_create_material_save_name(update, user_id: int, name: str):
    """Сохраняет название нового материала"""
    excel = get_excel_handler()
    existing = excel.get_product_by_name(name)
    
    if existing:
        await update.message.reply_text(
            "❌ Материал с таким названием уже существует.",
            reply_markup=back_to_main_button(user_id)
        )
        return
    
    from .router import get_admin_session
    from states import AdminStates
    from keyboards.admin import material_category_select_keyboard
    
    session = get_admin_session(user_id)
    session['data']['new_material_name'] = name
    session['state'] = AdminStates.PRODUCT_CREATE_MATERIAL_CATEGORY
    
    paths = excel.get_category_paths()
    
    await update.message.reply_text(
        f"🧱 СОЗДАНИЕ МАТЕРИАЛА\n\n"
        f"Название: {name}\n\n"
        f"Выберите категорию:",
        reply_markup=material_category_select_keyboard(user_id, paths, "prod_new_mat")
    )


async def product_create_material_save_category(query: CallbackQuery, user_id: int, category: str):
    """Сохраняет категорию нового материала"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['data']['new_material_category'] = category
    session['state'] = AdminStates.PRODUCT_CREATE_MATERIAL_PRICE
    
    await query.edit_message_text(
        f"🧱 СОЗДАНИЕ МАТЕРИАЛА\n\n"
        f"Название: {session['data']['new_material_name']}\n"
        f"Категория: {category}\n\n"
        f"Введите цену материала (ISK, по умолчанию 0):",
        reply_markup=back_to_main_button(user_id)
    )


async def product_create_material_save_price(update, user_id: int, text: str):
    """Сохраняет цену, создаёт материал и запрашивает количество для привязки"""
    from utils.validators import validate_price
    
    price = validate_price(text)
    if price is None:
        price = 0
    
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    data = session['data']
    
    excel = get_excel_handler()
    success, message, code = excel.add_item(
        'материал',
        data['new_material_name'],
        data['new_material_category'],
        1,
        price
    )
    
    if not success:
        await update.message.reply_text(f"{message}", reply_markup=back_to_main_button(user_id))
        return
    
    data['pending_links'] = [{'code': code, 'name': data['new_material_name']}]
    data['link_type'] = 'material'
    data['current_link_index'] = 0
    data['state'] = AdminStates.PRODUCT_LINK_MATERIAL_QUANTITY
    
    for key in ['new_material_name', 'new_material_category', 'creating_for_product']:
        if key in data:
            del data[key]
    
    await update.message.reply_text(
        f"✅ Материал '{data['pending_links'][0]['name']}' создан!\n"
        f"Код: {code}\n\n"
        f"Введите количество, необходимое для производства\n"
        f"одного чертежа изделия при эффективности 150%:",
        reply_markup=back_to_main_button(user_id)
    )


async def product_finish_setup(query: CallbackQuery, user_id: int):
    """Завершает настройку изделия"""
    from .router import clear_admin_session
    from keyboards.admin import main_menu_keyboard
    
    session = get_admin_session(user_id)
    product_name = session.get('data', {}).get('name', 'Изделие')
    
    clear_admin_session(user_id)
    
    await query.edit_message_text(
        f"✅ Настройка изделия '{product_name}' завершена!\n\n"
        f"Что делаем дальше?",
        reply_markup=main_menu_keyboard(user_id)
    )


# ==================== РЕДАКТИРОВАНИЕ И УДАЛЕНИЕ ====================

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
