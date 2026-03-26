import logging
import math
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from keyboards.calculator import result_keyboard, explanation_keyboard, cancel_button
from utils.formatters import (
    format_number, format_price, format_material_result_line,
    format_node_result_line, format_leftover_line, format_total_result, format_explanation
)
from utils.calculations import calculate_tax
from .session import get_session, reset_session_for_new_calculation

logger = logging.getLogger(__name__)


async def calculate_final_result(update_obj, user_id: int):
    """Финальный расчёт и вывод результатов"""
    session = get_session(user_id)
    mode = session.get('mode')
    tax_rate = session.get('tax', 0)
    
    if mode == 'single':
        await _calculate_single_result(update_obj, user_id, tax_rate)
    else:
        await _calculate_multi_result(update_obj, user_id, tax_rate)


async def _send_result_message(update_obj, text: str, reply_markup):
    """Универсальная функция отправки результата"""
    if isinstance(update_obj, CallbackQuery):
        await update_obj.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    elif hasattr(update_obj, 'message') and hasattr(update_obj.message, 'reply_text'):
        await update_obj.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    elif hasattr(update_obj, 'reply_text'):
        await update_obj.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        logger.error(f"Не удалось отправить результат: неизвестный тип {type(update_obj)}")


async def _calculate_single_result(update_obj, user_id: int, tax_rate: float):
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
    node_drawings_cost = sum(node.get('total_cost', 0) for node in nodes_list)
    drawings_cost += node_drawings_cost
    
    # Итоговые расчёты
    total_cost = materials_cost + production_cost + drawings_cost
    revenue = market_price * quantity
    profit_before_tax = revenue - total_cost
    tax = calculate_tax(profit_before_tax, tax_rate)
    profit_after_tax = profit_before_tax - tax
    per_unit_cost = total_cost / quantity if quantity > 0 else 0
    per_unit_profit = profit_after_tax / quantity if quantity > 0 else 0
    
    # Формируем текст
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
        
        leftovers = [n for n in nodes_list if n.get('leftover', 0) > 0]
        if leftovers:
            text += "📦 ОСТАТКИ УЗЛОВ (неиспользованные):\n"
            for node in leftovers:
                text += format_leftover_line(node['name'], node['leftover']) + "\n"
            text += "\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    text += format_total_result(
        materials_cost, production_cost, drawings_cost,
        total_cost, revenue, profit_before_tax, tax, profit_after_tax,
        per_unit_cost, per_unit_profit
    )
    
    session['last_result_text'] = text
    session['last_result_keyboard'] = result_keyboard(user_id, is_multi=False)
    
    await _send_result_message(update_obj, text, result_keyboard(user_id, is_multi=False))


async def _calculate_multi_result(update_obj, user_id: int, tax_rate: float):
    """Расчёт и вывод результата для множественного режима"""
    session = get_session(user_id)
    products_data = session.get('products_with_details', [])
    materials_list = session.get('materials_list', [])
    nodes_list = session.get('nodes_list', [])
    
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
    node_drawings_cost = sum(node.get('total_cost', 0) for node in nodes_list)
    total_drawings_cost += node_drawings_cost
    
    # Итоговые расчёты
    total_cost = total_materials_cost + total_production_cost + total_drawings_cost
    profit_before_tax = total_revenue - total_cost
    tax = calculate_tax(profit_before_tax, tax_rate)
    profit_after_tax = profit_before_tax - tax
    
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
    session['result_page'] = 0
    
    await _show_total_summary(update_obj, user_id, tax_rate)


