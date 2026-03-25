from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import hashlib

def make_callback(user_id: int, action: str, data: str = "") -> str:
    """Создаёт callback_data с проверкой длины"""
    if data:
        base = f"user_{user_id}_{action}_{data}"
    else:
        base = f"user_{user_id}_{action}"
    
    if len(base.encode()) <= 64:
        return base
    
    # Если длинно, берём хэш
    data_hash = hashlib.md5(data.encode()).hexdigest()[:8]
    return f"user_{user_id}_{action}_{data_hash}"


def cancel_button(user_id: int) -> InlineKeyboardMarkup:
    """Кнопка отмены"""
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))]]
    return InlineKeyboardMarkup(keyboard)


def back_button(user_id: int, to: str) -> InlineKeyboardMarkup:
    """Кнопка назад"""
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=make_callback(user_id, f"back_to_{to}"))],
        [InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))]
    ]
    return InlineKeyboardMarkup(keyboard)


def mode_selection_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора режима (калькулятор)"""
    keyboard = [
        [InlineKeyboardButton("🧮 Одиночный расчёт", callback_data=make_callback(user_id, "single_mode"))],
        [InlineKeyboardButton("📊 Множественный расчёт", callback_data=make_callback(user_id, "multi_mode"))],
        [InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))]
    ]
    return InlineKeyboardMarkup(keyboard)


def categories_keyboard(categories: list, user_id: int, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура списка категорий"""
    keyboard = []
    
    for cat in categories:
        cat_short = cat[:20]
        keyboard.append([InlineKeyboardButton(
            f"📁 {cat}",
            callback_data=make_callback(user_id, "cat", cat_short)
        )])
    
    # Навигация
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "categories_page", str(page - 1))))
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "categories_page", str(page + 1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))])
    
    return InlineKeyboardMarkup(keyboard)


def products_keyboard(products: list, user_id: int, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура списка изделий"""
    keyboard = []
    
    for p in products:
        name = p['name'][:30] + "..." if len(p['name']) > 30 else p['name']
        keyboard.append([InlineKeyboardButton(
            f"{name}",
            callback_data=make_callback(user_id, "product", p['code'])
        )])
    
    # Навигация
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "products_page", str(page - 1))))
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "products_page", str(page + 1))))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data=make_callback(user_id, "back_to_categories"))])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))])
    
    return InlineKeyboardMarkup(keyboard)


def materials_keyboard(materials: list, user_id: int, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура списка материалов (после расчёта)"""
    keyboard = []
    
    # Кнопки для постраничного просмотра материалов
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=make_callback(user_id, "materials_page", str(page - 1))))
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=make_callback(user_id, "materials_page", str(page + 1))))
    if nav_row:
        keyboard.append(nav_row)
    
    # Основные кнопки
    keyboard.append([InlineKeyboardButton("✏️ Ввод цен", callback_data=make_callback(user_id, "price_input"))])
    keyboard.append([InlineKeyboardButton("🤖 Автоматически", callback_data=make_callback(user_id, "auto_prices"))])
    keyboard.append([InlineKeyboardButton("🔙 Назад к выбору изделия", callback_data=make_callback(user_id, "back_to_products"))])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=make_callback(user_id, "cancel"))])
    
    return InlineKeyboardMarkup(keyboard)


def result_keyboard(user_id: int, has_next: bool = False, has_prev: bool = False, is_single: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура результатов"""
    keyboard = []
    
    if not is_single:
        nav_row = []
        if has_prev:
            nav_row.append(InlineKeyboardButton("◀️ Предыдущее", callback_data=make_callback(user_id, "prev_detail")))
        if has_next:
            nav_row.append(InlineKeyboardButton("Следующее ▶️", callback_data=make_callback(user_id, "next_detail")))
        if nav_row:
            keyboard.append(nav_row)
        
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
