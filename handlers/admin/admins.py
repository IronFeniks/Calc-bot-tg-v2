import logging
from telegram import CallbackQuery
from keyboards.admin import admins_list_keyboard, back_to_main_button
from excel_handler import get_excel_handler
from config import MASTER_ADMIN_ID

logger = logging.getLogger(__name__)


async def show_admins_list(query: CallbackQuery, user_id: int):
    """Показывает список администраторов"""
    # Проверяем, что пользователь - главный админ
    if user_id != MASTER_ADMIN_ID:
        await query.answer("⛔ Только главный администратор может управлять администраторами", show_alert=True)
        return
    
    excel = get_excel_handler()
    admins = excel.get_all_admins()
    
    text = "👥 АДМИНИСТРАТОРЫ\n\n"
    
    if not admins:
        text += "Нет администраторов.\n"
    else:
        for admin in admins:
            status = "✅ Активен" if admin.get('is_active', 1) == 1 else "❌ Неактивен"
            text += f"• ID: {admin['user_id']}\n"
            text += f"  Имя: {admin.get('first_name', '—')}\n"
            text += f"  Username: @{admin.get('username', '—')}\n"
            text += f"  Статус: {status}\n"
            text += f"  Добавлен: {admin.get('added_at', '—')}\n\n"
    
    text += "\nВыберите действие:"
    
    await query.edit_message_text(
        text,
        reply_markup=admins_list_keyboard(user_id, admins)
    )


async def add_admin_start(query: CallbackQuery, user_id: int):
    """Запрашивает ID нового администратора"""
    if user_id != MASTER_ADMIN_ID:
        await query.answer("⛔ Только главный администратор может добавлять администраторов", show_alert=True)
        return
    
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.ADMIN_ADD_ID
    
    await query.edit_message_text(
        "👥 ДОБАВЛЕНИЕ АДМИНИСТРАТОРА\n\n"
        "Введите Telegram ID пользователя:\n"
        "(число, можно узнать через @userinfobot)\n\n"
        "Или нажмите Отмена",
        reply_markup=back_to_main_button(user_id)
    )


async def add_admin_save(update, user_id: int, text: str):
    """Сохраняет нового администратора"""
    from .router import clear_admin_session
    from keyboards.admin import main_menu_keyboard
    from utils.validators import validate_user_id
    
    admin_id = validate_user_id(text)
    if admin_id is None:
        await update.message.reply_text(
            "❌ Введите корректный Telegram ID (положительное число).",
            reply_markup=back_to_main_button(user_id)
        )
        return
    
    excel = get_excel_handler()
    success, message = excel.add_admin(admin_id, '', '', user_id)
    
    clear_admin_session(user_id)
    
    await update.message.reply_text(
        f"{message}\n\nЧто делаем дальше?",
        reply_markup=main_menu_keyboard(user_id)
    )


async def delete_admin_confirm(query: CallbackQuery, user_id: int):
    """Показывает список администраторов для удаления"""
    if user_id != MASTER_ADMIN_ID:
        await query.answer("⛔ Только главный администратор может удалять администраторов", show_alert=True)
        return
    
    excel = get_excel_handler()
    admins = excel.get_all_admins()
    
    # Фильтруем главного админа
    admins = [a for a in admins if a['user_id'] != MASTER_ADMIN_ID]
    
    if not admins:
        await query.answer("❌ Нет администраторов для удаления", show_alert=True)
        return
    
    text = "🗑️ УДАЛЕНИЕ АДМИНИСТРАТОРА\n\n"
    text += "Выберите администратора для удаления:\n\n"
    
    for admin in admins:
        text += f"• ID: {admin['user_id']} — {admin.get('first_name', '—')}\n"
    
    from keyboards.admin import admin_delete_select_keyboard
    await query.edit_message_text(
        text,
        reply_markup=admin_delete_select_keyboard(user_id, admins)
    )


async def delete_admin_execute(query: CallbackQuery, user_id: int, admin_id: int):
    """Удаляет администратора"""
    if user_id != MASTER_ADMIN_ID:
        await query.answer("⛔ Нет доступа", show_alert=True)
        return
    
    from keyboards.admin import main_menu_keyboard
    
    excel = get_excel_handler()
    success, message = excel.remove_admin(admin_id)
    
    if success:
        await query.edit_message_text(
            f"✅ Администратор {admin_id} удалён.\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        await query.edit_message_text(
            f"{message}\n\nЧто делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )


async def toggle_admin_execute(query: CallbackQuery, user_id: int, admin_id: int):
    """Переключает статус администратора (активен/неактивен)"""
    if user_id != MASTER_ADMIN_ID:
        await query.answer("⛔ Нет доступа", show_alert=True)
        return
    
    excel = get_excel_handler()
    success, message = excel.toggle_admin(admin_id)
    
    if success:
        await query.answer(message, show_alert=True)
        # Обновляем список
        await show_admins_list(query, user_id)
    else:
        await query.answer(message, show_alert=True)
