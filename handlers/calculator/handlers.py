import logging
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from keyboards.calculator import mode_selection_keyboard, cancel_button, back_button, categories_keyboard
from .instructions import INSTRUCTION_TOPIC, INSTRUCTION_PRIVATE, INSTRUCTION_ADMIN
from .session import get_session, clear_session
from .categories import show_categories, select_category, back_to_categories
from .products import show_products, select_product_by_number, select_product_by_name, show_multi_products, toggle_product, confirm_products
from .parameters import process_efficiency, process_tax, process_multi_efficiency, process_multi_tax
from .quantity_prices import (
    process_quantity, process_market_price, process_drawing_price,
    process_multi_quantity, process_multi_market_price, process_multi_drawing_price
)
from .materials import (
    start_price_input, auto_prices, input_missing_prices,
    process_price_input_value, process_missing_price_value,
    _show_materials_list
)
from .results import (
    calculate_final_result, next_detail, prev_detail,
    back_to_total_summary, back_to_result, same_category, show_explanation
)
from excel_handler import get_excel_handler
from handlers.auth import is_admin

logger = logging.getLogger(__name__)


async def start_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE, is_topic: bool, lock=None):
    """Запуск калькулятора"""
    user_id = update.effective_user.id
    
    if is_topic and lock and lock.is_locked() and lock.current_user != user_id:
        lock_info = lock.get_lock_info()
        name = lock_info['first_name'] or f"@{lock_info['username']}" if lock_info['username'] else f"ID {lock_info['user_id']}"
        await update.message.reply_text(
            f"⏳ *Бот занят*\n\nСейчас расчёты выполняет: *{name}*",
            parse_mode='Markdown'
        )
        return
    
    if is_topic and lock:
        if not lock.acquire(user_id, update.effective_user.username, update.effective_user.first_name):
            await update.message.reply_text("❌ Не удалось начать расчёт. Попробуйте позже.")
            return
    
    clear_session(user_id)
    session = get_session(user_id)
    
    excel = get_excel_handler()
    if excel:
        tree = excel.get_category_tree()
        session['category_tree'] = tree
    
    if is_topic:
        instruction = INSTRUCTION_TOPIC
    else:
        if is_admin(user_id):
            instruction = INSTRUCTION_ADMIN
        else:
            instruction = INSTRUCTION_PRIVATE
    
    await update.message.reply_text(
        instruction,
        reply_markup=mode_selection_keyboard(user_id),
        parse_mode='Markdown'
    )


async def select_mode(query, user_id: int, mode: str):
    """Обработка выбора режима"""
    session = get_session(user_id)
    session['mode'] = mode
    session['step'] = 'categories'
    session['category_path'] = []
    
    tree = session.get('category_tree', {})
    categories = list(tree.keys())
    
    if categories:
        total_pages = (len(categories) + 9) // 10
        page_categories = categories[:10]
        
        await query.edit_message_text(
            "📂 ВЫБОР КАТЕГОРИИ\n\nДоступные категории:",
            reply_markup=categories_keyboard(page_categories, user_id, 1, total_pages)
        )
    else:
        await query.edit_message_text(
            "❌ Нет доступных категорий",
            reply_markup=cancel_button(user_id)
        )


