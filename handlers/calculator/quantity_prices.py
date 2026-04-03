import logging
import math
from telegram import Update
from telegram.ext import ContextTypes
from keyboards.calculator import cancel_button, back_button, calculation_mode_keyboard
from utils.formatters import parse_int_input, parse_float_input, format_price
from price_db import get_drawing_price, save_drawing_price, get_market_price, save_market_price
from .session import get_session
from .parameters import check_product_has_nodes

logger = logging.getLogger(__name__)


async def process_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода количества для одиночного режима"""
    qty = parse_int_input(text)
    session = get_session(user_id)
    product = session.get('selected_product', {})
    multiplicity = product.get('Кратность', 1)
    
    if qty is None or qty <= 0 or qty % multiplicity != 0:
        await update.message.reply_text(
            f"❌ Количество должно быть положительным целым числом, кратным {multiplicity}",
            reply_markup=back_button(user_id, "tax")
        )
        return
    
    session['qty'] = qty
    session['step'] = 'market_price'
    
    saved_market_price = get_market_price(product.get('Код', ''))
    price_text = format_price(saved_market_price) if saved_market_price > 0 else "не установлена"
    
    await update.message.reply_text(
        f"💰 РЫНОЧНАЯ ЦЕНА (1/2)\n\n"
        f"Изделие: {product.get('Наименование', '')}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите рыночную цену за 1 шт (ISK):\n"
        f"(только число, без ISK)\n\n"
        f"Текущая сохранённая цена: {price_text}\n"
        f"Пример: 4 767 760",
        reply_markup=back_button(user_id, "quantity")
    )


async def process_market_price(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода рыночной цены для одиночного режима"""
    price = parse_float_input(text)
    if price is None or price < 0:
        await update.message.reply_text(
            "❌ Введите положительное число",
            reply_markup=back_button(user_id, "quantity")
        )
        return
    
    session = get_session(user_id)
    session['market_price'] = price
    session['step'] = 'drawing_price'
    
    product = session.get('selected_product', {})
    save_market_price(product.get('Код', ''), price)
    
    saved_drawing_price = get_drawing_price(product.get('Код', ''))
    price_text = format_price(saved_drawing_price) if saved_drawing_price > 0 else "не установлена"
    
    await update.message.reply_text(
        f"💰 СТОИМОСТЬ ЧЕРТЕЖА (2/2)\n\n"
        f"Изделие: {product.get('Наименование', '')}\n"
        f"Кратность: {product.get('Кратность', 1)}\n\n"
        f"Введите стоимость чертежа (ISK):\n"
        f"(сохраняется для будущих расчётов)\n\n"
        f"Текущая сохранённая цена: {price_text}\n"
        f"Пример: 5 454",
        reply_markup=back_button(user_id, "market_price")
    )


