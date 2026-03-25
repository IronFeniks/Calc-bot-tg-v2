from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import hashlib

def make_callback(user_id: int, action: str, data: str = "") -> str:
    """
    Создаёт callback_data с проверкой длины (Telegram лимит 64 байта)
    
    Args:
        user_id: ID пользователя
        action: действие
        data: дополнительные данные
    
    Returns:
        строка для callback_data
    """
    if data:
        base = f"user_{user_id}_{action}_{data}"
    else:
        base = f"user_{user_id}_{action}"
    
    if len(base.encode()) <= 64:
        return base
    
    # Если длинно, берём хэш от данных
    data_hash = hashlib.md5(data.encode()).hexdigest()[:8]
    return f"user_{user_id}_{action}_{data_hash}"


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
    
    Args:
        user_id: ID пользователя
        page: текущая страница
        total_pages: всего страниц
        action: действие для callback (например, "categories_page")
    
    Returns:
        список кнопок для строки
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
    """
    Клавиатура списка категорий
    
    Args:
        categories: список категорий на текущей странице
        user_id: ID пользователя
        page: текущая страница
        total_pages: всего страниц
    """
    keyboard = []
    
    for cat in categories:
        cat_short = cat[:20]  # Обрезаем для callback
        keyboard.append([InlineKeyboardButton(
            f"📁 {cat}",
            callback_data=make_callback(user_id, "cat", cat_short)
        )])
    
    # Навигация
    nav_row = navigation_buttons(user_id, page, total_pages, "categories_page")
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== ИЗДЕЛИЯ (ОДИНОЧНЫЙ РЕЖИМ) ====================

def products_keyboard(products: list, user_id: int, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """
    Клавиатура списка изделий для одиночного режима
    
    Args:
        products: список изделий на текущей странице
        user_id: ID пользователя
        page: текущая страница
        total_pages: всего страниц
    """
    keyboard = []
    
    for p in products:
        name = p['name'][:30] + "..." if len(p['name']) > 30 else p['name']
        keyboard.append([InlineKeyboardButton(
            f"{name}",
            callback_data=make_callback(user_id, "select_product", p['name'])
        )])
    
    # Навигация
    nav_row = navigation_buttons(user_id, page, total_pages, "products_page")
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data=make_callback(user_id, "back_to_categories"))])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== ИЗДЕЛИЯ (МНОЖЕСТВЕННЫЙ РЕЖИМ) ====================

def multi_select_products_keyboard(products: list, user_id: int, page: int, total_pages: int, selected: set) -> InlineKeyboardMarkup:
    """
    Клавиатура списка изделий с чекбоксами для множественного режима
    
    Args:
        products: список изделий на текущей странице
        user_id: ID пользователя
        page: текущая страница
        total_pages: всего страниц
        selected: множество выбранных названий
    """
    keyboard = []
    
    for p in products:
        name = p['name'][:30] + "..." if len(p['name']) > 30 else p['name']
        checkbox = "☑️" if name in selected else "☐"
        keyboard.append([InlineKeyboardButton(
            f"{checkbox} {name}",
            callback_data=make_callback(user_id, "toggle_product", p['name'])
        )])
    
    # Навигация
    nav_row = navigation_buttons(user_id, page, total_pages, "multi_products_page")
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("✅ Подтвердить выбор", callback_data=make_callback(user_id, "confirm_products"))])
    keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data=make_callback(user_id, "back_to_categories"))])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== МАТЕРИАЛЫ ====================

def materials_keyboard(materials: list, user_id: int, page: int, total_pages: int, mode: str = "single") -> InlineKeyboardMarkup:
    """
    Клавиатура списка материалов
    
    Args:
        materials: список материалов
        user_id: ID пользователя
        page: текущая страница
        total_pages: всего страниц
        mode: "single" или "multi"
    """
    keyboard = []
    
    # Кнопки для постраничного просмотра материалов
    nav_row = navigation_buttons(user_id, page, total_pages, "materials_page")
    if nav_row:
        keyboard.append(nav_row)
    
    # Основные кнопки
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
    """
    Клавиатура для страницы результатов
    
    Args:
        user_id: ID пользователя
        is_multi: множественный ли режим
        current_index: текущий индекс изделия (для множественного режима)
        total_count: общее количество изделий (для множественного режима)
    """
    keyboard = []
    
    if is_multi and total_count > 0:
        nav_row = []
        if current_index > 0:
            nav_row.append(InlineKeyboardButton("◀️ Предыдущее", callback_data=make_callback(user_id, "prev_detail")))
        if current_index < total_count - 1:
            nav_row.append(InlineKeyboardButton("Следующее ▶️", callback_data=make_callback(user_id, "next_detail")))
        if nav_row:
            keyboard.append(nav_row)
        
        if current_index != -1:  # -1 означает общую сводку
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


# ==================== ПОМОЩЬ ====================

def help_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для возврата из помощи"""
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, "back_to_start"))]
    ]
    return InlineKeyboardMarkup(keyboard)
