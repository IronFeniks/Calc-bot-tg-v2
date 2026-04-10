import logging
import math
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from keyboards.calculator import result_keyboard, explanation_keyboard, cancel_button, comparison_keyboard
from utils.formatters import (
    format_number, format_price, format_material_result_line,
    format_node_result_line, format_leftover_line, format_explanation
)
from utils.calculations import calculate_tax
from .session import get_session, clear_session
from .parameters import check_product_has_nodes

logger = logging.getLogger(__name__)


async def _send_result_message(update_obj, text: str, reply_markup, parse_mode: str = 'Markdown'):
    """
    Универсальная функция отправки результата с проверкой длины сообщения
    Telegram ограничивает длину сообщения 4096 символами
    """
    TELEGRAM_MAX_LENGTH = 4096
    WARNING_TEXT = "\n\n⚠️ *Сообщение обрезано из-за ограничения Telegram.*"
    
    if len(text) > TELEGRAM_MAX_LENGTH:
        max_text_length = TELEGRAM_MAX_LENGTH - len(WARNING_TEXT)
        text = text[:max_text_length] + WARNING_TEXT
        logger.warning(f"Сообщение обрезано: итоговая длина {len(text)} символов")
    
    if isinstance(update_obj, CallbackQuery):
        try:
            await update_obj.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await update_obj.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    elif hasattr(update_obj, 'message') and update_obj.message:
        await update_obj.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    elif hasattr(update_obj, 'reply_text'):
        await update_obj.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    else:
        logger.error(f"Не удалось отправить результат: неизвестный тип {type(update_obj)}")


async def calculate_final_result(update_obj, user_id: int, is_comparison: bool = False):
    """Финальный расчёт и вывод результатов"""
    session = get_session(user_id)
    mode = session.get('mode')
    tax_rate = session.get('tax', 0)
    calculation_mode = session.get('calculation_mode', 'buy_nodes')
    
    is_second_pass = session.get('is_comparison_second_pass', False)
    
    if not is_comparison and not is_second_pass and session.get('first_calculation_completed') is None:
        session['first_calculation_mode'] = calculation_mode
        session['first_calculation_tax'] = tax_rate
        session['first_calculation_completed'] = True
        logger.info(f"🔧 ПЕРВЫЙ расчёт сохранён: mode_raw={calculation_mode}")
    elif is_second_pass:
        logger.info(f"🔧 ВТОРОЙ проход сравнения, режим={calculation_mode}, НЕ перезаписываем первый расчёт")
    
    if mode == 'single':
        await _calculate_single_result(update_obj, user_id, tax_rate, calculation_mode, is_comparison, is_second_pass)
        if is_second_pass:
            await show_comparison_results(update_obj, user_id)
            session['is_comparison_second_pass'] = False
    else:
        await _calculate_multi_result(update_obj, user_id, tax_rate, calculation_mode, is_comparison)


