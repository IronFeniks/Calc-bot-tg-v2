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

def main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Главное меню админки"""
    keyboard = [
        [InlineKeyboardButton("📋 Категории", callback_data=make_callback(user_id, "categories"))],
        [InlineKeyboardButton("🏗️ Изделия", callback_data=make_callback(user_id, "products"))],
        [InlineKeyboardButton("🔩 Узлы", callback_data=make_callback(user_id, "nodes"))],
        [InlineKeyboardButton("⚙️ Материалы", callback_data=make_callback(user_id, "materials"))],
        [InlineKeyboardButton("👥 Администраторы", callback_data=make_callback(user_id, "admins"))],
        [InlineKeyboardButton("🚪 Выход", callback_data=make_callback(user_id, "exit"))]
    ]
    return InlineKeyboardMarkup(keyboard)
