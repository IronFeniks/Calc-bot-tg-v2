import logging
import math
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from keyboards.calculator import cancel_button, back_button, back_with_skip_button, calculation_mode_keyboard
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
        text = "❌ Ошибка: не задана эффективность. Пожалуйста, начните расчёт заново с /start"
        if is_callback:
            await update_obj.edit_message_text(text, reply_markup=cancel_button(user_id))
        else:
            await update_obj.message.reply_text(text, reply_markup=cancel_button(user_id))
        return
    
    tax = session.get('tax')
    if tax is None:
        logger.error(f"tax is None для пользователя {user_id}")
        text = "❌ Ошибка: не задан налог. Пожалуйста, начните расчёт заново с /start"
        if is_callback:
            await update_obj.edit_message_text(text, reply_markup=cancel_button(user_id))
        else:
            await update_obj.message.reply_text(text, reply_markup=cancel_button(user_id))
        return
    
    product = session.get('selected_product', {})
    save_drawing_price(product.get('Код', ''), price)
    
    has_nodes = await check_product_has_nodes(product.get('Код', ''))
    session['has_nodes'] = has_nodes
    
    logger.info(f"✅ Цена чертежа сохранена: {price}, efficiency={efficiency}, tax={tax}, has_nodes={has_nodes}")
    
    if has_nodes:
        session['step'] = 'mode_selection'
        text = ("📊 ВЫБОР РЕЖИМА РАСЧЁТА МАТЕРИАЛОВ\n\n"
                "Как будем считать?\n\n"
                "🏭 Как в игре\n"
                "   Показывает материалы из изделия и узлы.\n"
                "   Узлы покупаются готовыми, их материалы не суммируются.\n\n"
                "📊 По материалам\n"
                "   Суммирует все материалы (из изделия + из узлов).\n"
                "   Показывает только итоговый список материалов.\n"
                "   Узлы производятся самостоятельно.\n\n"
                "Выберите режим:")
        reply_markup = calculation_mode_keyboard(user_id, is_multi=False)
    else:
        session['calculation_mode'] = 'buy_nodes'
        from .materials import calculate_single_materials
        if is_callback:
            await calculate_single_materials(update_obj, user_id)
        else:
            await calculate_single_materials(update_obj, user_id)
        return
    
    if is_callback:
        await update_obj.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update_obj.message.reply_text(text, reply_markup=reply_markup)


# ==================== ФУНКЦИИ ДЛЯ КНОПКИ "НАЗАД" ====================

async def back_to_quantity(query: CallbackQuery, user_id: int):
    """Возврат к вводу количества"""
    session = get_session(user_id)
    product = session.get('selected_product', {})
    multiplicity = product.get('Кратность', 1)
    session['step'] = 'quantity'
    
    await query.edit_message_text(
        f"📦 КОЛИЧЕСТВО\n\n"
        f"Изделие: {product.get('Наименование', '')}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите количество продукции (шт):\n"
        f"(должно быть кратно {multiplicity})",
        reply_markup=back_button(user_id, "tax")
    )


async def back_to_market_price(query: CallbackQuery, user_id: int):
    """Возврат к вводу рыночной цены"""
    session = get_session(user_id)
    product = session.get('selected_product', {})
    multiplicity = product.get('Кратность', 1)
    session['step'] = 'market_price'
    
    saved_price = get_market_price(product.get('Код', ''))
    price_text = format_price(saved_price) if saved_price > 0 else "не установлена"
    
    await query.edit_message_text(
        f"💰 РЫНОЧНАЯ ЦЕНА (1/2)\n\n"
        f"Изделие: {product.get('Наименование', '')}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите рыночную цену за 1 шт (ISK):\n"
        f"(только число, без ISK)\n\n"
        f"Текущая сохранённая цена: {price_text}\n"
        f"Пример: 4 767 760",
        reply_markup=back_with_skip_button(user_id, "quantity", "skip_market_price")
    )