async def _calculate_single_result(update_obj, user_id: int, tax_rate: float, calculation_mode: str, 
                                    is_comparison: bool, is_second_pass: bool = False):
    """Расчёт и вывод результата для одиночного режима"""
    session = get_session(user_id)
    product = session.get('selected_product', {})
    quantity = session.get('qty', 0)
    market_price = session.get('market_price', 0)
    drawing_price = session.get('drawing_price', 0)
    materials_list = session.get('materials_list', [])
    nodes_list = session.get('nodes_list', [])
    drawings_list = session.get('drawings_list', [])
    drawings_needed = session.get('single_product_detail', {}).get('drawings_needed', 1)
    
    materials_cost = 0
    for m in materials_list:
        cost = m['qty'] * m.get('price', 0)
        m['cost'] = cost
        materials_cost += cost
    
    prod_price_str = product.get('Цена производства', '0 ISK')
    try:
        prod_price = float(str(prod_price_str).replace(' ISK', '').replace(' ', ''))
    except:
        prod_price = 0
    production_cost = prod_price * drawings_needed
    
    drawings_cost = drawing_price * drawings_needed
    
    nodes_cost = 0
    node_production_cost = 0
    
    if calculation_mode == 'buy_nodes':
        for node in nodes_list:
            node_cost = node['needed_qty'] * node.get('price', 0)
            nodes_cost += node_cost
    else:
        for node in nodes_list:
            node_production_cost += node.get('total_cost', 0)
        for drawing in drawings_list:
            drawings_cost += drawing['drawings'] * drawing.get('price', 0)
    
    total_cost = materials_cost + production_cost + drawings_cost + nodes_cost + node_production_cost
    revenue = market_price * quantity
    profit_before_tax = revenue - total_cost
    tax = calculate_tax(profit_before_tax, tax_rate)
    profit_after_tax = profit_before_tax - tax
    per_unit_cost = total_cost / quantity if quantity > 0 else 0
    per_unit_profit = profit_after_tax / quantity if quantity > 0 else 0
    
    mode_name = "покупка узлов" if calculation_mode == 'buy_nodes' else "производство узлов"
    text = f"📊 РЕЗУЛЬТАТЫ РАСЧЕТА\n\n"
    text += f"🏷️ ИЗДЕЛИЕ: {product.get('Наименование', '')}\n"
    text += f"📂 КАТЕГОРИЯ: {product.get('Категории', '')}\n"
    text += f"📦 КОЛИЧЕСТВО: {format_number(quantity)} шт\n"
    text += f"⚙️ ЭФФЕКТИВНОСТЬ: {session.get('efficiency', 150)}%\n"
    text += f"🏛️ НАЛОГ: {tax_rate}%\n"
    text += f"🎯 РЕЖИМ: {mode_name}\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    max_materials_display = 15
    if len(materials_list) > max_materials_display:
        text += f"📦 МАТЕРИАЛЫ (показаны первые {max_materials_display} из {len(materials_list)}):\n"
        display_materials = materials_list[:max_materials_display]
    else:
        text += "📦 МАТЕРИАЛЫ:\n"
        display_materials = materials_list
    
    for i, m in enumerate(display_materials, 1):
        text += format_material_result_line(i, m['name'], m['qty'], m.get('price', 0), m.get('cost', 0)) + "\n"
    
    if len(materials_list) > max_materials_display:
        text += f"... и ещё {len(materials_list) - max_materials_display} материалов\n"
    text += "\n"
    
    max_nodes_display = 10
    
    if calculation_mode == 'buy_nodes' and nodes_list:
        if len(nodes_list) > max_nodes_display:
            text += f"🔩 УЗЛЫ (покупка, показаны первые {max_nodes_display} из {len(nodes_list)}):\n"
            display_nodes = nodes_list[:max_nodes_display]
        else:
            text += "🔩 УЗЛЫ (покупка):\n"
            display_nodes = nodes_list
        
        for i, node in enumerate(display_nodes, 1):
            text += f"{i}. {node['name']}: нужно {format_number(node['needed_qty'])} шт | цена: {format_price(node.get('price', 0))}\n"
        
        if len(nodes_list) > max_nodes_display:
            text += f"... и ещё {len(nodes_list) - max_nodes_display} узлов\n"
        text += "\n"
        
    elif not calculation_mode == 'buy_nodes' and drawings_list:
        if len(drawings_list) > max_nodes_display:
            text += f"📄 ЧЕРТЕЖИ УЗЛОВ (показаны первые {max_nodes_display} из {len(drawings_list)}):\n"
            display_drawings = drawings_list[:max_nodes_display]
        else:
            text += "📄 ЧЕРТЕЖИ УЗЛОВ:\n"
            display_drawings = drawings_list
        
        for i, drawing in enumerate(display_drawings, 1):
            text += f"{i}. {drawing['name']}: нужно {format_number(drawing['drawings'])} чертежей | цена: {format_price(drawing.get('price', 0))}\n"
        
        if len(drawings_list) > max_nodes_display:
            text += f"... и ещё {len(drawings_list) - max_nodes_display} чертежей\n"
        text += "\n"
        
        if node_production_cost > 0:
            text += "🏭 ПРОИЗВОДСТВО УЗЛОВ (фиксированная стоимость):\n"
            for node in nodes_list[:max_nodes_display]:
                text += f"• {node['name']}: {format_number(node['drawings'])} чертежей x {format_price(node['price_per_drawing'])} = {format_price(node['total_cost'])}\n"
            if len(nodes_list) > max_nodes_display:
                text += f"... и ещё {len(nodes_list) - max_nodes_display} узлов\n"
            text += "\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += _format_total_result_list(
        materials_cost, production_cost, drawings_cost + nodes_cost + node_production_cost,
        total_cost, revenue, profit_before_tax, tax, profit_after_tax,
        per_unit_cost, per_unit_profit
    )
    
    # Определяем, показывать ли кнопку сравнения (ДОЛЖНО БЫТЬ ОПРЕДЕЛЕНО ДО ИСПОЛЬЗОВАНИЯ)
    show_comparison = not is_comparison and not is_second_pass and session.get('has_nodes', False)
    
    if not is_comparison and not is_second_pass:
        session['first_calculation_result'] = text
        session['first_calculation_data'] = {
            'materials_cost': materials_cost,
            'production_cost': production_cost,
            'drawings_cost': drawings_cost,
            'nodes_cost': nodes_cost,
            'node_production_cost': node_production_cost,
            'total_cost': total_cost,
            'revenue': revenue,
            'profit_before_tax': profit_before_tax,
            'tax': tax,
            'profit_after_tax': profit_after_tax
        }
        session['first_calculation_mode_name'] = mode_name
        session['first_calculation_mode_raw'] = calculation_mode
        session['product_name'] = product.get('Наименование', '')
        session['quantity'] = quantity
        session['has_nodes'] = await check_product_has_nodes(product.get('Код', ''))
        logger.info(f"🔧 ПЕРВЫЙ расчёт: mode_name={mode_name}, mode_raw={calculation_mode}")
    elif is_second_pass:
        session['second_calculation_result'] = text
        session['second_calculation_data'] = {
            'materials_cost': materials_cost,
            'production_cost': production_cost,
            'drawings_cost': drawings_cost,
            'nodes_cost': nodes_cost,
            'node_production_cost': node_production_cost,
            'total_cost': total_cost,
            'revenue': revenue,
            'profit_before_tax': profit_before_tax,
            'tax': tax,
            'profit_after_tax': profit_after_tax
        }
        session['second_calculation_mode_name'] = mode_name
        session['second_calculation_mode_raw'] = calculation_mode
        logger.info(f"🔧 ВТОРОЙ расчёт: mode_name={mode_name}, mode_raw={calculation_mode}")
    
    # Сохраняем последний результат
    session['last_result_text'] = text
    session['last_result_keyboard'] = result_keyboard(user_id, is_multi=False, show_comparison=show_comparison)
    session['last_calculation_data'] = {
        'materials_cost': materials_cost,
        'production_cost': production_cost,
        'drawings_cost': drawings_cost,
        'nodes_cost': nodes_cost,
        'node_production_cost': node_production_cost,
        'total_cost': total_cost,
        'revenue': revenue,
        'profit_before_tax': profit_before_tax,
        'tax': tax,
        'profit_after_tax': profit_after_tax
    }
    session['calculation_mode_name'] = mode_name
    session['calculation_mode_raw'] = calculation_mode
    
    await _send_result_message(
        update_obj,
        text,
        result_keyboard(user_id, is_multi=False, show_comparison=show_comparison),
        parse_mode='Markdown'
    )


