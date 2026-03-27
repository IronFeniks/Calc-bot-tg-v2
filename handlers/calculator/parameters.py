import logging
from telegram import Update
from telegram.ext import ContextTypes
from keyboards.calculator import cancel_button, back_button
from utils.formatters import parse_float_input
from excel_handler import get_excel_handler
from .session import get_session

logger = logging.getLogger(__name__)


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
    
    logger.info(f"✅ Эффективность сохранена: {efficiency} для пользователя {user_id}")
    
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
    
    logger.info(f"✅ Эффективность сохранена для множественного режима: {efficiency} для пользователя {user_id}")
    
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
    
    await process_next_multi_product(update, user_id)


async def process_next_multi_product(update, user_id: int):
    """Ввод параметров для следующего изделия (множественный режим)"""
    session = get_session(user_id)
    products = session.get('multi_products', [])
    index = session.get('current_product_index', 0)
    total = len(products)
    
    if index >= total:
        # Все параметры введены — переходим к расчёту
        logger.info(f"Все {total} изделий обработаны, переход к расчёту материалов")
        from .materials import calculate_multi_materials
        await calculate_multi_materials(update, user_id)
        return
    
    product = products[index]
    session['current_multi_product'] = product
    
    multiplicity = product.get('Кратность', 1)
    
    logger.info(f"📦 Запрос количества для {product['Наименование']} ({index + 1}/{total})")
    
    await update.message.reply_text(
        f"📦 КОЛИЧЕСТВО ({index + 1}/{total})\n\n"
        f"Изделие: {product['Наименование']}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите количество продукции (шт):\n"
        f"(должно быть кратно {multiplicity})",
        reply_markup=cancel_button(user_id)
    )
