import logging
import math
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from keyboards.calculator import cancel_button, back_button, back_with_skip_button
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
        reply_markup=back_with_skip_button(user_id, "quantity", "skip_market_price")
    )


async def skip_market_price(query: CallbackQuery, user_id: int):
    """Пропуск ввода рыночной цены (использовать сохранённую)"""
    session = get_session(user_id)
    product = session.get('selected_product', {})
    
    saved_price = get_market_price(product.get('Код', ''))
    
    if saved_price <= 0:
        await query.answer("❌ Нет сохранённой цены. Введите цену вручную.", show_alert=True)
        return
    
    session['market_price'] = saved_price
    session['step'] = 'drawing_price'
    
    saved_drawing_price = get_drawing_price(product.get('Код', ''))
    price_text = format_price(saved_drawing_price) if saved_drawing_price > 0 else "не установлена"
    
    logger.info(f"✅ Рыночная цена пропущена, используется сохранённая: {saved_price}")
    
    await query.edit_message_text(
        f"💰 СТОИМОСТЬ ЧЕРТЕЖА (2/2)\n\n"
        f"✅ Рыночная цена: {format_price(saved_price)} (из базы)\n\n"
        f"Изделие: {product.get('Наименование', '')}\n"
        f"Кратность: {product.get('Кратность', 1)}\n\n"
        f"Введите стоимость чертежа (ISK):\n"
        f"(сохраняется для будущих расчётов)\n\n"
        f"Текущая сохранённая цена: {price_text}\n"
        f"Пример: 5 454",
        reply_markup=back_with_skip_button(user_id, "market_price", "skip_drawing_price")
    )


async def process_market_price(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода рыночной цены для одиночного режима"""
    price = parse_float_input(text)
    if price is None or price < 0:
        await update.message.reply_text(
            "❌ Введите положительное число",
            reply_markup=back_with_skip_button(user_id, "quantity", "skip_market_price")
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
        reply_markup=back_with_skip_button(user_id, "market_price", "skip_drawing_price")
    )


async def process_drawing_price(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода стоимости чертежа для одиночного режима"""
    price = parse_float_input(text)
    if price is None or price < 0:
        await update.message.reply_text(
            "❌ Введите положительное число",
            reply_markup=back_with_skip_button(user_id, "market_price", "skip_drawing_price")
        )
        return
    
    await _finalize_drawing_price(update, user_id, price)


async def skip_drawing_price(query: CallbackQuery, user_id: int):
    """Пропуск ввода стоимости чертежа (использовать сохранённую)"""
    session = get_session(user_id)
    product = session.get('selected_product', {})
    
    saved_price = get_drawing_price(product.get('Код', ''))
    
    if saved_price <= 0:
        await query.answer("❌ Нет сохранённой цены чертежа. Введите цену вручную.", show_alert=True)
        return
    
    logger.info(f"✅ Цена чертежа пропущена, используется сохранённая: {saved_price}")
    
    await _finalize_drawing_price(query, user_id, saved_price, is_callback=True)


async def _finalize_drawing_price(update_obj, user_id: int, price: float, is_callback: bool = False):
    """Завершение ввода цены чертежа и переход к выбору режима или расчёту"""
    session = get_session(user_id)
    session['drawing_price'] = price
    
    efficiency = session.get('efficiency')
    if efficiency is None:
        logger.error(f"efficiency is None для пользователя {user_id}")
        text = "❌ Ошибка: не задана эффективность. Пожалуйста, начните расчёт занов