def _format_total_result_list(
    materials_cost: float,
    production_cost: float,
    drawings_cost: float,
    total_cost: float,
    revenue: float,
    profit_before_tax: float,
    tax: float,
    profit_after_tax: float,
    per_unit_cost: float = None,
    per_unit_profit: float = None
) -> str:
    """Форматирует итоги в виде списка (без таблицы)"""
    lines = [
        "💰 ИТОГИ",
        f"• Материалы: {format_price(materials_cost)}",
        f"• Производство: {format_price(production_cost)}",
        f"• Чертежи: {format_price(drawings_cost)}",
        f"• Себестоимость: {format_price(total_cost)}",
        f"• Выручка: {format_price(revenue)}",
        f"• Прибыль до налога: {format_price(profit_before_tax)}",
        f"• Налог: {format_price(tax)}",
        f"• Прибыль после налога: {format_price(profit_after_tax)}"
    ]
    
    if per_unit_cost is not None:
        lines.append("")
        lines.append("📏 НА 1 ШТУКУ:")
        lines.append(f"• Себестоимость: {format_price(per_unit_cost)}")
        if per_unit_profit is not None:
            lines.append(f"• Прибыль: {format_price(per_unit_profit)}")
    
    return "\n".join(lines)


async def _calculate_multi_result(update_obj, user_id: int, tax_rate: float, calculation_mode: str, is_comparison: bool):
    """Расчёт и вывод результата для множественного режима"""
    session = get_session(user_id)
    products_with_details = session.get('products_with_details', [])
    
    if not products_with_details:
        logger.error(f"Нет данных для множественного результата у пользователя {user_id}")
        await _send_result_message(update_obj, "❌ Нет данных для расчёта", cancel_button(user_id))
        return
    
    total_materials_cost = 0
    total_production_cost = 0
    total_drawings_cost = 0
    total_nodes_cost = 0
    total_node_production_cost = 0
    total_revenue = 0
    
    multi_result = []
    
    for item in products_with_details:
        product = item['product']
        quantity = item['quantity']
        market_price = item['market_price']
        drawing_price = item['drawing_price']
        materials_list = item['materials']
        nodes_list = item['nodes']
        drawings_list = item['drawings']
        drawings_needed = item['drawings_needed']
        
        materials_cost = sum(m['qty'] * m.get('price', 0) for m in materials_list)
        
        prod_price_str = product.get('Цена производства', '0 ISK')
        try:
            prod_price = float(str(prod_price_str).replace(' ISK', '').replace(' ', ''))
        except:
            prod_price = 0
        production_cost = prod_price * drawings_needed
        
        item_drawings_cost = drawing_price * drawings_needed
        
        nodes_cost = 0
        node_production_cost = 0
        
        if calculation_mode == 'buy_nodes':
            nodes_cost = sum(n['needed_qty'] * n.get('price', 0) for n in nodes_list)
        else:
            node_production_cost = sum(n.get('total_cost', 0) for n in nodes_list)
            for d in drawings_list:
                item_drawings_cost += d['drawings'] * d.get('price', 0)
        
        total_cost = materials_cost + production_cost + item_drawings_cost + nodes_cost + node_production_cost
        revenue = market_price * quantity
        profit_before_tax = revenue - total_cost
        tax = calculate_tax(profit_before_tax, tax_rate)
        profit_after_tax = profit_before_tax - tax
        
        multi_result.append({
            'product': product,
            'quantity': quantity,
            'materials_cost': materials_cost,
            'production_cost': production_cost,
            'drawings_cost': item_drawings_cost,
            'nodes_cost': nodes_cost,
            'node_production_cost': node_production_cost,
            'total_cost': total_cost,
            'revenue': revenue,
            'profit_before_tax': profit_before_tax,
            'tax': tax,
            'profit_after_tax': profit_after_tax
        })
        
        total_materials_cost += materials_cost
        total_production_cost += production_cost
        total_drawings_cost += item_drawings_cost
        total_nodes_cost += nodes_cost
        total_node_production_cost += node_production_cost
        total_revenue += revenue
    
    total_cost_all = total_materials_cost + total_production_cost + total_drawings_cost + total_nodes_cost + total_node_production_cost
    total_profit_before_tax = total_revenue - total_cost_all
    total_tax = calculate_tax(total_profit_before_tax, tax_rate)
    total_profit_after_tax = total_profit_before_tax - total_tax
    
    session['multi_result'] = multi_result
    session['result_page'] = 0
    
    mode_name = "покупка узлов" if calculation_mode == 'buy_nodes' else "производство узлов"
    
    text = f"📊 ОБЩАЯ СВОДКА (МНОЖЕСТВЕННЫЙ РЕЖИМ)\n\n"
    text += f"📦 ВСЕГО ИЗДЕЛИЙ: {len(products_with_details)}\n"
    text += f"⚙️ ЭФФЕКТИВНОСТЬ: {session.get('efficiency', 150)}%\n"
    text += f"🏛️ НАЛОГ: {tax_rate}%\n"
    text += f"🎯 РЕЖИМ: {mode_name}\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += _format_total_result_list(
        total_materials_cost, total_production_cost, total_drawings_cost + total_nodes_cost + total_node_production_cost,
        total_cost_all, total_revenue, total_profit_before_tax, total_tax, total_profit_after_tax
    )
    
    session['last_result_text'] = text
    session['last_result_keyboard'] = result_keyboard(user_id, is_multi=True, current_index=-1, total_count=len(multi_result))
    
    await _send_result_message(
        update_obj,
        text,
        result_keyboard(user_id, is_multi=True, current_index=-1, total_count=len(multi_result)),
        parse_mode='Markdown'
    )


