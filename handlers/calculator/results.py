import logging
import math
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from keyboards.calculator import result_keyboard, explanation_keyboard, cancel_button, comparison_keyboard
from utils.formatters import (
    format_number, format_price, format_material_result_line,
    format_node_result_line, format_leftover_line, format_total_result, format_explanation
)
from utils.calculations import calculate_tax
from .session import get_session, clear_session
from .parameters import check_product_has_nodes

logger = logging.getLogger(__name__)


async def _send_result_message(update_obj, text: str, reply_markup, parse_mode: str = 'Markdown'):
    """Универсальная функция отправки результата"""
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
    
    # Сохраняем результаты первого расчёта для сравнения
    if not is_comparison and session.get('first_calculation_completed') is None:
        session['first_calculation_mode'] = calculation_mode
        session['first_calculation_tax'] = tax_rate
        session['first_calculation_completed'] = True
    
    if mode == 'single':
        await _calculate_single_result(update_obj, user_id, tax_rate, calculation_mode, is_comparison)
    else:
        await _calculate_multi_result(update_obj, user_id, tax_rate, calculation_mode, is_comparison)


async def _calculate_single_result(update_obj, user_id: int, tax_rate: float, calculation_mode: str, is_comparison: bool):
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
    
    # Расчёт стоимости чертежа изделия
    drawings_cost = drawing_price * drawings_needed
    
    # Расчёт в зависимости от режима
    nodes_cost = 0
    node_production_cost = 0
    
    if calculation_mode == 'buy_nodes':
        # Покупка узлов
        for node in nodes_list:
            node_cost = node['needed_qty'] * node.get('price', 0)
            nodes_cost += node_cost
    else:
        # Производство узлов
        for node in nodes_list:
            node_production_cost += node.get('total_cost', 0)
        # ИСПРАВЛЕНО: используем ключ 'drawings' вместо 'qty'
        for drawing in drawings_list:
            drawings_cost += drawing['drawings'] * drawing.get('price', 0)
    
    total_cost = materials_cost + production_cost + drawings_cost + nodes_cost + node_production_cost
    revenue = market_price * quantity
    profit_before_tax = revenue - total_cost
    tax = calculate_tax(profit_before_tax, tax_rate)
    profit_after_tax = profit_before_tax - tax
    per_unit_cost = total_cost / quantity if quantity > 0 else 0
    per_unit_profit = profit_after_tax / quantity if quantity > 0 else 0
    
    # Формируем текст
    mode_name = "покупка узлов" if calculation_mode == 'buy_nodes' else "производство узлов"
    text = f"📊 РЕЗУЛЬТАТЫ РАСЧЕТА\n\n"
    text += f"🏷️ ИЗДЕЛИЕ: {product.get('Наименование', '')}\n"
    text += f"📂 КАТЕГОРИЯ: {product.get('Категории', '')}\n"
    text += f"📦 КОЛИЧЕСТВО: {format_number(quantity)} шт\n"
    text += f"⚙️ ЭФФЕКТИВНОСТЬ: {session.get('efficiency', 150)}%\n"
    text += f"🏛️ НАЛОГ: {tax_rate}%\n"
    text += f"🎯 РЕЖИМ: {mode_name}\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Материалы
    if materials_list:
        text += "📦 МАТЕРИАЛЫ:\n"
        for i, m in enumerate(materials_list, 1):
            text += format_material_result_line(i, m['name'], m['qty'], m.get('price', 0), m.get('cost', 0)) + "\n"
        text += "\n"
    
    # Узлы или чертежи
    if calculation_mode == 'buy_nodes' and nodes_list:
        text += "🔩 УЗЛЫ (покупка):\n"
        for i, node in enumerate(nodes_list, 1):
            text += f"{i}. {node['name']}: нужно {format_number(node['needed_qty'])} шт | цена: {format_price(node.get('price', 0))}\n"
        text += "\n"
    elif not calculation_mode == 'buy_nodes' and drawings_list:
        text += "📄 ЧЕРТЕЖИ УЗЛОВ:\n"
        for i, drawing in enumerate(drawings_list, 1):
            text += f"{i}. {drawing['name']}: нужно {format_number(drawing['drawings'])} чертежей | цена: {format_price(drawing.get('price', 0))}\n"
        text += "\n"
        
        if node_production_cost > 0:
            text += "🏭 ПРОИЗВОДСТВО УЗЛОВ (фиксированная стоимость):\n"
            for node in nodes_list:
                text += f"• {node['name']}: {format_number(node['drawings'])} чертежей × {format_price(node['price_per_drawing'])} = {format_price(node['total_cost'])}\n"
            text += "\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    text += format_total_result(
        materials_cost, production_cost, drawings_cost + nodes_cost + node_production_cost,
        total_cost, revenue, profit_before_tax, tax, profit_after_tax,
        per_unit_cost, per_unit_profit
    )
    
    # Сохраняем результат
    if not is_comparison:
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
        session['product_name'] = product.get('Наименование', '')
        session['quantity'] = quantity
        session['has_nodes'] = await check_product_has_nodes(product.get('Код', ''))
    
    # Сохраняем для последующего использования (например, в сравнении)
    session['last_result_text'] = text
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
    
    # Определяем, показывать ли кнопку сравнения
    show_comparison = not is_comparison and session.get('has_nodes', False)
    
    await _send_result_message(
        update_obj,
        text,
        result_keyboard(user_id, is_multi=False, show_comparison=show_comparison),
        parse_mode='Markdown'
    )


