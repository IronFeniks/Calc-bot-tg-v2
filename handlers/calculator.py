import logging
import math
from telegram import Update
from telegram.ext import ContextTypes

from utils.formatters import (
    format_number, format_price, format_price_inline,
    parse_int_input, parse_float_input, parse_excel_price,
    format_material_line, format_material_result_line,
    format_node_result_line, format_leftover_line,
    format_category_path, format_total_result, format_explanation
)
from utils.calculations import (
    calculate_with_efficiency, round_quantity, calculate_node_drawings,
    calculate_node_cost, calculate_total_cost, calculate_profit,
    calculate_tax, calculate_profit_after_tax, merge_materials,
    calculate_materials_for_product, calculate_total_summary
)
from keyboards.calculator import (
    make_callback, mode_selection_keyboard, categories_keyboard,
    products_keyboard, multi_select_products_keyboard,
    materials_keyboard, missing_prices_keyboard,
    result_keyboard, explanation_keyboard, cancel_button, back_button
)
from excel_handler import get_excel_handler
from price_db import get_all_material_prices, save_material_price, get_drawing_price, save_drawing_price

logger = logging.getLogger(__name__)

# ==================== СЕССИИ ПОЛЬЗОВАТЕЛЕЙ ====================

sessions = {}

def get_session(user_id: int) -> dict:
    """Получить сессию пользователя"""
    if user_id not in sessions:
        sessions[user_id] = {
            'step': None,              # текущий шаг
            'mode': None,              # 'single' или 'multi'
            'category_path': [],       # путь по категориям
            'category_tree': None,     # дерево категорий
            'efficiency': None,        # эффективность (%)
            'tax': None,               # налог (%)
            'selected_products': [],   # список выбранных изделий (для multi)
            'current_product_index': 0,# текущий индекс для ввода параметров
            'products_data': [],       # собранные данные по изделиям
            'materials_list': [],      # список материалов и узлов
            'materials_page': 0,       # текущая страница материалов
            'current_material': 0,     # индекс текущего материала для ввода цены
            'missing_materials': [],    # материалы без цен
            'current_missing': 0,       # индекс в списке missing
            'result_page': 0,          # текущая страница результатов (0=общая, 1..n=детали)
            'last_result_text': None,   # текст последнего результата
            'last_result_keyboard': None # клавиатура последнего результата
        }
    return sessions[user_id]

def clear_session(user_id: int):
    """Очистить сессию пользователя"""
    if user_id in sessions:
        del sessions[user_id]

# ==================== ИНСТРУКЦИИ ====================

INSTRUCTION_TOPIC = """🏭 ПРОИЗВОДСТВЕННЫЙ КАЛЬКУЛЯТОР

📍 РЕЖИМ: ТОПИК

📌 ОСОБЕННОСТИ:
• Одновременно может работать только один пользователь
• Если бот занят, вы увидите имя текущего пользователя
• Таймаут сессии: 5 минут бездействия
• Бот отвечает только в этом топике

💾 СОХРАНЕНИЕ ЦЕН:
• Цены материалов и узлов сохраняются автоматически
• При повторном расчёте подставляются сохранённые цены

📋 РЕЖИМЫ РАСЧЁТА:
1. Одиночный — расчёт одного изделия или узла
2. Множественный — расчёт нескольких изделий/узлов с суммированием материалов

📖 КАК РАБОТАТЬ:
1. Введите /start
2. Выберите режим расчёта
3. Следуйте инструкциям бота
4. Все цены вводятся только числом, без ISK

👤 ПЕРЕХОД В ЛИЧНЫЙ РЕЖИМ:
• Если хотите использовать калькулятор без блокировки, перейдите в личную переписку с ботом
• В личке нет ограничений, цены сохраняются лично для вас

❗ ВАЖНО:
• Для отмены текущего расчёта нажмите ❌ Отмена
• Для нового расчёта используйте /start"""

INSTRUCTION_PRIVATE = """🏭 ПРОИЗВОДСТВЕННЫЙ КАЛЬКУЛЯТОР

📍 РЕЖИМ: ЛИЧНАЯ ПЕРЕПИСКА

📌 ОСОБЕННОСТИ:
• Нет ограничений на количество пользователей
• Сессия не имеет таймаута
• Вы можете пользоваться калькулятором в любое время

💾 СОХРАНЕНИЕ ЦЕН:
• Цены материалов и узлов сохраняются автоматически
• При повторном расчёте подставляются сохранённые цены
• Цены сохраняются лично для вас

📋 РЕЖИМЫ РАСЧЁТА:
1. Одиночный — расчёт одного изделия или узла
2. Множественный — расчёт нескольких изделий/узлов с суммированием материалов

📖 КАК РАБОТАТЬ:
1. Введите /start
2. Выберите режим расчёта
3. Следуйте инструкциям бота
4. Все цены вводятся только числом, без ISK

❗ ВАЖНО:
• Для отмены текущего расчёта нажмите ❌ Отмена
• Для нового расчёта используйте /start"""

INSTRUCTION_ADMIN = """🏭 ПРОИЗВОДСТВЕННЫЙ КАЛЬКУЛЯТОР

📍 РЕЖИМ: АДМИНИСТРАТОР (калькулятор)

📌 ОСОБЕННОСТИ:
• Вы вошли как администратор
• Режим калькулятора — без ограничений
• Для перехода в админку используйте /admin

💾 СОХРАНЕНИЕ ЦЕН:
• Цены материалов и узлов сохраняются автоматически
• При повторном расчёте подставляются сохранённые цены

📋 РЕЖИМЫ РАСЧЁТА:
1. Одиночный — расчёт одного изделия или узла
2. Множественный — расчёт нескольких изделий/узлов с суммированием материалов

🔄 ПЕРЕКЛЮЧЕНИЕ РЕЖИМОВ:
• /admin — перейти в режим администрирования
• /start — вернуться в режим калькулятора

❗ ВАЖНО:
• Для отмены текущего расчёта нажмите ❌ Отмена
• Для нового расчёта используйте /start"""

# ==================== ЗАПУСК КАЛЬКУЛЯТОРА ====================