async def calculator_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, is_topic: bool, lock=None):
    """Обработчик текстовых сообщений в калькуляторе"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    session = get_session(user_id)
    step = session.get('step')
    
    if is_topic and lock and lock.current_user == user_id:
        lock.refresh(user_id)
    
    logger.info(f"📝 Текстовый ввод от {user_id}: '{text}', шаг={step}, режим={session.get('mode')}")
    
    # ==================== ОДИНОЧНЫЙ РЕЖИМ ====================
    if step == 'efficiency':
        await process_efficiency(update, context, user_id, text)
        return
    elif step == 'tax':
        await process_tax(update, context, user_id, text)
        return
    elif step == 'quantity':
        await process_quantity(update, context, user_id, text)
        return
    elif step == 'market_price':
        await process_market_price(update, context, user_id, text)
        return
    elif step == 'drawing_price':
        await process_drawing_price(update, context, user_id, text)
        return
    
    # ==================== МНОЖЕСТВЕННЫЙ РЕЖИМ ====================
    elif step == 'multi_efficiency':
        await process_multi_efficiency(update, context, user_id, text)
        return
    elif step == 'multi_tax':
        await process_multi_tax(update, context, user_id, text)
        return
    elif step == 'multi_quantity':
        await process_multi_quantity(update, context, user_id, text)
        return
    elif step == 'multi_market_price':
        await process_multi_market_price(update, context, user_id, text)
        return
    elif step == 'multi_drawing_price':
        await process_multi_drawing_price(update, context, user_id, text)
        return
    
    # ==================== ВВОД ЦЕН ====================
    elif step == 'price_input_waiting':
        await process_price_input_value(update, user_id, text)
        return
    elif step == 'price_input_missing_waiting':
        await process_missing_price_value(update, user_id, text)
        return
    
    # ==================== ВЫБОР ИЗДЕЛИЯ ПО НОМЕРУ ====================
    elif step == 'products':
        try:
            idx = int(text)
            await select_product_by_number(update, user_id, idx)
        except ValueError:
            await update.message.reply_text(
                "❌ Введите номер изделия",
                reply_markup=back_button(user_id, "products")
            )
        return
    
    # ==================== НЕИЗВЕСТНЫЙ ШАГ ====================
    else:
        await update.message.reply_text(
            "❓ Я ожидаю команды из меню. Используйте /start для начала",
            reply_markup=cancel_button(user_id)
        )


async def calculator_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, is_topic: bool, lock=None):
    """Обработчик callback кнопок в калькуляторе"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Проверка, что callback для этого пользователя
    if not data.startswith(f"user_{user_id}_") and data != "noop":
        await query.answer("⛔ Эта кнопка не для вас", show_alert=True)
        return
    
    if is_topic and lock and lock.current_user == user_id:
        lock.refresh(user_id)
    
    action = data.replace(f"user_{user_id}_", "")
    
    # ==================== ГЛОБАЛЬНЫЕ ====================
    if action == "cancel":
        await cancel_calculator(update, context, is_topic, lock)
        return
    
    if action == "noop":
        # Пустая кнопка для пагинации — ничего не делаем
        return
    
    # ==================== ВЫБОР РЕЖИМА (для админа в личке) ====================
    if action == "mode_calculator":
        # Переход в режим калькулятора
        session = get_session(user_id)
        session['mode'] = 'single'
        session['step'] = 'categories'
        session['category_path'] = []
        
        tree = session.get('category_tree', {})
        categories = list(tree.keys())
        
        if categories:
            total_pages = (len(categories) + 9) // 10
            page_categories = categories[:10]
            
            await query.edit_message_text(
                "📂 ВЫБОР КАТЕГОРИИ\n\nДоступные категории:",
                reply_markup=categories_keyboard(page_categories, user_id, 1, total_pages)
            )
        else:
            await query.edit_message_text(
                "❌ Нет доступных категорий",
                reply_markup=cancel_button(user_id)
            )
        return
    
    if action == "mode_admin":
        # Переход в режим администрирования
        from handlers.admin import start_admin
        await start_admin(update, context)
        return
    
    if action == "mode_help":
        await help_calculator(update, context, is_topic)
        return
    
    if action == "mode_exit":
        await cancel_calculator(update, context, is_topic, lock)
        return
    
    # ==================== ВЫБОР РЕЖИМА РАСЧЁТА ====================
    if action == "single_mode":
        await select_mode(query, user_id, "single")
        return
    elif action == "multi_mode":
        await select_mode(query, user_id, "multi")
        return
    
    # ==================== НАВИГАЦИЯ ПО КАТЕГОРИЯМ ====================
    if action.startswith("categories_page_"):
        page = int(action.replace("categories_page_", ""))
        await show_categories(query, user_id, page)
        return
    elif action.startswith("cat_"):
        category = action[4:]
        await select_category(query, user_id, category)
        return
    elif action == "back_to_categories":
        await back_to_categories(query, user_id)
        return
    
    # ==================== ВЫБОР ИЗДЕЛИЯ (ОДИНОЧНЫЙ) ====================
    if action.startswith("select_product_"):
        product_name = action.replace("select_product_", "")
        await select_product_by_name(query, user_id, product_name)
        return
    elif action.startswith("products_page_"):
        page = int(action.replace("products_page_", ""))
        await show_products(query, user_id, page)
        return
    
    # ==================== МНОЖЕСТВЕННЫЙ ВЫБОР ====================
    if action.startswith("toggle_product_"):
        product_name = action.replace("toggle_product_", "")
        await toggle_product(query, user_id, product_name)
        return
    elif action == "confirm_products":
        await confirm_products(query, user_id)
        return
    elif action.startswith("multi_products_page_"):
        page = int(action.replace("multi_products_page_", ""))
        await show_multi_products(query, user_id, page)
        return
    
    # ==================== МАТЕРИАЛЫ ====================
    if action == "price_input":
        await start_price_input(query, user_id)
        return
    elif action == "auto_prices":
        await auto_prices(query, user_id)
        return
    elif action == "price_input_missing":
        await input_missing_prices(query, user_id)
        return
    elif action == "continue":
        await calculate_final_result(query, user_id)
        return
    
    # ==================== ПАГИНАЦИЯ МАТЕРИАЛОВ ====================
    if action.startswith("materials_page_"):
        try:
            page = int(action.replace("materials_page_", ""))
            session = get_session(user_id)
            session['materials_page'] = page - 1
            # Вызываем _show_materials_list для обновления страницы
            await _show_materials_list(query, user_id, session.get('mode') == 'multi')
        except Exception as e:
            logger.error(f"Ошибка при смене страницы материалов: {e}")
            await query.edit_message_text("❌ Ошибка при загрузке страницы", reply_markup=cancel_button(user_id))
        return
    
    # ==================== РЕЗУЛЬТАТЫ ====================
    if action == "next_detail":
        await next_detail(query, user_id)
        return
    elif action == "prev_detail":
        await prev_detail(query, user_id)
        return
    elif action == "total_summary":
        await back_to_total_summary(query, user_id)
        return
    elif action == "back_to_result":
        await back_to_result(query, user_id)
        return
    elif action == "same_category":
        await same_category(query, user_id)
        return
    elif action == "explain":
        await show_explanation(query, user_id)
        return
    elif action == "back_to_products":
        await show_products(query, user_id, 1)
        return
    elif action == "back_to_multi_select":
        await show_multi_products(query, user_id, 1)
        return
    elif action == "back_to_start":
        # Возврат к началу из помощи
        await start_calculator(update, context, is_topic, lock)
        return
    
    logger.warning(f"Неизвестный callback: {action}")
    await query.edit_message_text("❌ Неизвестная команда")