async def back_to_multi_quantity(query: CallbackQuery, user_id: int):
    """Возврат к вводу количества для множественного режима"""
    session = get_session(user_id)
    product = session.get('current_multi_product', {})
    current_index = session.get('current_product_index', 0)
    total_products = len(session.get('multi_products', []))
    multiplicity = product.get('Кратность', 1)
    session['step'] = 'multi_quantity'
    
    await query.edit_message_text(
        f"📦 КОЛИЧЕСТВО ({current_index + 1}/{total_products})\n\n"
        f"Изделие: {product['Наименование']}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите количество продукции (шт):\n"
        f"(должно быть кратно {multiplicity})",
        reply_markup=back_button(user_id, "multi_tax")
    )


async def back_to_multi_market_price(query: CallbackQuery, user_id: int):
    """Возврат к вводу рыночной цены для множественного режима"""
    session = get_session(user_id)
    product = session.get('current_multi_product', {})
    current_index = session.get('current_product_index', 0)
    total_products = len(session.get('multi_products', []))
    multiplicity = product.get('Кратность', 1)
    session['step'] = 'multi_market_price'
    
    saved_price = get_market_price(product.get('Код', ''))
    price_text = format_price(saved_price) if saved_price > 0 else "не установлена"
    
    await query.edit_message_text(
        f"💰 РЫНОЧНАЯ ЦЕНА ({current_index + 1}/{total_products})\n\n"
        f"Изделие: {product['Наименование']}\n"
        f"Кратность: {multiplicity}\n\n"
        f"Введите рыночную цену за 1 шт (ISK):\n"
        f"(только число, без ISK)\n\n"
        f"Текущая сохранённая цена: {price_text}\n"
        f"Пример: 4 767 760",
        reply_markup=back_with_skip_button(user_id, "multi_quantity", "skip_multi_market_price")
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
        reply_markup=back_with_skip_button(user_id, "multi_quantity", "skip_multi_market_price")
    )


async def skip_multi_market_price(query: CallbackQuery, user_id: int):
    """Пропуск ввода рыночной цены для множественного режима"""
    session = get_session(user_id)
    product = session.get('current_multi_product', {})
    current_index = session.get('current_product_index', 0)
    total_products = len(session.get('multi_products', []))
    
    saved_price = get_market_price(product.get('Код', ''))
    
    if saved_price <= 0:
        await query.answer("❌ Нет сохранённой цены. Введите цену вручную.", show_alert=True)
        return
    
    session['temp_market_price'] = saved_price
    session['step'] = 'multi_drawing_price'
    
    saved_drawing_price = get_drawing_price(product.get('Код', ''))
    price_text = format_price(saved_drawing_price) if saved_drawing_price > 0 else "не установлена"
    
    logger.info(f"✅ Рыночная цена пропущена (множественный): {saved_price}")
    
    await query.edit_message_text(
        f"💰 СТОИМОСТЬ ЧЕРТЕЖА ({current_index + 1}/{total_products})\n\n"
        f"✅ Рыночная цена: {format_price(saved_price)} (из базы)\n\n"
        f"Изделие: {product['Наименование']}\n"
        f"Кратность: {product.get('Кратность', 1)}\n\n"
        f"Введите стоимость чертежа (ISK):\n"
        f"(сохраняется для будущих расчётов)\n\n"
        f"Текущая сохранённая цена: {price_text}\n"
        f"Пример: 5 454",
        reply_markup=back_with_skip_button(user_id, "multi_market_price", "skip_multi_drawing_price")
    )


