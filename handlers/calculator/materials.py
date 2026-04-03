import logging
import math
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from keyboards.calculator import materials_keyboard, missing_prices_keyboard, cancel_button, back_button
from utils.formatters import format_number, format_price, format_material_line
from utils.calculations import calculate_with_efficiency, round_quantity, calculate_node_drawings, merge_materials
from excel_handler import get_excel_handler
from price_db import get_all_material_prices, save_material_price
from .session import get_session

logger = logging.getLogger(__name__)


async def calculate_single_materials(update, user_id: int):
    """Расчёт материалов для одиночного режима"""
    session = get_session(user_id)
    excel = get_excel_handler()
    product = session.get('selected_product', {})
    quantity = session.get('qty', 0)
    efficiency = session.get('efficiency')
    
    # ДИАГНОСТИКА: читаем calculation_mode из сессии
    calculation_mode = session.get('calculation_mode', 'buy_nodes')
    logger.info(f"🔧 [calculate_single_materials] session['calculation_mode'] = {session.get('calculation_mode')}")
    logger.info(f"🔧 [calculate_single_materials] calculation_mode = {calculation_mode}")
    logger.info(f"🔧 [calculate_single_materials] product = {product.get('Наименование', 'Unknown')}")
    logger.info(f"🔧 [calculate_single_materials] quantity = {quantity}, efficiency = {efficiency}")
    
    if efficiency is None:
        logger.error(f"efficiency is None в calculate_single_materials для пользователя {user_id}")
        await update.message.reply_text(
            "❌ Ошибка: не задана эффективность. Пожалуйста, начните расчёт заново с /start",
            reply_markup=cancel_button(user_id)
        )
        return
    
    saved_prices = get_all_material_prices()
    
    materials_list, nodes_list, drawings_list = await _calculate_materials(
        product['Код'], quantity, efficiency, excel, saved_prices, calculation_mode
    )
    
    logger.info(f"🔧 [calculate_single_materials] materials_list: {len(materials_list)} шт")
    logger.info(f"🔧 [calculate_single_materials] nodes_list: {len(nodes_list)} шт")
    logger.info(f"🔧 [calculate_single_materials] drawings_list: {len(drawings_list)} шт")
    
    # Унифицируем структуру для ввода цен
    unified_items = []
    for m in materials_list:
        unified_items.append({
            'name': m['name'],
            'qty': m['qty'],
            'price': m.get('price', 0),
            'type': 'material',
            'original': m
        })
    
    if calculation_mode == 'buy_nodes':
        logger.info("🔧 [calculate_single_materials] Режим: ПОКУПКА УЗЛОВ — добавляем узлы в список")
        for n in nodes_list:
            unified_items.append({
                'name': n['name'],
                'qty': n['needed_qty'],
                'price': n.get('price', 0),
                'type': 'node',
                'original': n
            })
    else:
        logger.info("🔧 [calculate_single_materials] Режим: ПРОИЗВОДСТВО УЗЛОВ — добавляем чертежи в список")
        for d in drawings_list:
            unified_items.append({
                'name': d['name'],
                'qty': d['drawings'],
                'price': d.get('price', 0),
                'type': 'drawing',
                'original': d
            })
    
    unified_items.sort(key=lambda x: x['name'])
    
    session['materials_list'] = materials_list
    session['nodes_list'] = nodes_list
    session['drawings_list'] = drawings_list
    session['unified_price_items'] = unified_items
    session['calculation_mode'] = calculation_mode
    session['single_product_detail'] = {
        'product': product,
        'quantity': quantity,
        'drawings_needed': math.ceil(quantity / product.get('Кратность', 1))
    }
    session['step'] = 'materials'
    session['materials_page'] = 0
    
    await _show_materials_list(update, user_id, is_multi=False, mode=calculation_mode)


async def calculate_multi_materials(update, user_id: int):
    """Расчёт материалов для множественного режима"""
    pass