async def _show_total_summary(update_obj, user_id: int, tax_rate: float = None):
    """Показывает общую сводку для множественного режима"""
    session = get_session(user_id)
    result = session.get('multi_result', {})
    products_data = session.get('products_with_details', [])
    
    if tax_rate is None:
        tax_rate = session.get('tax', 0)
    
    materials_list = result.get('materials_list', [])
    nodes_list = result.get('nodes_list', [])
    
    product_names = [p['product']['Наименование'] for p in products_data]
    text = f"📊 РЕЗУЛЬТАТЫ РАСЧЁТА (ОБЩАЯ СВОДКА)\n\n"
    text += f"Режим: множественный расчёт\n"
    text += f"Изделия: {', '.join(product_names)} ({len(products_data)} шт)\n"
    text += f"Эффективность: {session.get('efficiency', 150)}%\n"
    text += f"Налог: {tax_rate}%\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if materials_list:
        text += "📦 МАТЕРИАЛЫ (ОБЩИЕ):\n"
        for i, m in enumerate(materials_list, 1):
            text += format_material_result_line(i, m['name'], m['qty'], m.get('price', 0), m.get('cost', 0)) + "\n"
        text += "\n"
    
    if nodes_list:
        text += "🔩 УЗЛЫ И ЧЕРТЕЖИ (ОБЩИЕ):\n"
        for i, node in enumerate(nodes_list, 1):
            text += format_node_result_line(
                i, node['name'], node['needed_qty'], 
                node['drawings'], node.get('multiplicity', 1)
            ) + "\n"
        text += "\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
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
    
    await _send_result_message(update_obj, text, result_keyboard(user_id, is_multi=True, current_index=-1, total_count=len(products_data)))


async def show_product_detail(update_obj, user_id: int, index: int):
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
            leftover = node.get('leftover', 0)
            text += format_node_result_line(
                i, node['name'], node['needed_qty'], 
                node['drawings'], node.get('multiplicity', 1),
                leftover if leftover > 0 else None
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
    
    await _send_result_message(update_obj, text, result_keyboard(user_id, is_multi=True, current_index=index, total_count=len(products_data)))


async def next_detail(update_obj, user_id: int):
    """Переход к следующему изделию"""
    session = get_session(user_id)
    products_data = session.get('products_with_details', [])
    current = session.get('result_page', 0)
    
    next_index = current + 1
    if next_index < len(products_data):
        session['result_page'] = next_index
        await show_product_detail(update_obj, user_id, next_index)


async def prev_detail(update_obj, user_id: int):
    """Переход к предыдущему изделию"""
    session = get_session(user_id)
    current = session.get('result_page', 0)
    
    prev_index = current - 1
    if prev_index >= 0:
        session['result_page'] = prev_index
        await show_product_detail(update_obj, user_id, prev_index)


async def back_to_total_summary(update_obj, user_id: int):
    """Возврат к общей сводке"""
    session = get_session(user_id)
    session['result_page'] = -1
    await _show_total_summary(update_obj, user_id)


async def back_to_result(update_obj, user_id: int):
    """Возврат к результатам из пояснения"""
    session = get_session(user_id)
    text = session.get('last_result_text')
    keyboard = session.get('last_result_keyboard')
    
    if text and keyboard:
        await _send_result_message(update_obj, text, keyboard)


async def same_category(update_obj, user_id: int):
    """Новый расчёт в той же категории"""
    session = get_session(user_id)
    category_path = session.get('category_path', [])
    category_tree = session.get('category_tree')
    mode = session.get('mode')
    
    reset_session_for_new_calculation(user_id, mode, category_path, category_tree)
    
    path_str = " > ".join(category_path) if category_path else ""
    
    if mode == 'single':
        await _send_result_message(
            update_obj,
            f"📊 ПАРАМЕТРЫ РАСЧЁТА\n\n"
            f"Категория: {path_str}\n\n"
            f"Введите эффективность производства (%):\n"
            f"Пример: 110",
            cancel_button(user_id)
        )
    else:
        await _send_result_message(
            update_obj,
            f"📊 ПАРАМЕТРЫ РАСЧЁТА\n\n"
            f"Категория: {path_str}\n\n"
            f"Введите эффективность производства (%):\n"
            f"(общая для всех изделий)\n\n"
            f"Пример: 110",
            cancel_button(user_id)
        )


async def show_explanation(update_obj, user_id: int):
    """Показывает пояснение"""
    await _send_result_message(
        update_obj,
        format_explanation(),
        explanation_keyboard(user_id)
    )