async def start_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE, is_topic: bool, lock=None):
    """Запуск калькулятора"""
    user_id = update.effective_user.id
    
    # Проверка блокировки для топика
    if is_topic and lock and lock.is_locked() and lock.current_user != user_id:
        lock_info = lock.get_lock_info()
        name = lock_info['first_name'] or f"@{lock_info['username']}" if lock_info['username'] else f"ID {lock_info['user_id']}"
        await update.message.reply_text(
            f"⏳ *Бот занят*\n\nСейчас расчёты выполняет: *{name}*",
            parse_mode='Markdown'
        )
        return
    
    # Захват блокировки для топика
    if is_topic and lock:
        if not lock.acquire(user_id, update.effective_user.username, update.effective_user.first_name):
            await update.message.reply_text("❌ Не удалось начать расчёт. Попробуйте позже.")
            return
    
    # Очищаем старую сессию
    clear_session(user_id)
    session = get_session(user_id)
    
    # Загружаем дерево категорий
    excel = get_excel_handler()
    if excel:
        tree = excel.get_category_tree()
        session['category_tree'] = tree
    
    # Определяем, какую инструкцию показывать
    if is_topic:
        instruction = INSTRUCTION_TOPIC
    else:
        from handlers.router import is_admin
        if is_admin(user_id):
            instruction = INSTRUCTION_ADMIN
        else:
            instruction = INSTRUCTION_PRIVATE
    
    # Показываем меню выбора режима
    await update.message.reply_text(
        instruction,
        reply_markup=mode_selection_keyboard(user_id),
        parse_mode='Markdown'
    )

# ==================== ВЫБОР РЕЖИМА ====================

async def select_mode(query, user_id, mode: str):
    """Обработка выбора режима"""
    session = get_session(user_id)
    session['mode'] = mode
    session['step'] = 'categories'
    session['category_path'] = []
    
    # Получаем корневые категории
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

# ==================== КАТЕГОРИИ ====================

async def show_categories(query, user_id, page: int):
    """Показывает категории на текущем уровне"""
    session = get_session(user_id)
    tree = session.get('category_tree', {})
    path = session.get('category_path', [])
    
    # Получаем текущий уровень
    current = tree
    for cat in path:
        if cat in current:
            current = current[cat]['_subcategories']
        else:
            current = {}
    
    categories = list(current.keys())
    
    if not categories:
        # Если нет подкатегорий, переходим к выбору изделий
        if session['mode'] == 'single':
            await show_products(query, user_id, 1)
        else:
            await show_multi_products(query, user_id, 1)
        return
    
    total_pages = (len(categories) + 9) // 10
    start = (page - 1) * 10
    end = start + 10
    page_categories = categories[start:end]
    
    text = "📂 ВЫБОР КАТЕГОРИИ"
    if path:
        text += f"\n\n📁 {format_category_path(path)}"
    
    await query.edit_message_text(
        text,
        reply_markup=categories_keyboard(page_categories, user_id, page, total_pages)
    )

async def select_category(query, user_id, category: str):
    """Выбор категории"""
    session = get_session(user_id)
    tree = session.get('category_tree', {})
    path = session.get('category_path', [])
    
    # Добавляем категорию в путь
    path.append(category)
    session['category_path'] = path
    
    # Получаем подкатегории
    current = tree
    for cat in path:
        if cat in current:
            current = current[cat]['_subcategories']
        else:
            current = {}
    
    if current:
        # Есть подкатегории — показываем их
        categories = list(current.keys())
        total_pages = (len(categories) + 9) // 10
        page_categories = categories[:10]
        
        await query.edit_message_text(
            f"📂 ВЫБОР КАТЕГОРИИ\n\n📁 {format_category_path(path)}",
            reply_markup=categories_keyboard(page_categories, user_id, 1, total_pages)
        )
    else:
        # Нет подкатегорий — переходим к выбору изделий
        if session['mode'] == 'single':
            await show_products(query, user_id, 1)
        else:
            await show_multi_products(query, user_id, 1)

async def back_to_categories(query, user_id):
    """Возврат на уровень выше"""
    session = get_session(user_id)
    path = session.get('category_path', [])
    
    if path:
        path.pop()
        session['category_path'] = path
    
    await show_categories(query, user_id, 1)

# ==================== ВЫБОР ИЗДЕЛИЙ (ОДИНОЧНЫЙ РЕЖИМ) ====================

async def show_products(query, user_id, page: int):
    """Показывает список изделий в текущей категории (одиночный режим)"""
    session = get_session(user_id)
    tree = session.get('category_tree', {})
    path = session.get('category_path', [])
    
    # Получаем изделия на текущем уровне
    items = []
    if path:
        current = tree
        for cat in path:
            if cat in current:
                if cat == path[-1]:
                    items = current[cat].get('_items', [])
                    break
                current = current[cat]['_subcategories']
    
    if not items:
        await query.edit_message_text(
            "❌ В этой категории нет изделий",
            reply_markup=back_button(user_id, "categories")
        )
        return
    
    total_pages = (len(items) + 9) // 10
    start = (page - 1) * 10
    end = start + 10
    page_items = items[start:end]
    
    text = "🏗️ ВЫБОР ИЗДЕЛИЯ"
    if path:
        text += f"\n\n📁 {format_category_path(path)}"
    text += f"\n\nСтраница {page} из {total_pages}\n\n"
    
    for i, item in enumerate(page_items, start + 1):
        text += f"{i}. {item['name']}\n"
    text += "\n👉 Введите номер изделия для выбора"
    
    await query.edit_message_text(
        text,
        reply_markup=products_keyboard(page_items, user_id, page, total_pages)
    )


async def select_product(query, user_id, product_name: str):
    """Выбор изделия (одиночный режим)"""
    session = get_session(user_id)
    excel = get_excel_handler()
    
    product = excel.get_product_by_name(product_name)
    if not product:
        await query.edit_message_text("❌ Изделие не найдено")
        return
    
    session['selected_product'] = product
    session['step'] = 'efficiency'
    
    multiplicity = product.get('Кратность', 1)
    
    await query.edit_message_text(
        f"✅ Выбрано: {product['Наименование']}\n"
        f"📦 Кратность: {multiplicity}\n\n"
        f"📊 ПАРАМЕТРЫ РАСЧЁТА (1/2)\n\n"
        f"Введите эффективность производства (%):\n"
        f"(влияет на расход материалов)\n\n"
        f"Пример: 110",
        reply_markup=cancel_button(user_id)
    )


# ==================== ВЫБОР ИЗДЕЛИЙ (МНОЖЕСТВЕННЫЙ РЕЖИМ) ====================