async def cancel_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE, is_topic: bool, lock=None):
    """Отмена текущего расчёта"""
    user_id = update.effective_user.id
    
    if is_topic and lock and lock.current_user == user_id:
        lock.release()
    
    clear_session(user_id)
    
    if update.callback_query:
        await update.callback_query.edit_message_text("❌ Расчет отменен")
    else:
        await update.message.reply_text("❌ Расчет отменен")


async def help_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE, is_topic: bool):
    """Справка по калькулятору"""
    help_text = """📖 ПОМОЩЬ ПО КАЛЬКУЛЯТОРУ

📋 РЕЖИМЫ РАСЧЁТА:
• Одиночный — выбор одного изделия, пошаговый ввод
• Множественный — выбор нескольких изделий, суммирование материалов

💾 СОХРАНЕНИЕ ЦЕН:
• Цены вводятся один раз и сохраняются
• При повторном расчёте подставляются автоматически

📊 ФОРМУЛЫ:
• Эффективность влияет на расход материалов
• Чем ниже эффективность, тем меньше расход материалов
• Налог рассчитывается только при положительной прибыли

🔧 КОМАНДЫ:
/start — начать новый расчёт
/cancel — отменить текущее действие
/help — эта справка

❓ Вопросы: обратитесь к администратору"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(help_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(help_text, parse_mode='Markdown')
