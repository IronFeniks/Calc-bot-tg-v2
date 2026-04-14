from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import hashlib

# Словарь для хранения маппинга хэшей к оригинальным данным
_hash_mapping = {}

def get_hash_mapping(user_id: int) -> dict:
    """Получить маппинг хэшей для пользователя"""
    if user_id not in _hash_mapping:
        _hash_mapping[user_id] = {}
    return _hash_mapping[user_id]

def clear_hash_mapping(user_id: int):
    """Очистить маппинг хэшей для пользователя"""
    if user_id in _hash_mapping:
        _hash_mapping[user_id] = {}

def make_callback(user_id: int, action: str, data: str = "") -> str:
    """Создаёт callback_data с проверкой длины (Telegram лимит 64 байта)"""
    if data:
        base = f"user_{user_id}_{action}_{data}"
    else:
        base = f"user_{user_id}_{action}"
    
    if len(base.encode()) <= 64:
        return base
    
    data_hash = hashlib.md5(data.encode()).hexdigest()[:8]
    mapping = get_hash_mapping(user_id)
    mapping[f"{action}_{data_hash}"] = data
    
    return f"user_{user_id}_{action}_{data_hash}"

def restore_callback_data(user_id: int, action: str, data_hash: str) -> str:
    """Восстанавливает оригинальные данные из хэша"""
    mapping = get_hash_mapping(user_id)
    key = f"{action}_{data_hash}"
    if key in mapping:
        return mapping[key]
    return data_hash


def mode_selection_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора режима для админа"""
    keyboard = [
        [InlineKeyboardButton("🧮 Калькулятор", callback_data=make_callback(user_id, "mode_calculator"))],
        [InlineKeyboardButton("⚙️ Администрирование", callback_data=make_callback(user_id, "mode_admin"))],
        [InlineKeyboardButton("📖 Помощь", callback_data=make_callback(user_id, "mode_help"))],
        [InlineKeyboardButton("🚪 Выход", callback_data=make_callback(user_id, "mode_exit"))]
    ]
    return InlineKeyboardMarkup(keyboard)


def cancel_button(user_id: int) -> InlineKeyboardMarkup:
    """Кнопка отмены"""
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))]]
    return InlineKeyboardMarkup(keyboard)


def back_button(user_id: int, to: str) -> InlineKeyboardMarkup:
    """Кнопка назад с указанием куда"""
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, f"back_to_{to}"))],
        [InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_to_main_button(user_id: int) -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню админки"""
    keyboard = [
        [InlineKeyboardButton("🔙 В главное меню", callback_data=make_callback(user_id, "admin_back_to_main"))],
        [InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))]
    ]
    return InlineKeyboardMarkup(keyboard)


def main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Главное меню админки"""
    keyboard = [
        [InlineKeyboardButton("📋 Категории", callback_data=make_callback(user_id, "admin_categories"))],
        [InlineKeyboardButton("🏗️ Изделия", callback_data=make_callback(user_id, "admin_products"))],
        [InlineKeyboardButton("🔩 Узлы", callback_data=make_callback(user_id, "admin_nodes"))],
        [InlineKeyboardButton("⚙️ Материалы", callback_data=make_callback(user_id, "admin_materials"))],
        [InlineKeyboardButton("🔗 Спецификации", callback_data=make_callback(user_id, "admin_spec"))],
        [InlineKeyboardButton("👥 Администраторы", callback_data=make_callback(user_id, "admin_admins"))],
        [InlineKeyboardButton("🔍 Поиск", callback_data=make_callback(user_id, "admin_search"))],
        [InlineKeyboardButton("🚪 Выход", callback_data=make_callback(user_id, "admin_exit"))]
    ]
    return InlineKeyboardMarkup(keyboard)


def confirm_delete_keyboard(user_id: int, item_id: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления"""
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data=make_callback(user_id, f"admin_confirm_delete_{item_id}"))],
        [InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_back_to_main"))]
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== КАТЕГОРИИ ====================

def categories_list_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для списка категорий"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить категорию", callback_data=make_callback(user_id, "admin_categories_add"))],
        [InlineKeyboardButton("✏️ Редактировать", callback_data=make_callback(user_id, "admin_categories_edit"))],
        [InlineKeyboardButton("🗑️ Удалить", callback_data=make_callback(user_id, "admin_categories_delete"))],
        [InlineKeyboardButton("🔙 В главное меню", callback_data=make_callback(user_id, "admin_back_to_main"))]
    ]
    return InlineKeyboardMarkup(keyboard)