async def show_multi_products(query, user_id, page: int):
    """Показывает список изделий с чекбоксами (множественный режим)"""
    session = get_session(user_id)
    tree = session.get('category_tree', {})
    path = session.get('category_path', [])
    
    # Получаем изделия на текущем уровне
    items = []
    if path:
        current = tree
        for cat in path:
            if cat in current:
                if cat == path[-1]:
                    items = current[cat].get('_items', [])
                    break
                current = current[cat]['_subcategories']
    
    if not items:
        await query.edit_message_text(
            "❌ В этой категории нет изделий",
            reply_markup=back_button(user_id, "categories")
        )
        return
    
    total_pages = (len(items) + 9) // 10
    start = (page - 1) * 10
    end = start + 10
    page_items = items[start:end]
    
    selected = set(session.get('selected_products', []))
    
    text = "📊 ВЫБОР ИЗДЕЛИЙ (множественный режим)"
    if path:
        text += f"\n\n📁 {format_category_path(path)}"
    text += f"\n\nСтраница {page} из {total_pages}\n\n"
    text += "Выберите изделия для расчёта (можно несколько):\n\n"
    
    for i, item in enumerate(page_items, start + 1):
        checkbox = "☑️" if item['name'] in selected else "☐"
        text += f"{checkbox} {i}. {item['name']}\n"
    
    await query.edit_message_text(
        text,
        reply_markup=multi_select_products_keyboard(page_items, user_id, page, total_pages, selected)
    )


async def toggle_product(query, user_id, product_name: str):
    """Переключение выбора изделия (множественный режим)"""
    session = get_session(user_id)
    selected = session.get('selected_products', [])
    
    if product_name in selected:
        selected.remove(product_name)
    else:
        selected.append(product_name)
    
    session['selected_products'] = selected
    
    # Обновляем текущую страницу
    await show_multi_products(query, user_id, 1)


async def confirm_products(query, user_id):
    """Подтверждение выбора изделий (множественный режим)"""
    session = get_session(user_id)
    selected = session.get('selected_products', [])
    
    if not selected:
        await query.answer("❌ Выберите хотя бы одно изделие", show_alert=True)
        return
    
    excel = get_excel_handler()
    
    # Сохраняем выбранные изделия
    products = []
    for name in selected:
        product = excel.get_product_by_name(name)
        if product:
            products.append(product)
    
    session['multi_products'] = products
    session['current_product_index'] = 0
    session['step'] = 'multi_efficiency'
    
    await query.edit_message_text(
        f"✅ Выбрано изделий: {len(products)}\n\n"
        f"📊 ПАРАМЕТРЫ РАСЧЁТА (1/2)\n\n"
        f"Введите эффективность производства (%):\n"
        f"(общая для всех изделий)\n\n"
        f"Пример: 110",
        reply_markup=cancel_button(user_id)
    )


# ==================== ВВОД ПАРАМЕТРОВ (ОБЩИЙ) ====================