async def start_comparison(query, user_id: int):
    """Начать сравнительный расчёт"""
    session = get_session(user_id)
    
    # Определяем противоположный режим
    current_mode = session.get('calculation_mode', 'buy_nodes')
    opposite_mode = 'produce_nodes' if current_mode == 'buy_nodes' else 'buy_nodes'
    
    # Сохраняем, что мы в режиме сравнения
    session['comparison_mode'] = True
    session['comparison_target_mode'] = opposite_mode
    
    # Очищаем старые данные материалов, чтобы пересчитать в новом режиме
    session['materials_list'] = []
    session['nodes_list'] = []
    session['drawings_list'] = []
    session['unified_price_items'] = []
    
    # Устанавливаем новый режим расчёта
    session['calculation_mode'] = opposite_mode
    session['step'] = 'materials'  # Переходим сразу к списку материалов
    
    # Показываем сообщение о начале сравнения
    mode_name = "производство узлов" if opposite_mode == 'produce_nodes' else "покупка узлов"
    
    await query.edit_message_text(
        f"🔄 ЗАПУСК СРАВНИТЕЛЬНОГО РАСЧЁТА\n\n"
        f"Исходный режим: {'покупка узлов' if current_mode == 'buy_nodes' else 'производство узлов'}\n"
        f"Новый режим: {mode_name}\n\n"
        f"Выполняется расчёт в новом режиме...",
        reply_markup=cancel_button(user_id)
    )
    
    # Пересчитываем материалы в новом режиме
    from .materials import calculate_single_materials
    await calculate_single_materials(query, user_id)


async def show_comparison_results(query, user_id: int):
    """Показать результаты сравнительного расчёта (3 страницы)"""
    session = get_session(user_id)
    
    # Сохраняем второй расчёт
    session['second_calculation_result'] = session.get('last_result_text', '')
    session['second_calculation_mode_name'] = session.get('calculation_mode_name', '')
    session['second_calculation_data'] = session.get('last_calculation_data', {})
    
    # Показываем первую страницу (результаты первого расчёта)
    session['comparison_page'] = 0
    await _show_comparison_page(query, user_id, 0)