async def _calculate_materials(product_code: str, quantity: int, efficiency: float, excel, saved_prices, mode: str):
    """Внутренняя функция расчёта материалов"""
    logger.info(f"🔧 [_calculate_materials] mode = {mode}")
    
    product = excel.get_product_by_code(product_code)
    if not product:
        logger.warning(f"Продукт с кодом {product_code} не найден")
        return [], [], []
    
    multiplicity = product.get('Кратность', 1)
    drawings_needed = math.ceil(quantity / multiplicity)
    
    logger.info(f"🔧 [_calculate_materials] product = {product.get('Наименование')}, multiplicity={multiplicity}, drawings_needed={drawings_needed}")
    
    materials_dict = {}
    nodes_list = []
    drawings_list = []
    
    def collect_materials(code: str, multiplier: float, is_node: bool = False):
        specs = excel.get_specifications(code)
        
        if not specs:
            return
        
        for spec in specs:
            child_code = spec['child']
            child_qty = spec['quantity']
            child = excel.get_product_by_code(child_code)
            
            if not child:
                continue
            
            child_type = child.get('Тип', '').lower()
            child_name = child.get('Наименование', '')
            child_price_str = child.get('Цена производства', '0 ISK')
            
            try:
                child_price = float(str(child_price_str).replace(' ISK', '').replace(' ', ''))
            except:
                child_price = 0
            
            per_drawing = calculate_with_efficiency(child_qty, efficiency)
            rounded = round_quantity(per_drawing)
            total_qty = rounded * multiplier
            
            if child_type == 'материал':
                if child_name not in materials_dict:
                    materials_dict[child_name] = {
                        'name': child_name,
                        'qty': 0,
                        'price': saved_prices.get(child_name, 0),
                        'type': 'material',
                        'code': child_code
                    }
                materials_dict[child_name]['qty'] += total_qty
            
            elif child_type == 'узел':
                node_multiplicity = child.get('Кратность', 1)
                node_drawings, node_leftover = calculate_node_drawings(total_qty, node_multiplicity)
                
                logger.info(f"🔧 [collect_materials] Найден узел: {child_name}, total_qty={total_qty}, mode={mode}")
                
                nodes_list.append({
                    'name': child_name,
                    'needed_qty': total_qty,
                    'drawings': node_drawings,
                    'multiplicity': node_multiplicity,
                    'leftover': node_leftover,
                    'price_per_drawing': child_price,
                    'total_cost': node_drawings * child_price,
                    'price': 0
                })
                
                if mode == 'produce_nodes':
                    logger.info(f"🔧 [collect_materials] Режим production — рекурсивно собираем материалы узла {child_name}")
                    collect_materials(child_code, total_qty, is_node=True)
                else:
                    logger.info(f"🔧 [collect_materials] Режим buy_nodes — НЕ собираем материалы узла {child_name}")
            
            elif child_type == 'изделие' and is_node:
                collect_materials(child_code, total_qty, is_node=True)
    
    collect_materials(product_code, drawings_needed, is_node=False)
    
    if mode == 'produce_nodes':
        logger.info(f"🔧 [_calculate_materials] Формируем список чертежей для {len(nodes_list)} узлов")
        for node in nodes_list:
            drawings_list.append({
                'name': node['name'],
                'drawings': node['drawings'],
                'price': 0,
                'original': node
            })
    
    materials_list = list(materials_dict.values())
    materials_list.sort(key=lambda x: x['name'])
    for i, item in enumerate(materials_list, 1):
        item['number'] = i
    
    logger.info(f"🔧 [_calculate_materials] ИТОГ: материалов={len(materials_list)}, узлов={len(nodes_list)}, чертежей={len(drawings_list)}")
    
    return materials_list, nodes_list, drawings_list