async def show_product_detail(update_obj, user_id: int, index: int):
    """Показать детализацию по одному изделию в множественном режиме"""
    session = get_session(user_id)
    multi_result = session.get('multi_result', [])
    
    if index < 0 or index >= len(multi_result):
        await _send_result_message(update_obj, "❌ Изделие не найдено", cancel_button(user_id))
        return
    
    item = multi_result[index]
    product = item['product']
    quantity = item['quantity']
    
    text = f"📊 ДЕТАЛИЗАЦИЯ ({index + 1}/{len(multi_result)})\n\n"
    text += f"🏷️ ИЗДЕЛИЕ: {product.get('Наименование', '')}\n"
    text += f"📦 КОЛИЧЕСТВО: {format_number(quantity)} шт\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += _format_total_result_list(
        item['materials_cost'], item['production_cost'], item['drawings_cost'] + item['nodes_cost'] + item['node_production_cost'],
        item['total_cost'], item['revenue'], item['profit_before_tax'], item['tax'], item['profit_after_tax']
    )
    
    session['last_result_text'] = text
    session['last_result_keyboard'] = result_keyboard(user_id, is_multi=True, current_index=index, total_count=len(multi_result))
    session['result_page'] = index
    
    await _send_result_message(
        update_obj,
        text,
        result_keyboard(user_id, is_multi=True, current_index=index, total_count=len(multi_result)),
        parse_mode='Markdown'
    )