async def _show_comparison_page(query, user_id: int, page: int):
    """Показать страницу сравнения"""
    session = get_session(user_id)
    
    if page == 0:
        # Страница 1: результаты первого расчёта
        text = session.get('first_calculation_result', '')
        has_prev = False
        has_next = True
        title = "1/3"
    elif page == 1:
        # Страница 2: результаты второго расчёта
        text = session.get('second_calculation_result', '')
        has_prev = True
        has_next = True
        title = "2/3"
    else:
        # Страница 3: сравнительный анализ
        text = await _format_comparison_analysis(user_id)
        has_prev = True
        has_next = False
        title = "3/3"
    
    await query.edit_message_text(
        f"{text}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📄 Страница {title}",
        reply_markup=comparison_keyboard(user_id, has_prev, has_next),
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
    
    # Расчёт разницы
    diff_materials = data1.get('materials_cost', 0) - data2.get('materials_cost', 0)
    diff_other = (data1.get('drawings_cost', 0) + data1.get('nodes_cost', 0) + data1.get('node_production_cost', 0)) - \
                 (data2.get('drawings_cost', 0) + data2.get('nodes_cost', 0) + data2.get('node_production_cost', 0))
    diff_total = data1.get('total_cost', 0) - data2.get('total_cost', 0)
    
    # Определяем, какой режим дешевле
    if diff_total < 0:
        cheaper = mode1
        saving = abs(diff_total)
    elif diff_total > 0:
        cheaper = mode2
        saving = diff_total
    else:
        cheaper = None
        saving = 0
    
    # Формируем текст
    text = f"📊 СРАВНИТЕЛЬНЫЙ АНАЛИЗ\n\n"
    text += f"🏷️ ИЗДЕЛИЕ: {product_name}\n"
    text += f"📦 КОЛИЧЕСТВО: {format_number(quantity)} шт\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += "СРАВНЕНИЕ РЕЖИМОВ\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    text += "┌─────────────────────┬──────────────────┬──────────────────┬──────────────────┐\n"
    text += "│ Показатель          │ Режим 1          │ Режим 2          │ Разница (1 − 2) │\n"
    text += f"│                     │ ({mode1[:15]}) │ ({mode2[:15]}) │                  │\n"
    text += "├─────────────────────┼──────────────────┼──────────────────┼──────────────────┤\n"
    text += f"│ Материалы           │ {format_price(data1.get('materials_cost', 0)):>16} │ {format_price(data2.get('materials_cost', 0)):>16} │ {format_price(diff_materials):>16} │\n"
    text += f"│ Узлы/Чертежи/Произ-во│ {format_price(data1.get('drawings_cost', 0) + data1.get('nodes_cost', 0) + data1.get('node_production_cost', 0)):>16} │ {format_price(data2.get('drawings_cost', 0) + data2.get('nodes_cost', 0) + data2.get('node_production_cost', 0)):>16} │ {format_price(diff_other):>16} │\n"
    text += "├─────────────────────┼──────────────────┼──────────────────┼──────────────────┤\n"
    text += f"│ СЕБЕСТОИМОСТЬ       │ {format_price(data1.get('total_cost', 0)):>16} │ {format_price(data2.get('total_cost', 0)):>16} │ {format_price(diff_total):>16} │\n"
    text += "└─────────────────────┴──────────────────┴──────────────────┴──────────────────┘\n\n"
    
    if cheaper:
        text += f"📖 ИТОГ:\n"
        text += f"Режим {cheaper} дешевле режима {mode2 if cheaper == mode1 else mode1} на {format_price(saving)}\n"
    else:
        text += f"📖 ИТОГ:\n"
        text += f"При введённых ценах оба режима дают одинаковую себестоимость\n"
    
    return text


async def _calculate_multi_result(update_obj, user_id: int, tax_rate: float, calculation_mode: str, is_comparison: bool):
    """Расчёт для множественного режима (заглушка)"""
    # TODO: реализовать для множественного режима
    pass


async def show_product_detail(update_obj, user_id: int, index: int):
    """Показывает детали по конкретному изделию (множественный режим)"""
    pass


async def next_detail(update_obj, user_id: int):
    """Переход к следующему изделию"""
    pass


async def prev_detail(update_obj, user_id: int):
    """Переход к предыдущему изделию"""
    pass


async def back_to_total_summary(update_obj, user_id: int):
    """Возврат к общей сводке"""
    pass


async def back_to_result(query, user_id: int):
    """Возврат к результатам из пояснения"""
    session = get_session(user_id)
    text = session.get('last_result_text')
    keyboard = session.get('last_result_keyboard')
    
    if text and keyboard:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')


async def same_category(update_obj, user_id: int):
    """Новый расчёт в той же категории"""
    session = get_session(user_id)
    category_path = session.get('category_path', [])
    category_tree = session.get('category_tree')
    mode = session.get('mode')
    
    from .session import reset_session_for_new_calculation
    reset_session_for_new_calculation(user_id, mode, category_path, category_tree)
    
    path_str = " > ".join(category_path) if category_path else ""
    
    await _send_result_message(
        update_obj,
        f"📊 ПАРАМЕТРЫ РАСЧЁТА\n\n"
        f"Категория: {path_str}\n\n"
        f"Введите эффективность производства (%):\n"
        f"Пример: 110",
        cancel_button(user_id)
    )


async def show_explanation(update_obj, user_id: int):
    """Показывает пояснение"""
    await _send_result_message(
        update_obj,
        format_explanation(),
        explanation_keyboard(user_id),
        parse_mode='Markdown'
    )