async def _show_materials_list(update_obj, user_id: int, is_multi: bool = False, mode: str = 'buy_nodes'):
    """Показывает список материалов и узлов/чертежей"""
    session = get_session(user_id)
    materials = session.get('materials_list', [])
    nodes = session.get('nodes_list', [])
    drawings = session.get('drawings_list', [])
    
    unified_items = session.get('unified_price_items', [])
    
    if unified_items:
        display_items = unified_items
        logger.info(f"🔧 [_show_materials_list] Используем unified_price_items из сессии: {len(display_items)} элементов")
    else:
        if mode == 'buy_nodes':
            display_items = []
            for m in materials:
                display_items.append({
                    'name': m['name'],
                    'qty': m['qty'],
                    'price': m.get('price', 0),
                    'type': 'material',
                    'original': m
                })
            for n in nodes:
                display_items.append({
                    'name': n['name'],
                    'qty': n['needed_qty'],
                    'price': n.get('price', 0),
                    'type': 'node',
                    'original': n
                })
        else:
            display_items = []
            for m in materials:
                display_items.append({
                    'name': m['name'],
                    'qty': m['qty'],
                    'price': m.get('price', 0),
                    'type': 'material',
                    'original': m
                })
            for d in drawings:
                display_items.append({
                    'name': d['name'],
                    'qty': d['drawings'],
                    'price': d.get('price', 0),
                    'type': 'drawing',
                    'original': d
                })
        display_items.sort(key=lambda x: x['name'])
    
    logger.info(f"🔧 [_show_materials_list] mode = {mode}")
    logger.info(f"🔧 [_show_materials_list] display_items содержит {len(display_items)} элементов")
    
    for i, item in enumerate(display_items, 1):
        item['global_number'] = i
    
    if not display_items:
        text = "❌ Для выбранного изделия не найдено материалов или узлов в базе данных."
        if isinstance(update_obj, CallbackQuery):
            await update_obj.edit_message_text(text, reply_markup=back_button(user_id, "products"))
        else:
            await update_obj.message.reply_text(text, reply_markup=back_button(user_id, "products"))
        return
    
    items_per_page = 15
    total_pages = (len(display_items) + items_per_page - 1) // items_per_page
    page = session.get('materials_page', 0)
    
    if page >= total_pages:
        page = total_pages - 1
        session['materials_page'] = page
    
    start = page * items_per_page
    end = min(start + items_per_page, len(display_items))
    page_items = display_items[start:end]
    
    text = "📦 МАТЕРИАЛЫ И "
    if mode == 'buy_nodes':
        text += "УЗЛЫ\n\n"
    else:
        text += "ЧЕРТЕЖИ\n\n"
    
    product = session.get('selected_product', {})
    text += f"Изделие: {product.get('Наименование', '')}\n"
    text += f"Эффективность: {session.get('efficiency', 150)}%\n\n"
    text += f"Страница {page + 1} из {total_pages}\n\n"
    
    for item in page_items:
        item_type = item.get('type')
        price_str = format_price(item.get('price', 0)) if item.get('price', 0) > 0 else "не установлена"
        
        if item_type == 'material':
            text += f"{item['global_number']}. {item['name']}: нужно {format_number(item['qty'])} шт | цена: {price_str}\n"
        elif item_type == 'node':
            text += f"{item['global_number']}. {item['name']}: нужно {format_number(item['qty'])} шт | цена: {price_str}\n"
        elif item_type == 'drawing':
            text += f"{item['global_number']}. {item['name']}: нужно {format_number(item['qty'])} чертежей | цена: {price_str}\n"
        else:
            text += f"{item['global_number']}. {item['name']}: нужно {format_number(item['qty'])} шт | цена: {price_str}\n"
    
    missing = [i for i in display_items if i.get('price', 0) == 0]
    session['missing_materials'] = missing
    
    try:
        if isinstance(update_obj, CallbackQuery):
            await update_obj.edit_message_text(
                text,
                reply_markup=materials_keyboard(display_items, user_id, page + 1, total_pages, "multi" if is_multi else "single")
            )
        else:
            await update_obj.message.reply_text(
                text,
                reply_markup=materials_keyboard(display_items, user_id, page + 1, total_pages, "multi" if is_multi else "single")
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке списка: {e}")


async def start_price_input(query, user_id: int):
    session = get_session(user_id)
    unified_items = session.get('unified_price_items', [])
    
    session['price_input_items'] = unified_items
    session['current_material'] = 0
    session['step'] = 'price_input_waiting'
    
    await _process_next_price(query, user_id, is_callback=True)


async def _process_next_price(update_obj, user_id: int, is_callback: bool = True):
    session = get_session(user_id)
    items = session.get('price_input_items', [])
    current = session.get('current_material', 0)
    
    if current >= len(items):
        from .results import calculate_final_result
        await calculate_final_result(update_obj, user_id)
        return
    
    item = items[current]
    current_price = item.get('price', 0)
    
    text = f"📦 ВВОД ЦЕН ({current + 1}/{len(items)})\n\n"
    text += f"Элемент: {item['name']}\n"
    text += f"Необходимое количество: {format_number(item['qty'])} шт\n"
    text += f"Текущая цена в базе: {format_price(current_price)}\n\n"
    text += "Введите цену за 1 шт (ISK):"
    
    if is_callback and hasattr(update_obj, 'edit_message_text'):
        await update_obj.edit_message_text(text, reply_markup=cancel_button(user_id))
    else:
        await update_obj.message.reply_text(text, reply_markup=cancel_button(user_id))


async def process_price_input_value(update: Update, user_id: int, text: str):
    from utils.formatters import parse_float_input
    
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
        item['original']['price'] = price
        
        save_material_price(item['name'], price)
        
        if item.get('type') == 'material':
            for m in session.get('materials_list', []):
                if m['name'] == item['name']:
                    m['price'] = price
        elif item.get('type') == 'node':
            for n in session.get('nodes_list', []):
                if n['name'] == item['name']:
                    n['price'] = price
        elif item.get('type') == 'drawing':
            for d in session.get('drawings_list', []):
                if d['name'] == item['name']:
                    d['price'] = price
        
        session['current_material'] = current + 1
        await _process_next_price(update, user_id, is_callback=False)


async def auto_prices(query, user_id: int):
    session = get_session(user_id)
    unified_items = session.get('unified_price_items', [])
    
    missing = [i for i in unified_items if i.get('price', 0) == 0]
    
    if missing:
        text = "🤖 АВТОМАТИЧЕСКАЯ ПОДСТАНОВКА ЦЕН\n\n"
        text += f"✅ Цены подставлены для: {len(unified_items) - len(missing)} элементов\n"
        text += f"⚠️ Нет цен для: {len(missing)} элементов\n\n"
        text += "Элементы без цен:\n"
        for m in missing[:10]:
            text += f"• {m['name']} (нужно {format_number(m['qty'])} шт)\n"
        if len(missing) > 10:
            text += f"• ... и ещё {len(missing) - 10}\n\n"
        text += "Что делаем?"
        
        session['missing_materials'] = missing
        session['step'] = 'missing_prices'
        
        await query.edit_message_text(text, reply_markup=missing_prices_keyboard(user_id))
    else:
        from .results import calculate_final_result
        await calculate_final_result(query, user_id)


async def input_missing_prices(query, user_id: int):
    session = get_session(user_id)
    missing = session.get('missing_materials', [])
    
    session['price_input_items'] = missing
    session['current_material'] = 0
    session['step'] = 'price_input_missing_waiting'
    
    await _process_next_missing_price(query, user_id, is_callback=True)


async def _process_next_missing_price(update_obj, user_id: int, is_callback: bool = True):
    session = get_session(user_id)
    items = session.get('price_input_items', [])
    current = session.get('current_material', 0)
    
    if current >= len(items):
        from .results import calculate_final_result
        await calculate_final_result(update_obj, user_id)
        return
    
    item = items[current]
    
    text = f"📦 ВВОД НЕДОСТАЮЩИХ ЦЕН ({current + 1}/{len(items)})\n\n"
    text += f"Элемент: {item['name']}\n"
    text += f"Необходимое количество: {format_number(item['qty'])} шт\n\n"
    text += "Введите цену за 1 шт (ISK):"
    
    if is_callback and hasattr(update_obj, 'edit_message_text'):
        await update_obj.edit_message_text(text, reply_markup=cancel_button(user_id))
    else:
        await update_obj.message.reply_text(text, reply_markup=cancel_button(user_id))


async def process_missing_price_value(update: Update, user_id: int, text: str):
    from utils.formatters import parse_float_input
    
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
        item['original']['price'] = price
        
        save_material_price(item['name'], price)
        
        if item.get('type') == 'material':
            for m in session.get('materials_list', []):
                if m['name'] == item['name']:
                    m['price'] = price
        elif item.get('type') == 'node':
            for n in session.get('nodes_list', []):
                if n['name'] == item['name']:
                    n['price'] = price
        elif item.get('type') == 'drawing':
            for d in session.get('drawings_list', []):
                if d['name'] == item['name']:
                    d['price'] = price
        
        session['current_material'] = current + 1
        await _process_next_missing_price(update, user_id, is_callback=False)
# Добавьте в конец файла materials.py:

async def back_to_materials(update: Update, user_id: int):
    """Возврат к списку материалов"""
    session = get_session(user_id)
    session['step'] = 'materials'
    session['materials_page'] = 0
    await _show_materials_list(update, user_id, is_multi=False, mode=session.get('calculation_mode', 'buy_nodes'))