async def next_detail(query: CallbackQuery, user_id: int):
    """Следующее изделие в множественном режиме"""
    session = get_session(user_id)
    current = session.get('result_page', -1)
    multi_result = session.get('multi_result', [])
    
    if current == -1:
        current = 0
    elif current < len(multi_result) - 1:
        current += 1
    
    await show_product_detail(query, user_id, current)


async def prev_detail(query: CallbackQuery, user_id: int):
    """Предыдущее изделие в множественном режиме"""
    session = get_session(user_id)
    current = session.get('result_page', -1)
    multi_result = session.get('multi_result', [])
    
    if current == -1:
        current = len(multi_result) - 1
    elif current > 0:
        current -= 1
    
    await show_product_detail(query, user_id, current)


async def back_to_total_summary(query: CallbackQuery, user_id: int):
    """Возврат к общей сводке в множественном режиме"""
    session = get_session(user_id)
    text = session.get('last_result_text')
    
    if text:
        await _send_result_message(
            query,
            text,
            result_keyboard(user_id, is_multi=True, current_index=-1, total_count=len(session.get('multi_result', []))),
            parse_mode='Markdown'
        )


async def start_comparison(query, user_id: int):
    """Начать сравнительный расчёт"""
    session = get_session(user_id)
    
    current_mode_raw = session.get('first_calculation_mode_raw', 'buy_nodes')
    opposite_mode = 'produce_nodes' if current_mode_raw == 'buy_nodes' else 'buy_nodes'
    
    session['comparison_mode'] = True
    session['comparison_target_mode'] = opposite_mode
    session['is_comparison_second_pass'] = True
    
    session['materials_list'] = []
    session['nodes_list'] = []
    session['drawings_list'] = []
    session['unified_price_items'] = []
    
    session['calculation_mode'] = opposite_mode
    session['step'] = 'materials'
    
    mode_name = "производство узлов" if opposite_mode == 'produce_nodes' else "покупка узлов"
    current_mode_name = "покупка узлов" if current_mode_raw == 'buy_nodes' else "производство узлов"
    
    await query.edit_message_text(
        f"🔄 ЗАПУСК СРАВНИТЕЛЬНОГО РАСЧЁТА\n\n"
        f"Исходный режим: {current_mode_name}\n"
        f"Новый режим: {mode_name}\n\n"
        f"Выполняется расчёт в новом режиме...",
        reply_markup=cancel_button(user_id)
    )
    
    from .materials import calculate_single_materials
    await calculate_single_materials(query, user_id)