async def process_efficiency(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода эффективности для одиночного режима"""
    efficiency = parse_float_input(text)
    if efficiency is None or efficiency < 50 or efficiency > 150:
        await update.message.reply_text(
            "❌ Введите число от 50 до 150 (процентов)",
            reply_markup=back_button(user_id, "categories")
        )
        return
    
    session = get_session(user_id)
    session['efficiency'] = efficiency
    session['step'] = 'tax'
    
    await update.message.reply_text(
        f"📊 ПАРАМЕТРЫ РАСЧЁТА (2/2)\n\n"
        f"Введите ставку налога (%):\n"
        f"(налог рассчитывается только при положительной прибыли)\n\n"
        f"Пример: 20",
        reply_markup=cancel_button(user_id)
    )


async def process_tax(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода налога для одиночного режима"""
    tax = parse_float_input(text)
    if tax is None or tax < 0 or tax > 100:
        await update.message.reply_text(
            "❌ Введите число от 0 до 100 (процентов)",
            reply_markup=back_button(user_id, "categories")
        )
        return
    
    session = get_session(user_id)
    session['tax'] = tax
    
    # Переходим к вводу количества
    session['step'] = 'quantity'
    product = session.get('selected_product', {})
    multiplicity = product.get('Кратность', 1)
    
    await update.message.reply_text(
        f"📦 КОЛИЧЕСТВО\n\n"
        f"Изделие: {product.get('Наименование', '')}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите количество продукции (шт):\n"
        f"(должно быть кратно {multiplicity})",
        reply_markup=cancel_button(user_id)
    )


async def process_multi_efficiency(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода эффективности для множественного режима"""
    efficiency = parse_float_input(text)
    if efficiency is None or efficiency < 50 or efficiency > 150:
        await update.message.reply_text(
            "❌ Введите число от 50 до 150 (процентов)",
            reply_markup=back_button(user_id, "categories")
        )
        return
    
    session = get_session(user_id)
    session['efficiency'] = efficiency
    session['step'] = 'multi_tax'
    
    await update.message.reply_text(
        f"📊 ПАРАМЕТРЫ РАСЧЁТА (2/2)\n\n"
        f"Введите ставку налога (%):\n"
        f"(налог рассчитывается только при положительной прибыли)\n\n"
        f"Пример: 20",
        reply_markup=cancel_button(user_id)
    )


async def process_multi_tax(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода налога для множественного режима"""
    tax = parse_float_input(text)
    if tax is None or tax < 0 or tax > 100:
        await update.message.reply_text(
            "❌ Введите число от 0 до 100 (процентов)",
            reply_markup=back_button(user_id, "categories")
        )
        return
    
    session = get_session(user_id)
    session['tax'] = tax
    
    # Получаем выбранные изделия
    selected_names = session.get('selected_products', [])
    if not selected_names:
        await update.message.reply_text(
            "❌ Нет выбранных изделий",
            reply_markup=back_button(user_id, "categories")
        )
        return
    
    # Загружаем полные данные об изделиях
    excel = get_excel_handler()
    products = []
    for name in selected_names:
        product = excel.get_product_by_name(name)
        if product:
            products.append(product)
        else:
            logger.warning(f"Изделие не найдено: {name}")
    
    if not products:
        await update.message.reply_text(
            "❌ Не удалось загрузить выбранные изделия",
            reply_markup=back_button(user_id, "categories")
        )
        return
    
    session['multi_products'] = products
    session['current_product_index'] = 0
    session['multi_products_data'] = []
    session['step'] = 'multi_quantity'
    
    await process_next_multi_product(update, user_id)


# ==================== МНОЖЕСТВЕННЫЙ РЕЖИМ — ВВОД ПАРАМЕТРОВ ДЛЯ КАЖДОГО ====================


# ==================== МНОЖЕСТВЕННЫЙ РЕЖИМ — ВВОД ПАРАМЕТРОВ ДЛЯ КАЖДОГО ====================

async def process_next_multi_product(update, user_id: int):
    """Ввод параметров для следующего изделия (множественный режим)"""
    session = get_session(user_id)
    products = session.get('multi_products', [])
    index = session.get('current_product_index', 0)
    
    if index >= len(products):
        # Все параметры введены — переходим к расчёту
        await calculate_multi_materials(update, user_id)
        return
    
    product = products[index]
    session['current_multi_product'] = product
    session['step'] = 'multi_quantity'
    
    multiplicity = product.get('Кратность', 1)
    
    await update.message.reply_text(
        f"📦 КОЛИЧЕСТВО ({index + 1}/{len(products)})\n\n"
        f"Изделие: {product['Наименование']}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите количество продукции (шт):\n"
        f"(должно быть кратно {multiplicity})",
        reply_markup=cancel_button(user_id)
    )


async def process_multi_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода количества для множественного режима"""
    qty = parse_int_input(text)
    session = get_session(user_id)
    product = session.get('current_multi_product', {})
    multiplicity = product.get('Кратность', 1)
    
    if qty is None or qty <= 0 or qty % multiplicity != 0:
        await update.message.reply_text(
            f"❌ Количество должно быть положительным целым числом, кратным {multiplicity}",
            reply_markup=cancel_button(user_id)
        )
        return
    
    # Сохраняем количество
    session['temp_quantity'] = qty
    session['step'] = 'multi_market_price'
    
    saved_price = get_drawing_price(product.get('Код', ''))
    price_text = format_price(saved_price) if saved_price > 0 else "не установлена"
    
    await update.message.reply_text(
        f"💰 РЫНОЧНАЯ ЦЕНА ({session['current_product_index'] + 1}/{len(session['multi_products'])})\n\n"
        f"Изделие: {product['Наименование']}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите рыночную цену за 1 шт (ISK):\n"
        f"(только число, без ISK)\n\n"
        f"Текущая сохранённая цена: {price_text}\n"
        f"Пример: 4 767 760",
        reply_markup=cancel_button(user_id)
    )


async def process_multi_market_price(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода рыночной цены для множественного режима"""
    price = parse_float_input(text)
    if price is None or price < 0:
        await update.message.reply_text(
            "❌ Введите положительное число",
            reply_markup=cancel_button(user_id)
        )
        return
    
    session = get_session(user_id)
    session['temp_market_price'] = price
    session['step'] = 'multi_drawing_price'
    
    product = session.get('current_multi_product', {})
    saved_price = get_drawing_price(product.get('Код', ''))
    price_text = format_price(saved_price) if saved_price > 0 else "не установлена"
    
    await update.message.reply_text(
        f"💰 СТОИМОСТЬ ЧЕРТЕЖА ({session['current_product_index'] + 1}/{len(session['multi_products'])})\n\n"
        f"Изделие: {product['Наименование']}\n"
        f"Кратность: {product.get('Кратность', 1)}\n\n"
        f"Введите стоимость чертежа (ISK):\n"
        f"(сохраняется для будущих расчётов)\n\n"
        f"Текущая сохранённая цена: {price_text}\n"
        f"Пример: 5 454",
        reply_markup=cancel_button(user_id)
    )


async def process_multi_drawing_price(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода стоимости чертежа для множественного режима"""
    price = parse_float_input(text)
    if price is None or price < 0:
        await update.message.reply_text(
            "❌ Введите положительное число",
            reply_markup=cancel_button(user_id)
        )
        return
    
    session = get_session(user_id)
    product = session.get('current_multi_product', {})
    
    # Сохраняем цену чертежа
    save_drawing_price(product.get('Код', ''), price)
    
    # Сохраняем все данные для этого изделия
    product_data = {
        'product': product,
        'quantity': session.get('temp_quantity'),
        'market_price': session.get('temp_market_price'),
        'drawing_price': price
    }
    
    if 'multi_products_data' not in session:
        session['multi_products_data'] = []
    session['multi_products_data'].append(product_data)
    
    # Переходим к следующему изделию
    session['current_product_index'] += 1
    await process_next_multi_product(update, user_id)

# ==================== РАСЧЁТ МАТЕРИАЛОВ ====================

async def calculate_multi_materials(update, user_id: int):
    """Расчёт материалов для множественного режима"""
    session = get_session(user_id)
    excel = get_excel_handler()
    products_data = session.get('multi_products_data', [])
    efficiency = session.get('efficiency', 150)
    saved_prices = get_all_material_prices()
    
    all_materials = []
    all_nodes = []
    products_with_details = []
    
    for data in products_data:
        product = data['product']
        quantity = data['quantity']
        market_price = data['market_price']
        drawing_price = data['drawing_price']
        
        # Рассчитываем материалы для изделия
        materials_list, drawings_needed, node_details = calculate_materials_for_product(
            product['Код'], quantity, efficiency, excel, saved_prices
        )
        
        # Добавляем в общий список
        all_materials.extend(materials_list)
        all_nodes.extend(node_details)
        
        # Сохраняем детали для вывода
        products_with_details.append({
            'product': product,
            'quantity': quantity,
            'market_price': market_price,
            'drawing_price': drawing_price,
            'materials_list': materials_list,
            'drawings_needed': drawings_needed,
            'node_details': node_details
        })
    
    # Объединяем одинаковые материалы
    merged_materials = merge_materials(all_materials)
    
    # Объединяем одинаковые узлы
    merged_nodes = {}
    for node in all_nodes:
        name = node['name']
        if name not in merged_nodes:
            merged_nodes[name] = node.copy()
            merged_nodes[name]['needed_qty'] = 0
            merged_nodes[name]['drawings'] = 0
            merged_nodes[name]['total_cost'] = 0
        merged_nodes[name]['needed_qty'] += node['needed_qty']
        merged_nodes[name]['drawings'] += node['drawings']
        merged_nodes[name]['total_cost'] += node['total_cost']
    
    nodes_list = list(merged_nodes.values())
    nodes_list.sort(key=lambda x: x['name'])
    for i, node in enumerate(nodes_list, 1):
        node['number'] = i
    
    # Сохраняем в сессию
    session['materials_list'] = merged_materials
    session['nodes_list'] = nodes_list
    session['products_with_details'] = products_with_details
    session['step'] = 'materials'
    session['materials_page'] = 0
    
    # Показываем список материалов
    await show_materials_list(update, user_id, is_multi=True)


async def calculate_single_materials(update, user_id: int):
    """Расчёт материалов для одиночного режима"""
    session = get_session(user_id)
    excel = get_excel_handler()
    product = session.get('selected_product', {})
    quantity = session.get('qty', 0)
    efficiency = session.get('efficiency', 150)
    market_price = session.get('market_price', 0)
    drawing_price = session.get('drawing_price', 0)
    saved_prices = get_all_material_prices()
    
    # Рассчитываем материалы
    materials_list, drawings_needed, node_details = calculate_materials_for_product(
        product['Код'], quantity, efficiency, excel, saved_prices
    )
    
    # Сохраняем в сессию
    session['materials_list'] = materials_list
    session['nodes_list'] = node_details
    session['single_product_detail'] = {
        'product': product,
        'quantity': quantity,
        'market_price': market_price,
        'drawing_price': drawing_price,
        'drawings_needed': drawings_needed
    }
    session['step'] = 'materials'
    session['materials_page'] = 0
    
    # Показываем список материалов
    await show_materials_list(update, user_id, is_multi=False)


async def show_materials_list(update, user_id: int, is_multi: bool = False):
    """Показывает список материалов и узлов"""
    session = get_session(user_id)
    materials = session.get('materials_list', [])
    nodes = session.get('nodes_list', [])
    
    # Объединяем материалы и узлы для отображения
    all_items = materials + nodes
    all_items.sort(key=lambda x: x['number'])
    
    # Переопределяем номера для объединённого списка
    for i, item in enumerate(all_items, 1):
        item['display_number'] = i
    
    total_pages = (len(all_items) + 9) // 10
    page = session.get('materials_page', 0)
    start = page * 10
    end = min(start + 10, len(all_items))
    page_items = all_items[start:end]
    
    # Формируем текст
    text = "📦 МАТЕРИАЛЫ И УЗЛЫ\n\n"
    if not is_multi:
        product = session.get('selected_product', {})
        text += f"Изделие: {product.get('Наименование', '')}\n"
    else:
        text += f"Режим: множественный расчёт\n"
    text += f"Эффективность: {session.get('efficiency', 150)}%\n\n"
    
    text += f"Страница {page + 1} из {total_pages}\n\n"
    
    # Материалы
    materials_in_page = [i for i in page_items if i.get('type') == 'material']
    if materials_in_page:
        text += "МАТЕРИАЛЫ:\n"
        for item in materials_in_page:
            text += format_material_line(
                item['display_number'], item['name'], item['qty'], item.get('price', 0)
            ) + "\n"
        text += "\n"
    
    # Узлы
    nodes_in_page = [i for i in page_items if i.get('type') == 'node']
    if nodes_in_page:
        text += "УЗЛЫ:\n"
        for item in nodes_in_page:
            text += format_material_line(
                item['display_number'], item['name'], item['qty'], item.get('price', 0)
            ) + "\n"
        text += "\n"
    
    # Проверяем, есть ли материалы без цен
    missing = [i for i in all_items if i.get('price', 0) == 0]
    session['missing_materials'] = missing
    
    await update.message.reply_text(
        text,
        reply_markup=materials_keyboard(all_items, user_id, page + 1, total_pages, "multi" if is_multi else "single")
    )


# ==================== ВВОД ЦЕН НА МАТЕРИАЛЫ ====================

async def start_price_input(query, user_id: int):
    """Начало пошагового ввода цен"""
    session = get_session(user_id)
    materials = session.get('materials_list', [])
    nodes = session.get('nodes_list', [])
    
    # Объединяем все элементы
    all_items = materials + nodes
    all_items.sort(key=lambda x: x.get('number', 0))
    
    session['price_input_items'] = all_items
    session['current_material'] = 0
    session['step'] = 'price_input'
    
    await process_next_price(query, user_id)


async def process_next_price(query, user_id: int):
    """Ввод цены для следующего элемента"""
    session = get_session(user_id)
    items = session.get('price_input_items', [])
    current = session.get('current_material', 0)
    
    if current >= len(items):
        # Все цены введены — переходим к результатам
        await calculate_final_result(query, user_id)
        return
    
    item = items[current]
    current_price = item.get('price', 0)
    
    text = f"📦 ВВОД ЦЕН ({current + 1}/{len(items)})\n\n"
    text += f"Элемент: {item['name']}\n"
    text += f"Необходимое количество: {format_number(item['qty'])} шт\n"
    text += f"Текущая цена в базе: {format_price(current_price)}\n\n"
    text += "Введите цену за 1 шт (ISK):"
    
    await query.edit_message_text(
        text,
        reply_markup=cancel_button(user_id)
    )
    
    session['step'] = 'price_input_waiting'


async def process_price_input_value(update: Update, user_id: int, text: str):
    """Обработка введённой цены"""
    price = parse_float_input(text)
    if price is None or price < 0:
        await update.message.reply_text(
            "❌ Введите положительное число",
            reply_markup=cancel_button(user_id)
        )
        return
    
    session = get_session(user_id)
    items = session.get('price_input_items', [])
    current = session.get('current_material', 0)
    
    if current < len(items):
        item = items[current]
        item['price'] = price
        item['cost'] = price * item['qty']
        
        # Сохраняем цену в базу
        save_material_price(item['name'], price)
        
        # Обновляем цену в основном списке
        if item.get('type') == 'material':
            for m in session.get('materials_list', []):
                if m['name'] == item['name']:
                    m['price'] = price
        else:
            for n in session.get('nodes_list', []):
                if n['name'] == item['name']:
                    n['price'] = price
        
        session['current_material'] = current + 1
        await process_next_price(update, user_id)


async def auto_prices(query, user_id: int):
    """Автоматическая подстановка цен"""
    session = get_session(user_id)
    materials = session.get('materials_list', [])
    nodes = session.get('nodes_list', [])
    all_items = materials + nodes
    
    missing = [i for i in all_items if i.get('price', 0) == 0]
    
    if missing:
        # Есть материалы без цен
        text = "🤖 АВТОМАТИЧЕСКАЯ ПОДСТАНОВКА ЦЕН\n\n"
        text += f"✅ Цены подставлены для: {len(all_items) - len(missing)} элементов\n"
        text += f"⚠️ Нет цен для: {len(missing)} элементов\n\n"
        text += "Элементы без цен:\n"
        for m in missing[:10]:
            text += f"• {m['name']} (нужно {format_number(m['qty'])} шт)\n"
        if len(missing) > 10:
            text += f"• ... и ещё {len(missing) - 10}\n\n"
        text += "Что делаем?"
        
        session['missing_materials'] = missing
        session['step'] = 'missing_prices'
        
        await query.edit_message_text(
            text,
            reply_markup=missing_prices_keyboard(user_id)
        )
    else:
        # Все цены есть
        await calculate_final_result(query, user_id)


async def input_missing_prices(query, user_id: int):
    """Ввод только недостающих цен"""
    session = get_session(user_id)
    missing = session.get('missing_materials', [])
    
    session['price_input_items'] = missing
    session['current_material'] = 0
    session['step'] = 'price_input_missing'
    
    await process_next_missing_price(query, user_id)


async def process_next_missing_price(query, user_id: int):
    """Ввод цены для недостающего элемента"""
    session = get_session(user_id)
    items = session.get('price_input_items', [])
    current = session.get('current_material', 0)
    
    if current >= len(items):
        await calculate_final_result(query, user_id)
        return
    
    item = items[current]
    
    text = f"📦 ВВОД НЕДОСТАЮЩИХ ЦЕН ({current + 1}/{len(items)})\n\n"
    text += f"Элемент: {item['name']}\n"
    text += f"Необходимое количество: {format_number(item['qty'])} шт\n\n"
    text += "Введите цену за 1 шт (ISK):"
    
    await query.edit_message_text(
        text,
        reply_markup=cancel_button(user_id)
    )
    
    session['step'] = 'price_input_missing_waiting'


async def process_missing_price_value(update: Update, user_id: int, text: str):
    """Обработка введённой цены для недостающего элемента"""
    price = parse_float_input(text)
    if price is None or price < 0:
        await update.message.reply_text(
            "❌ Введите положительное число",
            reply_markup=cancel_button(user_id)
        )
        return
    
    session = get_session(user_id)
    items = session.get('price_input_items', [])
    current = session.get('current_material', 0)
    
    if current < len(items):
        item = items[current]
        item['price'] = price
        item['cost'] = price * item['qty']
        
        # Сохраняем цену в базу
        save_material_price(item['name'], price)
        
        # Обновляем цену в основном списке
        if item.get('type') == 'material':
            for m in session.get('materials_list', []):
                if m['name'] == item['name']:
                    m['price'] = price
        else:
            for n in session.get('nodes_list', []):
                if n['name'] == item['name']:
                    n['price'] = price
        
        session['current_material'] = current + 1
        await process_next_missing_price(update, user_id)

# ==================== ФИНАЛЬНЫЙ РАСЧЁТ ====================

async def calculate_final_result(query, user_id: int):
    """Финальный расчёт и вывод результатов"""
    session = get_session(user_id)
    mode = session.get('mode')
    tax_rate = session.get('tax', 0)
    
    if mode == 'single':
        await calculate_single_result(query, user_id, tax_rate)
    else:
        await calculate_multi_result(query, user_id, tax_rate)


async def calculate_single_result(query, user_id: int, tax_rate: float):
    """Расчёт и вывод результата для одиночного режима"""
    session = get_session(user_id)
    product = session.get('selected_product', {})
    quantity = session.get('qty', 0)
    market_price = session.get('market_price', 0)
    drawing_price = session.get('drawing_price', 0)
    materials_list = session.get('materials_list', [])
    nodes_list = session.get('nodes_list', [])
    drawings_needed = session.get('single_product_detail', {}).get('drawings_needed', 1)
    
    # Расчёт стоимости материалов
    materials_cost = 0
    for m in materials_list:
        cost = m['qty'] * m.get('price', 0)
        m['cost'] = cost
        materials_cost += cost
    
    # Расчёт стоимости производства
    prod_price_str = product.get('Цена производства', '0 ISK')
    try:
        prod_price = float(str(prod_price_str).replace(' ISK', '').replace(' ', ''))
    except:
        prod_price = 0
    production_cost = prod_price * drawings_needed
    
    # Расчёт стоимости чертежей
    drawings_cost = drawing_price * drawings_needed
    
    # Добавляем стоимость чертежей узлов
    node_drawings_cost = 0
    for node in nodes_list:
        node_drawings_cost += node.get('total_cost', 0)
    drawings_cost += node_drawings_cost
    
    # Итоговые расчёты
    total_cost = materials_cost + production_cost + drawings_cost
    revenue = market_price * quantity
    profit_before_tax = revenue - total_cost
    tax = calculate_tax(profit_before_tax, tax_rate)
    profit_after_tax = profit_before_tax - tax
    per_unit_cost = total_cost / quantity if quantity > 0 else 0
    per_unit_profit = profit_after_tax / quantity if quantity > 0 else 0
    
    # Формируем текст результатов
    text = f"📊 РЕЗУЛЬТАТЫ РАСЧЕТА\n\n"
    text += f"🏷️ ИЗДЕЛИЕ: {product.get('Наименование', '')}\n"
    text += f"📂 КАТЕГОРИЯ: {product.get('Категории', '')}\n"
    text += f"📦 КОЛИЧЕСТВО: {format_number(quantity)} шт\n"
    text += f"⚙️ ЭФФЕКТИВНОСТЬ: {session.get('efficiency', 150)}%\n"
    text += f"🏛️ НАЛОГ: {tax_rate}%\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Материалы
    if materials_list:
        text += "📦 МАТЕРИАЛЫ:\n"
        for i, m in enumerate(materials_list, 1):
            text += format_material_result_line(i, m['name'], m['qty'], m.get('price', 0), m.get('cost', 0)) + "\n"
        text += "\n"
    
    # Узлы
    if nodes_list:
        text += "🔩 УЗЛЫ И ЧЕРТЕЖИ:\n"
        for i, node in enumerate(nodes_list, 1):
            leftover = node.get('leftover', 0)
            text += format_node_result_line(
                i, node['name'], node['needed_qty'], 
                node['drawings'], node.get('multiplicity', 1), 
                leftover if leftover > 0 else None
            ) + "\n"
        text += "\n"
        
        # Остатки
        leftovers = [n for n in nodes_list if n.get('leftover', 0) > 0]
        if leftovers:
            text += "📦 ОСТАТКИ УЗЛОВ (неиспользованные):\n"
            for node in leftovers:
                text += format_leftover_line(node['name'], node['leftover']) + "\n"
            text += "\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Итоговая таблица
    text += format_total_result(
        materials_cost, production_cost, drawings_cost,
        total_cost, revenue, profit_before_tax, tax, profit_after_tax,
        per_unit_cost, per_unit_profit
    )
    
    # Сохраняем для возврата из пояснения
    session['last_result_text'] = text
    session['last_result_keyboard'] = result_keyboard(user_id, is_multi=False)
    
    await query.edit_message_text(
        text,
        reply_markup=result_keyboard(user_id, is_multi=False),
        parse_mode='Markdown'
    )


async def calculate_multi_result(query, user_id: int, tax_rate: float):
    """Расчёт и вывод результата для множественного режима"""
    session = get_session(user_id)
    products_data = session.get('products_with_details', [])
    materials_list = session.get('materials_list', [])
    nodes_list = session.get('nodes_list', [])
    efficiency = session.get('efficiency', 150)
    
    # Расчёт общей сводки
    total_materials_cost = 0
    total_production_cost = 0
    total_drawings_cost = 0
    total_revenue = 0
    
    for data in products_data:
        product = data['product']
        quantity = data['quantity']
        market_price = data['market_price']
        drawing_price = data['drawing_price']
        drawings_needed = data.get('drawings_needed', 1)
        
        # Производство
        prod_price_str = product.get('Цена производства', '0 ISK')
        try:
            prod_price = float(str(prod_price_str).replace(' ISK', '').replace(' ', ''))
        except:
            prod_price = 0
        total_production_cost += prod_price * drawings_needed
        
        # Чертежи
        total_drawings_cost += drawing_price * drawings_needed
        
        # Выручка
        total_revenue += market_price * quantity
    
    # Стоимость материалов
    for m in materials_list:
        cost = m['qty'] * m.get('price', 0)
        m['cost'] = cost
        total_materials_cost += cost
    
    # Стоимость чертежей узлов
    node_drawings_cost = 0
    for node in nodes_list:
        node_drawings_cost += node.get('total_cost', 0)
    total_drawings_cost += node_drawings_cost
    
    # Итоговые расчёты
    total_cost = total_materials_cost + total_production_cost + total_drawings_cost
    profit_before_tax = total_revenue - total_cost
    tax = calculate_tax(profit_before_tax, tax_rate)
    profit_after_tax = profit_before_tax - tax
    
    # Сохраняем данные для навигации
    session['multi_result'] = {
        'total_materials_cost': total_materials_cost,
        'total_production_cost': total_production_cost,
        'total_drawings_cost': total_drawings_cost,
        'total_cost': total_cost,
        'total_revenue': total_revenue,
        'profit_before_tax': profit_before_tax,
        'tax': tax,
        'profit_after_tax': profit_after_tax,
        'materials_list': materials_list,
        'nodes_list': nodes_list
    }
    session['products_with_details'] = products_data
    session['result_page'] = 0  # 0 = общая сводка
    
    # Показываем общую сводку
    await show_total_summary(query, user_id, tax_rate)


async def show_total_summary(query, user_id: int, tax_rate: float = None):
    """Показывает общую сводку для множественного режима"""
    session = get_session(user_id)
    result = session.get('multi_result', {})
    products_data = session.get('products_with_details', [])
    
    if tax_rate is None:
        tax_rate = session.get('tax', 0)
    
    materials_list = result.get('materials_list', [])
    nodes_list = result.get('nodes_list', [])
    
    # Формируем текст
    product_names = [p['product']['Наименование'] for p in products_data]
    text = f"📊 РЕЗУЛЬТАТЫ РАСЧЁТА (ОБЩАЯ СВОДКА)\n\n"
    text += f"Режим: множественный расчёт\n"
    text += f"Изделия: {', '.join(product_names)} ({len(products_data)} шт)\n"
    text += f"Эффективность: {session.get('efficiency', 150)}%\n"
    text += f"Налог: {tax_rate}%\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Материалы
    if materials_list:
        text += "📦 МАТЕРИАЛЫ (ОБЩИЕ):\n"
        for i, m in enumerate(materials_list, 1):
            text += format_material_result_line(i, m['name'], m['qty'], m.get('price', 0), m.get('cost', 0)) + "\n"
        text += "\n"
    
    # Узлы
    if nodes_list:
        text += "🔩 УЗЛЫ И ЧЕРТЕЖИ (ОБЩИЕ):\n"
        for i, node in enumerate(nodes_list, 1):
            text += format_node_result_line(
                i, node['name'], node['needed_qty'], 
                node['drawings'], node.get('multiplicity', 1)
            ) + "\n"
        text += "\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Итоговая таблица
    text += format_total_result(
        result.get('total_materials_cost', 0),
        result.get('total_production_cost', 0),
        result.get('total_drawings_cost', 0),
        result.get('total_cost', 0),
        result.get('total_revenue', 0),
        result.get('profit_before_tax', 0),
        result.get('tax', 0),
        result.get('profit_after_tax', 0)
    )
    
    session['last_result_text'] = text
    session['last_result_keyboard'] = result_keyboard(user_id, is_multi=True, current_index=-1, total_count=len(products_data))
    
    await query.edit_message_text(
        text,
        reply_markup=result_keyboard(user_id, is_multi=True, current_index=-1, total_count=len(products_data)),
        parse_mode='Markdown'
    )


async def show_product_detail(query, user_id: int, index: int):
    """Показывает детали по конкретному изделию (множественный режим)"""
    session = get_session(user_id)
    products_data = session.get('products_with_details', [])
    
    if index < 0 or index >= len(products_data):
        return
    
    data = products_data[index]
    product = data['product']
    quantity = data['quantity']
    market_price = data['market_price']
    drawing_price = data['drawing_price']
    materials_list = data.get('materials_list', [])
    node_details = data.get('node_details', [])
    drawings_needed = data.get('drawings_needed', 1)
    tax_rate = session.get('tax', 0)
    
    # Расчёт для одного изделия
    materials_cost = sum(m['qty'] * m.get('price', 0) for m in materials_list)
    
    prod_price_str = product.get('Цена производства', '0 ISK')
    try:
        prod_price = float(str(prod_price_str).replace(' ISK', '').replace(' ', ''))
    except:
        prod_price = 0
    production_cost = prod_price * drawings_needed
    
    drawings_cost = drawing_price * drawings_needed
    node_drawings_cost = sum(node.get('total_cost', 0) for node in node_details)
    drawings_cost += node_drawings_cost
    
    total_cost = materials_cost + production_cost + drawings_cost
    revenue = market_price * quantity
    profit_before_tax = revenue - total_cost
    tax = calculate_tax(profit_before_tax, tax_rate)
    profit_after_tax = profit_before_tax - tax
    per_unit_cost = total_cost / quantity if quantity > 0 else 0
    per_unit_profit = profit_after_tax / quantity if quantity > 0 else 0
    
    # Формируем текст
    text = f"📊 РЕЗУЛЬТАТЫ РАСЧЁТА ({index + 1}/{len(products_data)})\n\n"
    text += f"🏷️ ИЗДЕЛИЕ: {product.get('Наименование', '')}\n"
    text += f"📂 КАТЕГОРИЯ: {product.get('Категории', '')}\n"
    text += f"📦 КОЛИЧЕСТВО: {format_number(quantity)} шт\n"
    text += f"⚙️ ЭФФЕКТИВНОСТЬ: {session.get('efficiency', 150)}%\n"
    text += f"🏛️ НАЛОГ: {tax_rate}%\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if materials_list:
        text += "📦 МАТЕРИАЛЫ:\n"
        for i, m in enumerate(materials_list, 1):
            text += format_material_result_line(i, m['name'], m['qty'], m.get('price', 0), m['qty'] * m.get('price', 0)) + "\n"
        text += "\n"
    
    if node_details:
        text += "🔩 УЗЛЫ И ЧЕРТЕЖИ:\n"
        for i, node in enumerate(node_details, 1):
            text += format_node_result_line(
                i, node['name'], node['needed_qty'], 
                node['drawings'], node.get('multiplicity', 1),
                node.get('leftover', 0) if node.get('leftover', 0) > 0 else None
            ) + "\n"
        text += "\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    text += format_total_result(
        materials_cost, production_cost, drawings_cost,
        total_cost, revenue, profit_before_tax, tax, profit_after_tax,
        per_unit_cost, per_unit_profit
    )
    
    session['last_result_text'] = text
    session['last_result_keyboard'] = result_keyboard(user_id, is_multi=True, current_index=index, total_count=len(products_data))
    
    await query.edit_message_text(
        text,
        reply_markup=result_keyboard(user_id, is_multi=True, current_index=index, total_count=len(products_data)),
        parse_mode='Markdown'
    )


# ==================== НАВИГАЦИЯ ПО РЕЗУЛЬТАТАМ ====================

async def next_detail(query, user_id: int):
    """Переход к следующему изделию"""
    session = get_session(user_id)
    products_data = session.get('products_with_details', [])
    current = session.get('result_page', 0)
    
    if current < 0:
        current = 0
    
    next_index = current + 1
    if next_index < len(products_data):
        session['result_page'] = next_index
        await show_product_detail(query, user_id, next_index)


async def prev_detail(query, user_id: int):
    """Переход к предыдущему изделию"""
    session = get_session(user_id)
    current = session.get('result_page', 0)
    
    prev_index = current - 1
    if prev_index >= 0:
        session['result_page'] = prev_index
        await show_product_detail(query, user_id, prev_index)


async def back_to_total_summary(query, user_id: int):
    """Возврат к общей сводке"""
    session = get_session(user_id)
    session['result_page'] = -1
    await show_total_summary(query, user_id)


async def back_to_result(query, user_id: int):
    """Возврат к результатам из пояснения"""
    session = get_session(user_id)
    text = session.get('last_result_text')
    keyboard = session.get('last_result_keyboard')
    
    if text and keyboard:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')


async def same_category(query, user_id: int):
    """Новый расчёт в той же категории"""
    session = get_session(user_id)
    category_path = session.get('category_path', [])
    
    # Очищаем сессию, но сохраняем путь категории
    new_session = {
        'step': 'efficiency',
        'mode': session.get('mode'),
        'category_path': category_path.copy(),
        'category_tree': session.get('category_tree'),
        'efficiency': None,
        'tax': None,
        'selected_products': [],
        'multi_products': [],
        'products_data': [],
        'materials_list': [],
        'nodes_list': []
    }
    sessions[user_id] = new_session
    
    path_str = format_category_path(category_path)
    
    await query.edit_message_text(
        f"📊 ПАРАМЕТРЫ РАСЧЁТА\n\n"
        f"Категория: {path_str}\n\n"
        f"Введите эффективность производства (%):\n"
        f"Пример: 110",
        reply_markup=cancel_button(user_id)
    )


async def show_explanation(query, user_id: int):
    """Показывает пояснение"""
    await query.edit_message_text(
        format_explanation(),
        reply_markup=explanation_keyboard(user_id),
        parse_mode='Markdown'
    )


# ==================== ОБРАБОТЧИКИ ====================

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


# ==================== ОСНОВНОЙ ОБРАБОТЧИК ====================

async def calculator_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, is_topic: bool, lock=None):
    """Обработчик текстовых сообщений в калькуляторе"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    session = get_session(user_id)
    step = session.get('step')
    
    # Обновляем время блокировки для топика
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
            idx = int(text) - 1
            items = session.get('current_products', [])
            if 0 <= idx < len(items):
                product = items[idx]
                # Сохраняем выбранное изделие
                excel = get_excel_handler()
                product_full = excel.get_product_by_name(product['name'])
                if product_full:
                    session['selected_product'] = product_full
                    session['step'] = 'quantity'
                    multiplicity = product_full.get('Кратность', 1)
                    await update.message.reply_text(
                        f"✅ Выбрано: {product_full['Наименование']}\n"
                        f"📦 Кратность: {multiplicity}\n\n"
                        f"📦 Введите количество продукции (шт):\n"
                        f"(должно быть кратно {multiplicity})",
                        reply_markup=back_button(user_id, "products")
                    )
                else:
                    await update.message.reply_text(
                        "❌ Ошибка загрузки изделия",
                        reply_markup=back_button(user_id, "products")
                    )
            else:
                await update.message.reply_text(
                    f"❌ Введите число от 1 до {len(items)}",
                    reply_markup=back_button(user_id, "products")
                )
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
    
    # Обновляем время блокировки для топика
    if is_topic and lock and lock.current_user == user_id:
        lock.refresh(user_id)
    
    # Убираем префикс
    action = data.replace(f"user_{user_id}_", "")
    
    # Глобальная отмена
    if action == "cancel":
        await cancel_calculator(update, context, is_topic, lock)
        return
    
    # Выбор режима
    if action == "single_mode":
        await select_mode(query, user_id, "single")
        return
    elif action == "multi_mode":
        await select_mode(query, user_id, "multi")
        return
    
    # Навигация по категориям
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
    
    # Выбор изделия (одиночный)
    if action.startswith("select_product_"):
        product_name = action.replace("select_product_", "")
        await select_product(query, user_id, product_name)
        return
    elif action.startswith("products_page_"):
        page = int(action.replace("products_page_", ""))
        await show_products(query, user_id, page)
        return
    
    # Множественный выбор
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
    
    # Материалы
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
    elif action.startswith("materials_page_"):
        page = int(action.replace("materials_page_", ""))
        session = get_session(user_id)
        session['materials_page'] = page - 1
        await show_materials_list(query, user_id, session.get('mode') == 'multi')
        return
    
    # Результаты
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
    
    logger.warning(f"Неизвестный callback: {action}")
    await query.edit_message_text("❌ Неизвестная команда")
