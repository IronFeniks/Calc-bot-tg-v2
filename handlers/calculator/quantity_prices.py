import logging
import math
from telegram import Update
from telegram.ext import ContextTypes
from keyboards.calculator import cancel_button, back_button
from utils.formatters import parse_int_input, parse_float_input, format_price
from price_db import get_drawing_price, save_drawing_price
from .session import get_session

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
            reply_markup=back_button(user_id, "products")
        )
        return
    
    session['qty'] = qty
    session['step'] = 'market_price'
    
    saved_price = get_drawing_price(product.get('Код', ''))
    price_text = format_price(saved_price) if saved_price > 0 else "не установлена"
    
    await update.message.reply_text(
        f"💰 РЫНОЧНАЯ ЦЕНА (1/2)\n\n"
        f"Изделие: {product.get('Наименование', '')}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите рыночную цену за 1 шт (ISK):\n"
        f"(только число, без ISK)\n\n"
        f"Текущая сохранённая цена: {price_text}\n"
        f"Пример: 4 767 760",
        reply_markup=cancel_button(user_id)
    )


async def process_market_price(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода рыночной цены для одиночного режима"""
    price = parse_float_input(text)
    if price is None or price < 0:
        await update.message.reply_text(
            "❌ Введите положительное число",
            reply_markup=cancel_button(user_id)
        )
        return
    
    session = get_session(user_id)
    session['market_price'] = price
    session['step'] = 'drawing_price'
    
    product = session.get('selected_product', {})
    saved_price = get_drawing_price(product.get('Код', ''))
    price_text = format_price(saved_price) if saved_price > 0 else "не установлена"
    
    await update.message.reply_text(
        f"💰 СТОИМОСТЬ ЧЕРТЕЖА (2/2)\n\n"
        f"Изделие: {product.get('Наименование', '')}\n"
        f"Кратность: {product.get('Кратность', 1)}\n\n"
        f"Введите стоимость чертежа (ISK):\n"
        f"(сохраняется для будущих расчётов)\n\n"
        f"Текущая сохранённая цена: {price_text}\n"
        f"Пример: 5 454",
        reply_markup=cancel_button(user_id)
    )


async def process_drawing_price(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода стоимости чертежа для одиночного режима"""
    price = parse_float_input(text)
    if price is None or price < 0:
        await update.message.reply_text(
            "❌ Введите положительное число",
            reply_markup=cancel_button(user_id)
        )
        return
    
    session = get_session(user_id)
    session['drawing_price'] = price
    
    product = session.get('selected_product', {})
    save_drawing_price(product.get('Код', ''), price)
    
    # Переходим к расчёту материалов
    from .materials import calculate_single_materials
    await calculate_single_materials(update, user_id)


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
    
    session['multi_products_data'].append(product_data)
    
    # Переходим к следующему изделию
    session['current_product_index'] += 1
    
    from .parameters import process_next_multi_product
    await process_next_multi_product(update, user_id)