async def show_comparison_results(update_obj, user_id: int):
    """Показать результаты сравнительного расчёта (3 страницы)"""
    session = get_session(user_id)
    
    session['comparison_page'] = 0
    await _show_comparison_page(update_obj, user_id, 0)


async def _show_comparison_page(update_obj, user_id: int, page: int):
    """Показать страницу сравнения"""
    session = get_session(user_id)
    
    if page == 0:
        text = session.get('first_calculation_result', '')
        has_prev = False
        has_next = True
        title = "1/3"
    elif page == 1:
        text = session.get('second_calculation_result', '')
        has_prev = True
        has_next = True
        title = "2/3"
    else:
        text = await _format_comparison_analysis(user_id)
        has_prev = True
        has_next = False
        title = "3/3"
    
    await _send_result_message(
        update_obj,
        f"{text}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📄 Страница {title}",
        comparison_keyboard(user_id, has_prev, has_next),
        parse_mode='Markdown'
    )


async def _format_comparison_analysis(user_id: int) -> str:
    """Форматирует страницу сравнительного анализа"""
    session = get_session(user_id)
    
    data1 = session.get('first_calculation_data', {})
    data2 = session.get('second_calculation_data', {})
    mode1 = session.get('first_calculation_mode_name', 'Режим 1')
    mode2 = session.get('second_calculation_mode_name', 'Режим 2')
    product_name = session.get('product_name', '')
    quantity = session.get('quantity', 0)
    
    diff_materials = data1.get('materials_cost', 0) - data2.get('materials_cost', 0)
    diff_other = (data1.get('drawings_cost', 0) + data1.get('nodes_cost', 0) + data1.get('node_production_cost', 0)) - \
                 (data2.get('drawings_cost', 0) + data2.get('nodes_cost', 0) + data2.get('node_production_cost', 0))
    diff_total = data1.get('total_cost', 0) - data2.get('total_cost', 0)
    
    if diff_total < 0:
        cheaper = mode1
        saving = abs(diff_total)
    elif diff_total > 0:
        cheaper = mode2
        saving = diff_total
    else:
        cheaper = None
        saving = 0
    
    text = f"📊 СРАВНИТЕЛЬНЫЙ АНАЛИЗ\n\n"
    text += f"🏷️ ИЗДЕЛИЕ: {product_name}\n"
    text += f"📦 КОЛИЧЕСТВО: {format_number(quantity)} шт\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += "СРАВНЕНИЕ РЕЖИМОВ\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    text += f"• Режим 1 ({mode1}):\n"
    text += f"  - Материалы: {format_price(data1.get('materials_cost', 0))}\n"
    text += f"  - Узлы/Чертежи/Производство: {format_price(data1.get('drawings_cost', 0) + data1.get('nodes_cost', 0) + data1.get('node_production_cost', 0))}\n"
    text += f"  - Себестоимость: {format_price(data1.get('total_cost', 0))}\n\n"
    
    text += f"• Режим 2 ({mode2}):\n"
    text += f"  - Материалы: {format_price(data2.get('materials_cost', 0))}\n"
    text += f"  - Узлы/Чертежи/Производство: {format_price(data2.get('drawings_cost', 0) + data2.get('nodes_cost', 0) + data2.get('node_production_cost', 0))}\n"
    text += f"  - Себестоимость: {format_price(data2.get('total_cost', 0))}\n\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if cheaper:
        text += f"📖 ИТОГ:\n"
        text += f"Режим «{cheaper}» дешевле на {format_price(saving)}\n"
    else:
        text += f"📖 ИТОГ:\n"
        text += f"При введённых ценах оба режима дают одинаковую себестоимость\n"
    
    return text