async def process_multi_market_price(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода рыночной цены для множественного режима"""
    price = parse_float_input(text)
    if price is None or price < 0:
        await update.message.reply_text(
            "❌ Введите положительное число",
            reply_markup=back_with_skip_button(user_id, "multi_quantity", "skip_multi_market_price")
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
    
    logger.info(f"💰 Рыночная цена для {product['Наименование']} сохранена: {price}")
    
    await update.message.reply_text(
        f"💰 СТОИМОСТЬ ЧЕРТЕЖА ({current_index + 1}/{total_products})\n\n"
        f"Изделие: {product['Наименование']}\n"
        f"Кратность: {product.get('Кратность', 1)}\n\n"
        f"Введите стоимость чертежа (ISK):\n"
        f"(сохраняется для будущих расчётов)\n\n"
        f"Текущая сохранённая цена: {price_text}\n"
        f"Пример: 5 454",
        reply_markup=back_with_skip_button(user_id, "multi_market_price", "skip_multi_drawing_price")
    )


async def process_multi_drawing_price(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обработка ввода стоимости чертежа для множественного режима"""
    price = parse_float_input(text)
    if price is None or price < 0:
        await update.message.reply_text(
            "❌ Введите положительное число",
            reply_markup=back_with_skip_button(user_id, "multi_market_price", "skip_multi_drawing_price")
        )
        return
    
    await _finalize_multi_drawing_price(update, user_id, price)


async def skip_multi_drawing_price(query: CallbackQuery, user_id: int):
    """Пропуск ввода стоимости чертежа для множественного режима"""
    session = get_session(user_id)
    product = session.get('current_multi_product', {})
    
    saved_price = get_drawing_price(product.get('Код', ''))
    
    if saved_price <= 0:
        await query.answer("❌ Нет сохранённой цены чертежа. Введите цену вручную.", show_alert=True)
        return
    
    logger.info(f"✅ Цена чертежа пропущена (множественный): {saved_price}")
    
    await _finalize_multi_drawing_price(query, user_id, saved_price, is_callback=True)


async def _finalize_multi_drawing_price(update_obj, user_id: int, price: float, is_callback: bool = False):
    """Завершение ввода цены чертежа для одного изделия в множественном режиме"""
    session = get_session(user_id)
    product = session.get('current_multi_product', {})
    current_index = session.get('current_product_index', 0)
    total_products = len(session.get('multi_products', []))
    
    efficiency = session.get('efficiency')
    if efficiency is None:
        logger.error(f"efficiency is None для пользователя {user_id} в множественном режиме")
        text = "❌ Ошибка: не задана эффективность. Пожалуйста, начните расчёт заново с /start"
        if is_callback:
            await update_obj.edit_message_text(text, reply_markup=cancel_button(user_id))
        else:
            await update_obj.message.reply_text(text, reply_markup=cancel_button(user_id))
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
        # Ещё есть изделия для ввода
        from .parameters import process_next_multi_product
        await process_next_multi_product(update_obj, user_id, is_callback=is_callback)
    else:
        # Все изделия обработаны, проверяем наличие узлов
        has_any_nodes = False
        for p_data in session['multi_products_data']:
            if await check_product_has_nodes(p_data['product'].get('Код', '')):
                has_any_nodes = True
                break
        
        if has_any_nodes:
            # Показываем выбор режима расчёта
            session['step'] = 'multi_mode_selection'
            text = ("📊 ВЫБОР РЕЖИМА РАСЧЁТА МАТЕРИАЛОВ\n\n"
                    "Как будем считать?\n\n"
                    "🏭 Как в игре\n"
                    "   Показывает материалы из изделий и узлы.\n"
                    "   Узлы покупаются готовыми, их материалы не суммируются.\n\n"
                    "📊 По материалам\n"
                    "   Суммирует все материалы (из изделий + из узлов).\n"
                    "   Показывает только итоговый список материалов.\n"
                    "   Узлы производятся самостоятельно.\n\n"
                    "Выберите режим:")
            from keyboards.calculator import calculation_mode_keyboard
            reply_markup = calculation_mode_keyboard(user_id, is_multi=True)
            
            if is_callback:
                await update_obj.edit_message_text(text, reply_markup=reply_markup)
            else:
                await update_obj.message.reply_text(text, reply_markup=reply_markup)
        else:
            # Нет узлов, сразу запускаем расчёт в режиме buy_nodes
            session['calculation_mode'] = 'buy_nodes'
            logger.info(f"✅ Все {total_products} изделий обработаны, переход к расчёту материалов (нет узлов)")
            from .materials import calculate_multi_materials
            await calculate_multi_materials(update_obj, user_id)