def category_add_parent_keyboard(user_id: int, paths: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора родительской категории"""
    keyboard = []
    
    keyboard.append([InlineKeyboardButton("🌳 Корень", callback_data=make_callback(user_id, "admin_cat_parent", "root"))])
    
    for path in paths[:10]:
        short_path = path[:30] + "..." if len(path) > 30 else path
        keyboard.append([InlineKeyboardButton(
            f"📁 {short_path}",
            callback_data=make_callback(user_id, "admin_cat_parent", path)
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_categories"))])
    
    return InlineKeyboardMarkup(keyboard)


def category_edit_select_keyboard(user_id: int, paths: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора категории для редактирования"""
    keyboard = []
    
    for path in paths[:15]:
        short_path = path[:30] + "..." if len(path) > 30 else path
        keyboard.append([InlineKeyboardButton(
            f"📁 {short_path}",
            callback_data=make_callback(user_id, "admin_cat_edit", path)
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_categories"))])
    
    return InlineKeyboardMarkup(keyboard)


def category_delete_select_keyboard(user_id: int, paths: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора категории для удаления"""
    keyboard = []
    
    for path in paths[:15]:
        short_path = path[:30] + "..." if len(path) > 30 else path
        keyboard.append([InlineKeyboardButton(
            f"📁 {short_path}",
            callback_data=make_callback(user_id, "admin_cat_delete", path)
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_categories"))])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== ИЗДЕЛИЯ ====================

def products_list_keyboard(user_id: int, items: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура для списка изделий"""
    keyboard = []
    
    keyboard.append([InlineKeyboardButton("➕ Добавить изделие", callback_data=make_callback(user_id, "admin_products_add"))])
    
    if items:
        keyboard.append([InlineKeyboardButton("✏️ Редактировать", callback_data=make_callback(user_id, "admin_products_edit"))])
        keyboard.append([InlineKeyboardButton("🗑️ Удалить", callback_data=make_callback(user_id, "admin_products_delete"))])
    
    keyboard.append([InlineKeyboardButton("🔍 Поиск", callback_data=make_callback(user_id, "admin_products_search"))])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_products_page", str(page-1))))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_products_page", str(page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data=make_callback(user_id, "admin_back_to_main"))])
    
    return InlineKeyboardMarkup(keyboard)


def product_category_select_keyboard(user_id: int, paths: list, prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора категории для изделия"""
    keyboard = []
    
    for path in paths[:15]:
        short_path = path[:30] + "..." if len(path) > 30 else path
        keyboard.append([InlineKeyboardButton(
            f"📁 {short_path}",
            callback_data=make_callback(user_id, f"admin_{prefix}_cat", path)
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_products"))])
    
    return InlineKeyboardMarkup(keyboard)


def product_edit_select_keyboard(user_id: int, items: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора изделия для редактирования"""
    keyboard = []
    
    for item in items:
        keyboard.append([InlineKeyboardButton(
            f"📦 {item['name']} ({item['code']})",
            callback_data=make_callback(user_id, "admin_prod_edit", item['code'])
        )])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_products_edit_page", str(page-1))))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_products_edit_page", str(page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_products"))])
    
    return InlineKeyboardMarkup(keyboard)


def product_edit_field_keyboard(user_id: int, code: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора поля для редактирования изделия"""
    keyboard = [
        [InlineKeyboardButton("📝 Название", callback_data=make_callback(user_id, f"admin_prod_field", f"{code}_Наименование"))],
        [InlineKeyboardButton("📂 Категория", callback_data=make_callback(user_id, f"admin_prod_field", f"{code}_Категории"))],
        [InlineKeyboardButton("🔢 Кратность", callback_data=make_callback(user_id, f"admin_prod_field", f"{code}_Кратность"))],
        [InlineKeyboardButton("💰 Цена производства", callback_data=make_callback(user_id, f"admin_prod_field", f"{code}_Цена производства"))],
        [InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_products_edit"))]
    ]
    return InlineKeyboardMarkup(keyboard)


def product_delete_select_keyboard(user_id: int, items: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора изделия для удаления"""
    keyboard = []
    
    for item in items:
        keyboard.append([InlineKeyboardButton(
            f"❌ {item['name']} ({item['code']})",
            callback_data=make_callback(user_id, "admin_prod_delete", item['code'])
        )])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_products_delete_page", str(page-1))))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_products_delete_page", str(page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_products"))])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== УЗЛЫ ====================

def nodes_list_keyboard(user_id: int, items: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура для списка узлов"""
    keyboard = []
    
    keyboard.append([InlineKeyboardButton("➕ Добавить узел", callback_data=make_callback(user_id, "admin_nodes_add"))])
    
    if items:
        keyboard.append([InlineKeyboardButton("✏️ Редактировать", callback_data=make_callback(user_id, "admin_nodes_edit"))])
        keyboard.append([InlineKeyboardButton("🗑️ Удалить", callback_data=make_callback(user_id, "admin_nodes_delete"))])
    
    keyboard.append([InlineKeyboardButton("🔍 Поиск", callback_data=make_callback(user_id, "admin_nodes_search"))])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_nodes_page", str(page-1))))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_nodes_page", str(page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data=make_callback(user_id, "admin_back_to_main"))])
    
    return InlineKeyboardMarkup(keyboard)


def node_category_select_keyboard(user_id: int, paths: list, prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора категории для узла"""
    keyboard = []
    
    for path in paths[:15]:
        short_path = path[:30] + "..." if len(path) > 30 else path
        keyboard.append([InlineKeyboardButton(
            f"📁 {short_path}",
            callback_data=make_callback(user_id, f"admin_{prefix}_cat", path)
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_nodes"))])
    
    return InlineKeyboardMarkup(keyboard)


def node_edit_select_keyboard(user_id: int, items: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора узла для редактирования"""
    keyboard = []
    
    for item in items:
        keyboard.append([InlineKeyboardButton(
            f"🔧 {item['name']} ({item['code']})",
            callback_data=make_callback(user_id, "admin_node_edit", item['code'])
        )])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_nodes_edit_page", str(page-1))))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_nodes_edit_page", str(page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_nodes"))])
    
    return InlineKeyboardMarkup(keyboard)


def node_edit_field_keyboard(user_id: int, code: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора поля для редактирования узла"""
    keyboard = [
        [InlineKeyboardButton("📝 Название", callback_data=make_callback(user_id, f"admin_node_field", f"{code}_Наименование"))],
        [InlineKeyboardButton("📂 Категория", callback_data=make_callback(user_id, f"admin_node_field", f"{code}_Категории"))],
        [InlineKeyboardButton("🔢 Кратность", callback_data=make_callback(user_id, f"admin_node_field", f"{code}_Кратность"))],
        [InlineKeyboardButton("💰 Цена производства", callback_data=make_callback(user_id, f"admin_node_field", f"{code}_Цена производства"))],
        [InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_nodes_edit"))]
    ]
    return InlineKeyboardMarkup(keyboard)


def node_delete_select_keyboard(user_id: int, items: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора узла для удаления"""
    keyboard = []
    
    for item in items:
        keyboard.append([InlineKeyboardButton(
            f"❌ {item['name']} ({item['code']})",
            callback_data=make_callback(user_id, "admin_node_delete", item['code'])
        )])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_nodes_delete_page", str(page-1))))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_nodes_delete_page", str(page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_nodes"))])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== МАТЕРИАЛЫ ====================

def materials_list_keyboard(user_id: int, items: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура для списка материалов"""
    keyboard = []
    
    keyboard.append([InlineKeyboardButton("➕ Добавить материал", callback_data=make_callback(user_id, "admin_materials_add"))])
    
    if items:
        keyboard.append([InlineKeyboardButton("✏️ Редактировать", callback_data=make_callback(user_id, "admin_materials_edit"))])
        keyboard.append([InlineKeyboardButton("🗑️ Удалить", callback_data=make_callback(user_id, "admin_materials_delete"))])
    
    keyboard.append([InlineKeyboardButton("🔍 Поиск", callback_data=make_callback(user_id, "admin_materials_search"))])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_materials_page", str(page-1))))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_materials_page", str(page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data=make_callback(user_id, "admin_back_to_main"))])
    
    return InlineKeyboardMarkup(keyboard)


def material_category_select_keyboard(user_id: int, paths: list, prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора категории для материала"""
    keyboard = []
    
    for path in paths[:15]:
        short_path = path[:30] + "..." if len(path) > 30 else path
        keyboard.append([InlineKeyboardButton(
            f"📁 {short_path}",
            callback_data=make_callback(user_id, f"admin_{prefix}_cat", path)
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_materials"))])
    
    return InlineKeyboardMarkup(keyboard)


def material_edit_select_keyboard(user_id: int, items: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора материала для редактирования"""
    keyboard = []
    
    for item in items:
        keyboard.append([InlineKeyboardButton(
            f"🧱 {item['name']} ({item['code']})",
            callback_data=make_callback(user_id, "admin_mat_edit", item['code'])
        )])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_materials_edit_page", str(page-1))))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_materials_edit_page", str(page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_materials"))])
    
    return InlineKeyboardMarkup(keyboard)


def material_edit_field_keyboard(user_id: int, code: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора поля для редактирования материала"""
    keyboard = [
        [InlineKeyboardButton("📝 Название", callback_data=make_callback(user_id, f"admin_mat_field", f"{code}_Наименование"))],
        [InlineKeyboardButton("📂 Категория", callback_data=make_callback(user_id, f"admin_mat_field", f"{code}_Категории"))],
        [InlineKeyboardButton("💰 Цена", callback_data=make_callback(user_id, f"admin_mat_field", f"{code}_Цена производства"))],
        [InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_materials_edit"))]
    ]
    return InlineKeyboardMarkup(keyboard)


def material_delete_select_keyboard(user_id: int, items: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора материала для удаления"""
    keyboard = []
    
    for item in items:
        keyboard.append([InlineKeyboardButton(
            f"❌ {item['name']} ({item['code']})",
            callback_data=make_callback(user_id, "admin_mat_delete", item['code'])
        )])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_materials_delete_page", str(page-1))))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_materials_delete_page", str(page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_materials"))])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== СПЕЦИФИКАЦИИ ====================

def spec_parent_select_keyboard(user_id: int, items: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора родителя для спецификаций"""
    keyboard = []
    
    for item in items:
        icon = "🏗️" if item['type'] == 'изделие' else "🔩"
        keyboard.append([InlineKeyboardButton(
            f"{icon} {item['name']} ({item['code']})",
            callback_data=make_callback(user_id, "admin_spec_parent", item['code'])
        )])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_spec_page", str(page-1))))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_spec_page", str(page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data=make_callback(user_id, "admin_back_to_main"))])
    
    return InlineKeyboardMarkup(keyboard)


def spec_menu_keyboard(user_id: int, parent_code: str, parent_type: str) -> InlineKeyboardMarkup:
    """Меню управления спецификациями"""
    keyboard = []
    
    if parent_type in ['изделие', 'узел']:
        keyboard.append([InlineKeyboardButton(
            "🔩 Привязать узел",
            callback_data=make_callback(user_id, "admin_spec_link_node", parent_code)
        )])
    
    keyboard.append([InlineKeyboardButton(
        "🧱 Привязать материал",
        callback_data=make_callback(user_id, "admin_spec_link_material", parent_code)
    )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_spec"))])
    
    return InlineKeyboardMarkup(keyboard)


def spec_node_select_keyboard(user_id: int, parent_code: str, nodes: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора узла для привязки"""
    keyboard = []
    
    for node in nodes:
        keyboard.append([InlineKeyboardButton(
            f"🔩 {node['name']} ({node['code']})",
            callback_data=make_callback(user_id, "admin_spec_node_select", f"{parent_code}_{node['code']}")
        )])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_spec_node_page", f"{parent_code}_{page-1}")))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_spec_node_page", f"{parent_code}_{page+1}")))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, f"admin_spec_parent_{parent_code}"))])
    
    return InlineKeyboardMarkup(keyboard)


def spec_material_select_keyboard(user_id: int, parent_code: str, materials: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора материала для привязки"""
    keyboard = []
    
    for material in materials:
        keyboard.append([InlineKeyboardButton(
            f"🧱 {material['name']} ({material['code']})",
            callback_data=make_callback(user_id, "admin_spec_mat_select", f"{parent_code}_{material['code']}")
        )])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_spec_mat_page", f"{parent_code}_{page-1}")))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_spec_mat_page", f"{parent_code}_{page+1}")))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, f"admin_spec_parent_{parent_code}"))])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== АДМИНИСТРАТОРЫ ====================

def admins_list_keyboard(user_id: int, admins: list) -> InlineKeyboardMarkup:
    """Клавиатура для списка администраторов"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить администратора", callback_data=make_callback(user_id, "admin_admins_add"))],
    ]
    
    if admins:
        keyboard.append([InlineKeyboardButton("🗑️ Удалить администратора", callback_data=make_callback(user_id, "admin_admins_delete"))])
        
        for admin in admins:
            if admin.get('is_active', 1) == 1:
                keyboard.append([InlineKeyboardButton(
                    f"❌ Деактивировать {admin['user_id']}",
                    callback_data=make_callback(user_id, "admin_admins_toggle", str(admin['user_id']))
                )])
            else:
                keyboard.append([InlineKeyboardButton(
                    f"✅ Активировать {admin['user_id']}",
                    callback_data=make_callback(user_id, "admin_admins_toggle", str(admin['user_id']))
                )])
    
    keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data=make_callback(user_id, "admin_back_to_main"))])
    
    return InlineKeyboardMarkup(keyboard)


def admin_delete_select_keyboard(user_id: int, admins: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора администратора для удаления"""
    keyboard = []
    
    for admin in admins:
        keyboard.append([InlineKeyboardButton(
            f"❌ ID: {admin['user_id']} — {admin.get('first_name', '—')}",
            callback_data=make_callback(user_id, "admin_admins_remove", str(admin['user_id']))
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "admin_admins"))])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== ПОИСК ====================

def search_results_keyboard(user_id: int, items: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура для результатов поиска"""
    keyboard = []
    
    for item in items:
        icon = "🏗️" if item['type'] == 'изделие' else ("🔩" if item['type'] == 'узел' else "🧱")
        keyboard.append([InlineKeyboardButton(
            f"{icon} {item['name']}",
            callback_data=make_callback(user_id, "admin_search_item", item['code'])
        )])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_search_page", str(page-1))))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_search_page", str(page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔍 Новый поиск", callback_data=make_callback(user_id, "admin_search"))])
    keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data=make_callback(user_id, "admin_back_to_main"))])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== МЕНЮ ПРИВЯЗКИ ДЛЯ ИЗДЕЛИЯ ====================

def product_link_menu_keyboard(user_id: int, product_code: str) -> InlineKeyboardMarkup:
    """Меню привязки компонентов к изделию"""
    keyboard = [
        [InlineKeyboardButton(
            "🔩 Привязать существующий узел",
            callback_data=make_callback(user_id, "admin_prod_link_node", product_code)
        )],
        [InlineKeyboardButton(
            "🧱 Привязать существующий материал",
            callback_data=make_callback(user_id, "admin_prod_link_material", product_code)
        )],
        [InlineKeyboardButton(
            "➕ Создать новый узел",
            callback_data=make_callback(user_id, "admin_prod_create_node", product_code)
        )],
        [InlineKeyboardButton(
            "➕ Создать новый материал",
            callback_data=make_callback(user_id, "admin_prod_create_material", product_code)
        )],
        [InlineKeyboardButton(
            "✅ Завершить настройку",
            callback_data=make_callback(user_id, "admin_prod_finish", product_code)
        )]
    ]
    return InlineKeyboardMarkup(keyboard)


def product_select_nodes_keyboard(user_id: int, nodes: list, page: int, total_pages: int, selected: set) -> InlineKeyboardMarkup:
    """Клавиатура множественного выбора узлов"""
    keyboard = []
    
    for node in nodes:
        checkbox = "☑️" if node['code'] in selected else "☐"
        keyboard.append([InlineKeyboardButton(
            f"{checkbox} {node['name']} ({node['code']})",
            callback_data=make_callback(user_id, "admin_prod_toggle_node", node['code'])
        )])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_prod_nodes_page", str(page-1))))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_prod_nodes_page", str(page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton(
        "✅ Подтвердить выбор",
        callback_data=make_callback(user_id, "admin_prod_confirm_nodes")
    )])
    keyboard.append([InlineKeyboardButton(
        "🔙 Назад",
        callback_data=make_callback(user_id, "admin_prod_back_to_link_menu")
    )])
    
    return InlineKeyboardMarkup(keyboard)


def product_select_materials_keyboard(user_id: int, materials: list, page: int, total_pages: int, selected: set) -> InlineKeyboardMarkup:
    """Клавиатура множественного выбора материалов"""
    keyboard = []
    
    for mat in materials:
        checkbox = "☑️" if mat['code'] in selected else "☐"
        keyboard.append([InlineKeyboardButton(
            f"{checkbox} {mat['name']} ({mat['code']})",
            callback_data=make_callback(user_id, "admin_prod_toggle_material", mat['code'])
        )])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_prod_materials_page", str(page-1))))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_prod_materials_page", str(page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton(
        "✅ Подтвердить выбор",
        callback_data=make_callback(user_id, "admin_prod_confirm_materials")
    )])
    keyboard.append([InlineKeyboardButton(
        "🔙 Назад",
        callback_data=make_callback(user_id, "admin_prod_back_to_link_menu")
    )])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== МЕНЮ ПРИВЯЗКИ ДЛЯ УЗЛА ====================

def node_link_menu_keyboard(user_id: int, node_code: str) -> InlineKeyboardMarkup:
    """Меню привязки материалов к узлу"""
    keyboard = [
        [InlineKeyboardButton(
            "🧱 Привязать существующий материал",
            callback_data=make_callback(user_id, "admin_node_link_material", node_code)
        )],
        [InlineKeyboardButton(
            "➕ Создать новый материал",
            callback_data=make_callback(user_id, "admin_node_create_material", node_code)
        )],
        [InlineKeyboardButton(
            "✅ Завершить настройку",
            callback_data=make_callback(user_id, "admin_node_finish", node_code)
        )]
    ]
    return InlineKeyboardMarkup(keyboard)


def node_select_materials_keyboard(user_id: int, materials: list, page: int, total_pages: int, selected: set) -> InlineKeyboardMarkup:
    """Клавиатура множественного выбора материалов для узла"""
    keyboard = []
    
    for mat in materials:
        checkbox = "☑️" if mat['code'] in selected else "☐"
        keyboard.append([InlineKeyboardButton(
            f"{checkbox} {mat['name']} ({mat['code']})",
            callback_data=make_callback(user_id, "admin_node_toggle_material", mat['code'])
        )])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "admin_node_materials_page", str(page-1))))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "admin_node_materials_page", str(page+1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton(
        "✅ Подтвердить выбор",
        callback_data=make_callback(user_id, "admin_node_confirm_materials")
    )])
    keyboard.append([InlineKeyboardButton(
        "🔙 Назад",
        callback_data=make_callback(user_id, "admin_node_back_to_link_menu")
    )])
    
    return InlineKeyboardMarkup(keyboard)