async def back_to_result(query: CallbackQuery, user_id: int):
    """Возврат к последнему результату"""
    session = get_session(user_id)
    text = session.get('last_result_text')
    keyboard = session.get('last_result_keyboard')
    
    if not text or not keyboard:
        await query.answer("❌ Нет сохранённого результата", show_alert=True)
        return
    
    # Проверяем, совпадает ли текущий текст с сохраняемым
    current_text = query.message.text if query.message else ""
    
    if current_text == text:
        # Текст уже совпадает, просто отвечаем на callback
        await query.answer("Вы уже на странице результатов")
        return
    
    try:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка при возврате к результату: {e}")
        # Если не удалось отредактировать, отправляем новое сообщение
        await query.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        await query.answer()


async def same_category(update_obj, user_id: int):
    """Новый расчёт в той же категории"""
    session = get_session(user_id)
    category_path = session.get('category_path', [])
    category_tree = session.get('category_tree')
    mode = session.get('mode')
    
    from .session import reset_session_for_new_calculation
    from keyboards.calculator import back_with_skip_button
    
    reset_session_for_new_calculation(user_id, mode, category_path, category_tree)
    
    path_str = " > ".join(category_path) if category_path else ""
    
    # Используем правильную клавиатуру в зависимости от режима
    if mode == 'single':
        reply_markup = back_with_skip_button(user_id, "products", "skip_efficiency")
    else:
        reply_markup = back_with_skip_button(user_id, "multi_select", "skip_multi_efficiency")
    
    await _send_result_message(
        update_obj,
        f"📊 ПАРАМЕТРЫ РАСЧЁТА\n\n"
        f"Категория: {path_str}\n\n"
        f"Введите эффективность производства (%):\n"
        f"Пример: 110\n\n"
        f"По умолчанию: 150%",
        reply_markup
    )


async def show_explanation(update_obj, user_id: int):
    """Показать пояснение"""
    session = get_session(user_id)
    
    # Сохраняем текущий результат как last_result, если он ещё не сохранён
    if not session.get('last_result_text'):
        # Если пояснение вызвано до показа результатов, сохраняем заглушку
        session['last_result_text'] = "📊 РЕЗУЛЬТАТЫ РАСЧЕТА\n\nРасчёт ещё не выполнен."
        session['last_result_keyboard'] = cancel_button(user_id)
    
    await _send_result_message(
        update_obj,
        format_explanation(),
        explanation_keyboard(user_id),
        parse_mode=None  # Без Markdown-разметки, чтобы избежать ошибок парсинга
    )
