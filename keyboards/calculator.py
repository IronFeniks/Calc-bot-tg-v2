from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import hashlib

# Словарь для хранения маппинга хэшей к оригинальным данным
# Формат: {user_id: {hash: original_value}}
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
    """
    Создаёт callback_data с проверкой длины (Telegram лимит 64 байта)
    Если данные длинные, заменяет их на хэш и сохраняет маппинг
    """
    if data:
        base = f"user_{user_id}_{action}_{data}"
    else:
        base = f"user_{user_id}_{action}"
    
    if len(base.encode()) <= 64:
        return base
    
    # Если длинно, берём хэш от данных
    data_hash = hashlib.md5(data.encode()).hexdigest()[:8]
    
    # Сохраняем маппинг для восстановления
    mapping = get_hash_mapping(user_id)
    mapping[data_hash] = data
    
    return f"user_{user_id}_{action}_{data_hash}"


def restore_callback_data(user_id: int, action: str, data_hash: str) -> str:
    """
    Восстанавливает оригинальные данные из хэша
    """
    mapping = get_hash_mapping(user_id)
    if data_hash in mapping:
        return mapping[data_hash]
    return data_hash


def clear_user_mapping(user_id: int):
    """Очищает маппинг для пользователя (при завершении сессии)"""
    clear_hash_mapping(user_id)


# ==================== БАЗОВЫЕ КНОПКИ ====================

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


def navigation_buttons(user_id: int, page: int, total_pages: int, action: str) -> list:
    """
    Создаёт строку навигационных кнопок
    """
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, action, str(page - 1))))
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, action, str(page + 1))))
    return nav_row


# ==================== ГЛАВНОЕ МЕНЮ ====================

def mode_selection_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора режима расчёта"""
    keyboard = [
        [InlineKeyboardButton("🧮 Одиночный расчёт", callback_data=make_callback(user_id, "single_mode"))],
        [InlineKeyboardButton("📊 Множественный расчёт", callback_data=make_callback(user_id, "multi_mode"))],
        [InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))]
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== КАТЕГОРИИ ====================

def categories_keyboard(categories: list, user_id: int, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура списка категорий"""
    keyboard = []
    
    for cat in categories:
        cat_short = cat[:20]
        keyboard.append([InlineKeyboardButton(
            f"📁 {cat}",
            callback_data=make_callback(user_id, "cat", cat_short)
        )])
    
    nav_row = navigation_buttons(user_id, page, total_pages, "categories_page")
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== ИЗДЕЛИЯ (ОДИНОЧНЫЙ РЕЖИМ) ====================

def products_keyboard(products: list, user_id: int, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура списка изделий для одиночного режима"""
    keyboard = []
    
    for p in products:
        name = p['name'][:30] + "..." if len(p['name']) > 30 else p['name']
        # Передаём полное название, make_callback сам обработает длину
        keyboard.append([InlineKeyboardButton(
            f"{name}",
            callback_data=make_callback(user_id, "select_product", p['name'])
        )])
    
    nav_row = navigation_buttons(user_id, page, total_pages, "products_page")
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data=make_callback(user_id, "back_to_categories"))])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== ИЗДЕЛИЯ (МНОЖЕСТВЕННЫЙ РЕЖИМ) ====================

def multi_select_products_keyboard(products: list, user_id: int, page: int, total_pages: int, selected: set) -> InlineKeyboardMarkup:
    """Клавиатура списка изделий с чекбоксами для множественного режима"""
    keyboard = []
    
    for p in products:
        name = p['name'][:30] + "..." if len(p['name']) > 30 else p['name']
        checkbox = "☑️" if name in selected else "☐"
        # Передаём полное название, make_callback сам обработает длину
        keyboard.append([InlineKeyboardButton(
            f"{checkbox} {name}",
            callback_data=make_callback(user_id, "toggle_product", p['name'])
        )])
    
    nav_row = navigation_buttons(user_id, page, total_pages, "multi_products_page")
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("✅ Подтвердить выбор", callback_data=make_callback(user_id, "confirm_products"))])
    keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data=make_callback(user_id, "back_to_categories"))])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== МАТЕРИАЛЫ ====================

def materials_keyboard(materials: list, user_id: int, page: int, total_pages: int, mode: str = "single") -> InlineKeyboardMarkup:
    """Клавиатура списка материалов"""
    keyboard = []
    
    nav_row = navigation_buttons(user_id, page, total_pages, "materials_page")
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("✏️ Ввод цен", callback_data=make_callback(user_id, "price_input"))])
    keyboard.append([InlineKeyboardButton("🤖 Автоматически", callback_data=make_callback(user_id, "auto_prices"))])
    
    if mode == "single":
        keyboard.append([InlineKeyboardButton("🔙 Назад к выбору изделия", callback_data=make_callback(user_id, "back_to_products"))])
    else:
        keyboard.append([InlineKeyboardButton("🔙 Назад к выбору изделий", callback_data=make_callback(user_id, "back_to_multi_select"))])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))])
    
    return InlineKeyboardMarkup(keyboard)


def missing_prices_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для выбора действий при отсутствии цен"""
    keyboard = [
        [InlineKeyboardButton("▶️ Продолжить с имеющимися ценами", callback_data=make_callback(user_id, "continue"))],
        [InlineKeyboardButton("✏️ Ввести недостающие", callback_data=make_callback(user_id, "price_input_missing"))],
        [InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))]
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== РЕЗУЛЬТАТЫ ====================

def result_keyboard(user_id: int, is_multi: bool = False, 
                    current_index: int = 0, total_count: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура для страницы результатов"""
    keyboard = []
    
    if is_multi and total_count > 0:
        nav_row = []
        if current_index > 0:
            nav_row.append(InlineKeyboardButton("◀️ Предыдущее", callback_data=make_callback(user_id, "prev_detail")))
        if current_index < total_count - 1:
            nav_row.append(InlineKeyboardButton("Следующее ▶️", callback_data=make_callback(user_id, "next_detail")))
        if nav_row:
            keyboard.append(nav_row)
        
        if current_index != -1:
            keyboard.append([InlineKeyboardButton("📊 Общая сводка", callback_data=make_callback(user_id, "total_summary"))])
    
    keyboard.append([InlineKeyboardButton("🔄 Новый расчёт в этой категории", callback_data=make_callback(user_id, "same_category"))])
    keyboard.append([InlineKeyboardButton("📖 Пояснить", callback_data=make_callback(user_id, "explain"))])
    keyboard.append([InlineKeyboardButton("❌ Завершить", callback_data=make_callback(user_id, "cancel"))])
    
    return InlineKeyboardMarkup(keyboard)


def explanation_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для возврата из пояснения"""
    keyboard = [
        [InlineKeyboardButton("🔙 Назад к результатам", callback_data=make_callback(user_id, "back_to_result"))]
    ]
    return InlineKeyboardMarkup(keyboard)


def help_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для возврата из помощи"""
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "back_to_start"))]
    ]
    return InlineKeyboardMarkup(keyboard)