async def process_drawing_price(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода стоимости чертежа для одиночного режима"""
    price = parse_float_input(text)
    if price is None or price < 0:
        await update.message.reply_text(
            "❌ Введите положительное число",
            reply_markup=back_button(user_id, "market_price")
        )
        return
    
    session = get_session(user_id)
    session['drawing_price'] = price
    
    efficiency = session.get('efficiency')
    if efficiency is None:
        logger.error(f"efficiency is None для пользователя {user_id}")
        await update.message.reply_text(
            "❌ Ошибка: не задана эффективность. Пожалуйста, начните расчёт заново с /start",
            reply_markup=cancel_button(user_id)
        )
        return
    
    tax = session.get('tax')
    if tax is None:
        logger.error(f"tax is None для пользователя {user_id}")
        await update.message.reply_text(
            "❌ Ошибка: не задан налог. Пожалуйста, начните расчёт заново с /start",
            reply_markup=cancel_button(user_id)
        )
        return
    
    product = session.get('selected_product', {})
    save_drawing_price(product.get('Код', ''), price)
    
    has_nodes = await check_product_has_nodes(product.get('Код', ''))
    session['has_nodes'] = has_nodes
    
    logger.info(f"✅ Цена чертежа сохранена: {price}, efficiency={efficiency}, tax={tax}, has_nodes={has_nodes}")
    
    if has_nodes:
        session['step'] = 'mode_selection'
        await update.message.reply_text(
            "📊 ВЫБОР РЕЖИМА РАСЧЁТА МАТЕРИАЛОВ\n\n"
            "Как будем считать?\n\n"
            "🏭 Как в игре\n"
            "   Показывает материалы из изделия и узлы.\n"
            "   Узлы покупаются готовыми, их материалы не суммируются.\n\n"
            "📊 По материалам\n"
            "   Суммирует все материалы (из изделия + из узлов).\n"
            "   Показывает только итоговый список материалов.\n"
            "   Узлы производятся самостоятельно.\n\n"
            "Выберите режим:",
            reply_markup=calculation_mode_keyboard(user_id)
        )
    else:
        session['calculation_mode'] = 'buy_nodes'
        from .materials import calculate_single_materials
        await calculate_single_materials(update, user_id)


async def back_to_quantity(update: Update, user_id: int):
    """Возврат к вводу количества"""
    session = get_session(user_id)
    product = session.get('selected_product', {})
    multiplicity = product.get('Кратность', 1)
    session['step'] = 'quantity'
    
    await update.message.reply_text(
        f"📦 КОЛИЧЕСТВО\n\n"
        f"Изделие: {product.get('Наименование', '')}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите количество продукции (шт):\n"
        f"(должно быть кратно {multiplicity})",
        reply_markup=back_button(user_id, "tax")
    )


async def back_to_market_price(update: Update, user_id: int):
    """Возврат к вводу рыночной цены"""
    session = get_session(user_id)
    product = session.get('selected_product', {})
    multiplicity = product.get('Кратность', 1)
    session['step'] = 'market_price'
    
    saved_price = get_market_price(product.get('Код', ''))
    price_text = format_price(saved_price) if saved_price > 0 else "не установлена"
    
    await update.message.reply_text(
        f"💰 РЫНОЧНАЯ ЦЕНА (1/2)\n\n"
        f"Изделие: {product.get('Наименование', '')}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите рыночную цену за 1 шт (ISK):\n"
        f"(только число, без ISK)\n\n"
        f"Текущая сохранённая цена: {price_text}\n"
        f"Пример: 4 767 760",
        reply_markup=back_button(user_id, "quantity")
    )


# ==================== МНОЖЕСТВЕННЫЙ РЕЖИМ ====================

async def process_multi_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода количества для множественного режима"""
    qty = parse_int_input(text)
    session = get_session(user_id)
    product = session.get('current_multi_product', {})
    multiplicity = product.get('Кратность', 1)
    current_index = session.get('current_product_index', 0)
    total_products = len(session.get('multi_products', []))
    
    if qty is None or qty <= 0 or qty % multiplicity != 0:
        await update.message.reply_text(
            f"❌ Количество должно быть положительным целым числом, кратным {multiplicity}",
            reply_markup=back_button(user_id, "multi_tax")
        )
        return
    
    session['temp_quantity'] = qty
    session['step'] = 'multi_market_price'
    
    saved_market_price = get_market_price(product.get('Код', ''))
    price_text = format_price(saved_market_price) if saved_market_price > 0 else "не установлена"
    
    logger.info(f"📦 Количество для {product['Наименование']} сохранено: {qty}, переход к рыночной цене")
    
    await update.message.reply_text(
        f"💰 РЫНОЧНАЯ ЦЕНА ({current_index + 1}/{total_products})\n\n"
        f"Изделие: {product['Наименование']}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите рыночную цену за 1 шт (ISK):\n"
        f"(только число, без ISK)\n\n"
        f"Текущая сохранённая цена: {price_text}\n"
        f"Пример: 4 767 760",
        reply_markup=back_button(user_id, "multi_quantity")
    )


async def process_multi_market_price(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода рыночной цены для множественного режима"""
    price = parse_float_input(text)
    if price is None or price < 0:
        await update.message.reply_text(
            "❌ Введите положительное число",
            reply_markup=back_button(user_id, "multi_quantity")
        )
        return
    
    session = get_session(user_id)
    session['temp_market_price'] = price
    session['step'] = 'multi_drawing_price'
    
    product = session.get('current_multi_product', {})
    current_index = session.get('current_product_index', 0)
    total_products = len(session.get('multi_products', []))
    
    save_market_price(product.get('Код', ''), price)
    
    saved_drawing_price = get_drawing_price(product.get('Код', ''))
    price_text = format_price(saved_drawing_price) if saved_drawing_price > 0 else "не установлена"
    
    logger.info(f"💰 Рыночная цена для {product['Наименование']} сохранена: {price}, переход к стоимости чертежа")
    
    await update.message.reply_text(
        f"💰 СТОИМОСТЬ ЧЕРТЕЖА ({current_index + 1}/{total_products})\n\n"
        f"Изделие: {product['Наименование']}\n"
        f"Кратность: {product.get('Кратность', 1)}\n\n"
        f"Введите стоимость чертежа (ISK):\n"
        f"(сохраняется для будущих расчётов)\n\n"
        f"Текущая сохранённая цена: {price_text}\n"
        f"Пример: 5 454",
        reply_markup=back_button(user_id, "multi_market_price")
    )


async def process_multi_drawing_price(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода стоимости чертежа для множественного режима"""
    price = parse_float_input(text)
    if price is None or price < 0:
        await update.message.reply_text(
            "❌ Введите положительное число",
            reply_markup=back_button(user_id, "multi_market_price")
        )
        return
    
    session = get_session(user_id)
    product = session.get('current_multi_product', {})
    current_index = session.get('current_product_index', 0)
    total_products = len(session.get('multi_products', []))
    
    efficiency = session.get('efficiency')
    if efficiency is None:
        logger.error(f"efficiency is None для пользователя {user_id} в множественном режиме")
        await update.message.reply_text(
            "❌ Ошибка: не задана эффективность. Пожалуйста, начните расчёт заново с /start",
            reply_markup=cancel_button(user_id)
        )
        return
    
    save_drawing_price(product.get('Код', ''), price)
    
    product_data = {
        'product': product,
        'quantity': session.get('temp_quantity'),
        'market_price': session.get('temp_market_price'),
        'drawing_price': price
    }
    
    session['multi_products_data'].append(product_data)
    session['current_product_index'] = current_index + 1
    
    logger.info(f"✅ Данные для {product['Наименование']} сохранены ({current_index + 1}/{total_products})")
    
    if session['current_product_index'] < total_products:
        from .parameters import process_next_multi_product
        await process_next_multi_product(update, user_id)
    else:
        logger.info(f"✅ Все {total_products} изделий обработаны, переход к расчёту материалов")
        from .materials import calculate_multi_materials
        await calculate_multi_materials(update, user_id)


async def back_to_multi_quantity(update: Update, user_id: int):
    """Возврат к вводу количества для множественного режима"""
    session = get_session(user_id)
    product = session.get('current_multi_product', {})
    current_index = session.get('current_product_index', 0)
    total_products = len(session.get('multi_products', []))
    multiplicity = product.get('Кратность', 1)
    session['step'] = 'multi_quantity'
    
    await update.message.reply_text(
        f"📦 КОЛИЧЕСТВО ({current_index + 1}/{total_products})\n\n"
        f"Изделие: {product['Наименование']}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите количество продукции (шт):\n"
        f"(должно быть кратно {multiplicity})",
        reply_markup=back_button(user_id, "multi_tax")
    )


async def back_to_multi_market_price(update: Update, user_id: int):
    """Возврат к вводу рыночной цены для множественного режима"""
    session = get_session(user_id)
    product = session.get('current_multi_product', {})
    current_index = session.get('current_product_index', 0)
    total_products = len(session.get('multi_products', []))
    multiplicity = product.get('Кратность', 1)
    session['step'] = 'multi_market_price'
    
    saved_price = get_market_price(product.get('Код', ''))
    price_text = format_price(saved_price) if saved_price > 0 else "не установлена"
    
    await update.message.reply_text(
        f"💰 РЫНОЧНАЯ ЦЕНА ({current_index + 1}/{total_products})\n\n"
        f"Изделие: {product['Наименование']}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите рыночную цену за 1 шт (ISK):\n"
        f"(только число, без ISK)\n\n"
        f"Текущая сохранённая цена: {price_text}\n"
        f"Пример: 4 767 760",
        reply_markup=back_button(user_id, "multi_quantity")
    )
