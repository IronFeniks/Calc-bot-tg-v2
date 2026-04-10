import logging
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from keyboards.calculator import cancel_button, back_button, back_with_skip_button
from utils.formatters import parse_float_input
from excel_handler import get_excel_handler
from .session import get_session

logger = logging.getLogger(__name__)


async def check_product_has_nodes(product_code: str) -> bool:
    """Проверяет, есть ли у изделия узлы в составе"""
    excel = get_excel_handler()
    if not excel:
        return False
    specs = excel.get_specifications(product_code)
    for spec in specs:
        child = excel.get_product_by_code(spec['child'])
        if child and child.get('Тип', '').lower() == 'узел':
            return True
    return False


async def process_efficiency(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода эффективности для одиночного режима"""
    efficiency = parse_float_input(text)
    if efficiency is None or efficiency < 50 or efficiency > 150:
        await update.message.reply_text(
            "❌ Введите число от 50 до 150 (процентов)",
            reply_markup=back_with_skip_button(user_id, "products", "skip_efficiency")
        )
        return
    
    session = get_session(user_id)
    session['efficiency'] = efficiency
    session['step'] = 'tax'
    
    logger.info(f"✅ Эффективность сохранена: {efficiency} для пользователя {user_id}")
    
    await update.message.reply_text(
        f"📊 ПАРАМЕТРЫ РАСЧЁТА (2/2)\n\n"
        f"Введите ставку налога (%):\n"
        f"(налог рассчитывается только при положительной прибыли)\n\n"
        f"Пример: 20\n\n"
        f"По умолчанию: 20%",
        reply_markup=back_with_skip_button(user_id, "efficiency", "skip_tax")
    )


async def skip_efficiency(query: CallbackQuery, user_id: int):
    """Пропуск ввода эффективности (значение по умолчанию = 150)"""
    session = get_session(user_id)
    session['efficiency'] = 150
    session['step'] = 'tax'
    
    logger.info(f"✅ Эффективность пропущена, установлено значение 150 для пользователя {user_id}")
    
    await query.edit_message_text(
        f"📊 ПАРАМЕТРЫ РАСЧЁТА (2/2)\n\n"
        f"✅ Эффективность: 150% (по умолчанию)\n\n"
        f"Введите ставку налога (%):\n"
        f"(налог рассчитывается только при положительной прибыли)\n\n"
        f"Пример: 20\n\n"
        f"По умолчанию: 20%",
        reply_markup=back_with_skip_button(user_id, "efficiency", "skip_tax")
    )


async def process_tax(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода налога для одиночного режима"""
    tax = parse_float_input(text)
    if tax is None or tax < 0 or tax > 100:
        await update.message.reply_text(
            "❌ Введите число от 0 до 100 (процентов)",
            reply_markup=back_with_skip_button(user_id, "efficiency", "skip_tax")
        )
        return
    
    session = get_session(user_id)
    session['tax'] = tax
    session['step'] = 'quantity'
    
    product = session.get('selected_product', {})
    multiplicity = product.get('Кратность', 1)
    
    logger.info(f"✅ Налог сохранён: {tax} для пользователя {user_id}")
    
    await update.message.reply_text(
        f"📦 КОЛИЧЕСТВО\n\n"
        f"Изделие: {product.get('Наименование', '')}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите количество продукции (шт):\n"
        f"(должно быть кратно {multiplicity})",
        reply_markup=back_button(user_id, "tax")
    )


async def skip_tax(query: CallbackQuery, user_id: int):
    """Пропуск ввода налога (значение по умолчанию = 20)"""
    session = get_session(user_id)
    session['tax'] = 20
    session['step'] = 'quantity'
    
    product = session.get('selected_product', {})
    multiplicity = product.get('Кратность', 1)
    
    logger.info(f"✅ Налог пропущен, установлено значение 20 для пользователя {user_id}")
    
    await query.edit_message_text(
        f"📦 КОЛИЧЕСТВО\n\n"
        f"✅ Налог: 20% (по умолчанию)\n\n"
        f"Изделие: {product.get('Наименование', '')}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите количество продукции (шт):\n"
        f"(должно быть кратно {multiplicity})",
        reply_markup=back_button(user_id, "tax")
    )


async def process_multi_efficiency(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода эффективности для множественного режима"""
    efficiency = parse_float_input(text)
    if efficiency is None or efficiency < 50 or efficiency > 150:
        await update.message.reply_text(
            "❌ Введите число от 50 до 150 (процентов)",
            reply_markup=back_with_skip_button(user_id, "multi_select", "skip_multi_efficiency")
        )
        return
    
    session = get_session(user_id)
    session['efficiency'] = efficiency
    session['step'] = 'multi_tax'
    
    logger.info(f"✅ Эффективность сохранена для множественного режима: {efficiency} для пользователя {user_id}")
    
    await update.message.reply_text(
        f"📊 ПАРАМЕТРЫ РАСЧЁТА (2/2)\n\n"
        f"Введите ставку налога (%):\n"
        f"(налог рассчитывается только при положительной прибыли)\n\n"
        f"Пример: 20\n\n"
        f"По умолчанию: 20%",
        reply_markup=back_with_skip_button(user_id, "multi_efficiency", "skip_multi_tax")
    )


async def skip_multi_efficiency(query: CallbackQuery, user_id: int):
    """Пропуск ввода эффективности для множественного режима"""
    session = get_session(user_id)
    session['efficiency'] = 150
    session['step'] = 'multi_tax'
    
    logger.info(f"✅ Эффективность пропущена (множественный), установлено 150 для пользователя {user_id}")
    
    await query.edit_message_text(
        f"📊 ПАРАМЕТРЫ РАСЧЁТА (2/2)\n\n"
        f"✅ Эффективность: 150% (по умолчанию)\n\n"
        f"Введите ставку налога (%):\n"
        f"(налог рассчитывается только при положительной прибыли)\n\n"
        f"Пример: 20\n\n"
        f"По умолчанию: 20%",
        reply_markup=back_with_skip_button(user_id, "multi_efficiency", "skip_multi_tax")
    )


async def process_multi_tax(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода налога для множественного режима"""
    tax = parse_float_input(text)
    if tax is None or tax < 0 or tax > 100:
        await update.message.reply_text(
            "❌ Введите число от 0 до 100 (процентов)",
            reply_markup=back_with_skip_button(user_id, "multi_efficiency", "skip_multi_tax")
        )
        return
    
    session = get_session(user_id)
    session['tax'] = tax
    
    selected_names = session.get('selected_products', [])
    if not selected_names:
        await update.message.reply_text(
            "❌ Нет выбранных изделий",
            reply_markup=back_button(user_id, "categories")
        )
        return
    
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
    
    logger.info(f"✅ Налог сохранён для множественного режима: {tax}, загружено {len(products)} изделий")
    
    # Запрашиваем количество для первого изделия
    product = products[0]
    session['current_multi_product'] = product
    multiplicity = product.get('Кратность', 1)
    
    await update.message.reply_text(
        f"📦 КОЛИЧЕСТВО (1/{len(products)})\n\n"
        f"Изделие: {product['Наименование']}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите количество продукции (шт):\n"
        f"(должно быть кратно {multiplicity})",
        reply_markup=back_button(user_id, "multi_tax")
    )


async def skip_multi_tax(query: CallbackQuery, user_id: int):
    """Пропуск ввода налога для множественного режима"""
    session = get_session(user_id)
    session['tax'] = 20
    
    selected_names = session.get('selected_products', [])
    if not selected_names:
        await query.edit_message_text(
            "❌ Нет выбранных изделий",
            reply_markup=back_button(user_id, "categories")
        )
        return
    
    excel = get_excel_handler()
    products = []
    for name in selected_names:
        product = excel.get_product_by_name(name)
        if product:
            products.append(product)
        else:
            logger.warning(f"Изделие не найдено: {name}")
    
    if not products:
        await query.edit_message_text(
            "❌ Не удалось загрузить выбранные изделия",
            reply_markup=back_button(user_id, "categories")
        )
        return
    
    session['multi_products'] = products
    session['current_product_index'] = 0
    session['multi_products_data'] = []
    session['step'] = 'multi_quantity'
    
    logger.info(f"✅ Налог пропущен (множественный), установлено 20 для пользователя {user_id}")
    
    # Запрашиваем количество для первого изделия
    product = products[0]
    session['current_multi_product'] = product
    multiplicity = product.get('Кратность', 1)
    
    await query.edit_message_text(
        f"📦 КОЛИЧЕСТВО (1/{len(products)})\n\n"
        f"✅ Налог: 20% (по умолчанию)\n\n"
        f"Изделие: {product['Наименование']}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите количество продукции (шт):\n"
        f"(должно быть кратно {multiplicity})",
        reply_markup=back_button(user_id, "multi_tax")
    )


async def process_next_multi_product(update_obj, user_id: int, is_callback: bool = False):
    """Ввод параметров для следующего изделия (множественный режим)"""
    session = get_session(user_id)
    products = session.get('multi_products', [])
    index = session.get('current_product_index', 0)
    total = len(products)
    
    if index >= total:
        logger.info(f"Все {total} изделий обработаны, переход к расчёту материалов")
        from .materials import calculate_multi_materials
        await calculate_multi_materials(update_obj, user_id)
        return
    
    product = products[index]
    session['current_multi_product'] = product
    
    multiplicity = product.get('Кратность', 1)
    
    logger.info(f"📦 Запрос количества для {product['Наименование']} ({index + 1}/{total})")
    
    text = f"📦 КОЛИЧЕСТВО ({index + 1}/{total})\n\n"
    text += f"Изделие: {product['Наименование']}\n"
    text += f"Кратность: {multiplicity}\n\n"
    text += f"Введите количество продукции (шт):\n"
    text += f"(должно быть кратно {multiplicity})"
    
    if is_callback:
        await update_obj.edit_message_text(text, reply_markup=back_button(user_id, "multi_tax"))
    else:
        await update_obj.message.reply_text(text, reply_markup=back_button(user_id, "multi_tax"))


# ==================== ФУНКЦИИ ДЛЯ КНОПКИ "НАЗАД" ====================

async def back_to_efficiency(query: CallbackQuery, user_id: int):
    """Возврат к вводу эффективности"""
    session = get_session(user_id)
    session['step'] = 'efficiency'
    
    await query.edit_message_text(
        f"📊 ПАРАМЕТРЫ РАСЧЁТА (1/2)\n\n"
        f"Введите эффективность производства (%):\n"
        f"(влияет на расход материалов)\n\n"
        f"Пример: 110\n\n"
        f"По умолчанию: 150%",
        reply_markup=back_with_skip_button(user_id, "products", "skip_efficiency")
    )


async def back_to_tax(query: CallbackQuery, user_id: int):
    """Возврат к вводу налога"""
    session = get_session(user_id)
    session['step'] = 'tax'
    
    await query.edit_message_text(
        f"📊 ПАРАМЕТРЫ РАСЧЁТА (2/2)\n\n"
        f"Введите ставку налога (%):\n"
        f"(налог рассчитывается только при положительной прибыли)\n\n"
        f"Пример: 20\n\n"
        f"По умолчанию: 20%",
        reply_markup=back_with_skip_button(user_id, "efficiency", "skip_tax")
    )


async def back_to_multi_efficiency(query: CallbackQuery, user_id: int):
    """Возврат к вводу эффективности для множественного режима"""
    session = get_session(user_id)
    session['step'] = 'multi_efficiency'
    
    await query.edit_message_text(
        f"📊 ПАРАМЕТРЫ РАСЧЁТА (1/2)\n\n"
        f"Введите эффективность производства (%):\n"
        f"(общая для всех изделий)\n\n"
        f"Пример: 110\n\n"
        f"По умолчанию: 150%",
        reply_markup=back_with_skip_button(user_id, "multi_select", "skip_multi_efficiency")
    )


async def back_to_multi_tax(query: CallbackQuery, user_id: int):
    """Возврат к вводу налога для множественного режима"""
    session = get_session(user_id)
    session['step'] = 'multi_tax'
    
    await query.edit_message_text(
        f"📊 ПАРАМЕТРЫ РАСЧЁТА (2/2)\n\n"
        f"Введите ставку налога (%):\n"
        f"(налог рассчитывается только при положительной прибыли)\n\n"
        f"Пример: 20\n\n"
        f"По умолчанию: 20%",
        reply_markup=back_with_skip_button(user_id, "multi_efficiency", "skip_multi_tax")
    )
