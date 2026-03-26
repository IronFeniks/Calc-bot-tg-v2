import logging
import math
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from keyboards.calculator import materials_keyboard, missing_prices_keyboard, cancel_button
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
    
    if efficiency is None:
        logger.error(f"efficiency is None в calculate_single_materials для пользователя {user_id}")
        await update.message.reply_text(
            "❌ Ошибка: не задана эффективность. Пожалуйста, начните расчёт заново с /start",
            reply_markup=cancel_button(user_id)
        )
        return
    
    saved_prices = get_all_material_prices()
    
    materials_list, nodes_list = await _calculate_materials(
        product['Код'], quantity, efficiency, excel, saved_prices
    )
    
    session['materials_list'] = materials_list
    session['nodes_list'] = nodes_list
    session['single_product_detail'] = {
        'product': product,
        'quantity': quantity,
        'drawings_needed': math.ceil(quantity / product.get('Кратность', 1))
    }
    session['step'] = 'materials'
    session['materials_page'] = 0
    
    await _show_materials_list(update, user_id, is_multi=False)


async def calculate_multi_materials(update, user_id: int):
    """Расчёт материалов для множественного режима"""
    session = get_session(user_id)
    excel = get_excel_handler()
    products_data = session.get('multi_products_data', [])
    efficiency = session.get('efficiency')
    
    if efficiency is None:
        logger.error(f"efficiency is None в calculate_multi_materials для пользователя {user_id}")
        await update.message.reply_text(
            "❌ Ошибка: не задана эффективность. Пожалуйста, начните расчёт заново с /start",
            reply_markup=cancel_button(user_id)
        )
        return
    
    saved_prices = get_all_material_prices()
    
    all_materials = []
    all_nodes = []
    products_with_details = []
    
    for data in products_data:
        product = data['product']
        quantity = data['quantity']
        
        materials_list, nodes_list = await _calculate_materials(
            product['Код'], quantity, efficiency, excel, saved_prices
        )
        
        all_materials.extend(materials_list)
        all_nodes.extend(nodes_list)
        
        products_with_details.append({
            'product': product,
            'quantity': quantity,
            'market_price': data['market_price'],
            'drawing_price': data['drawing_price'],
            'materials_list': materials_list,
            'drawings_needed': math.ceil(quantity / product.get('Кратность', 1)),
            'node_details': nodes_list
        })
    
    merged_materials = merge_materials(all_materials)
    
    merged_nodes = {}
    for node in all_nodes:
        name = node['name']
        if name not in merged_nodes:
            merged_nodes[name] = node.copy()
            merged_nodes[name]['needed_qty'] = 0
            merged_nodes[name]['drawings'] = 0
            merged_nodes[name]['total_cost'] = 0
        merged_nodes[name]['needed_qty'] += node['needed_qty']
        merged_nodes[name]['drawings'] += node['drawings']
        merged_nodes[name]['total_cost'] += node['total_cost']
    
    nodes_list = list(merged_nodes.values())
    nodes_list.sort(key=lambda x: x['name'])
    for i, node in enumerate(nodes_list, 1):
        node['number'] = i
    
    session['materials_list'] = merged_materials
    session['nodes_list'] = nodes_list
    session['products_with_details'] = products_with_details
    session['step'] = 'materials'
    session['materials_page'] = 0
    
    await _show_materials_list(update, user_id, is_multi=True)


async def _calculate_materials(product_code: str, quantity: int, efficiency: float, excel, saved_prices):
    """Внутренняя функция расчёта материалов"""
    product = excel.get_product_by_code(product_code)
    if not product:
        return [], []
    
    multiplicity = product.get('Кратность', 1)
    drawings_needed = math.ceil(quantity / multiplicity)
    
    materials_dict = {}
    node_details = []
    
    def collect_materials(code: str, multiplier: float):
        specs = excel.get_specifications(code)
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
                
                node_details.append({
                    'name': child_name,
                    'needed_qty': total_qty,
                    'drawings': node_drawings,
                    'multiplicity': node_multiplicity,
                    'leftover': node_leftover,
                    'price_per_drawing': child_price,
                    'total_cost': node_drawings * child_price
                })
                
                if child_name not in materials_dict:
                    materials_dict[child_name] = {
                        'name': child_name,
                        'qty': total_qty,
                        'price': child_price,
                        'type': 'node',
                        'code': child_code,
                        'multiplicity': node_multiplicity
                    }
                else:
                    materials_dict[child_name]['qty'] += total_qty
                
                collect_materials(child_code, total_qty)
    
    collect_materials(product_code, drawings_needed)
    
    materials_list = list(materials_dict.values())
    materials_list.sort(key=lambda x: x['name'])
    for i, item in enumerate(materials_list, 1):
        item['number'] = i
    
    return materials_list, node_details


async def _show_materials_list(update_obj, user_id: int, is_multi: bool = False):
    """Показывает список материалов и узлов"""
    session = get_session(user_id)
    materials = session.get('materials_list', [])
    nodes = session.get('nodes_list', [])
    
    all_items = materials + nodes
    all_items.sort(key=lambda x: x.get('number', 0))
    
    for i, item in enumerate(all_items, 1):
        item['display_number'] = i
    
    total_pages = (len(all_items) + 9) // 10
    page = session.get('materials_page', 0)
    start = page * 10
    end = min(start + 10, len(all_items))
    page_items = all_items[start:end]
    
    text = "📦 МАТЕРИАЛЫ И УЗЛЫ\n\n"
    if not is_multi:
        product = session.get('selected_product', {})
        text += f"Изделие: {product.get('Наименование', '')}\n"
    else:
        text += f"Режим: множественный расчёт\n"
    text += f"Эффективность: {session.get('efficiency', 150)}%\n\n"
    text += f"Страница {page + 1} из {total_pages}\n\n"
    
    materials_in_page = [i for i in page_items if i.get('type') == 'material']
    if materials_in_page:
        text += "МАТЕРИАЛЫ:\n"
        for item in materials_in_page:
            text += format_material_line(
                item['display_number'], item['name'], item['qty'], item.get('price', 0)
            ) + "\n"
        text += "\n"
    
    nodes_in_page = [i for i in page_items if i.get('type') == 'node']
    if nodes_in_page:
        text += "УЗЛЫ:\n"
        for item in nodes_in_page:
            text += format_material_line(
                item['display_number'], item['name'], item['qty'], item.get('price', 0)
            ) + "\n"
        text += "\n"
    
    missing = [i for i in all_items if i.get('price', 0) == 0]
    session['missing_materials'] = missing
    
    # Определяем, с чем работаем: с Update или с CallbackQuery
    if isinstance(update_obj, CallbackQuery):
        await update_obj.edit_message_text(
            text,
            reply_markup=materials_keyboard(all_items, user_id, page + 1, total_pages, "multi" if is_multi else "single")
        )
    else:
        await update_obj.message.reply_text(
            text,
            reply_markup=materials_keyboard(all_items, user_id, page + 1, total_pages, "multi" if is_multi else "single")
        )


async def start_price_input(query, user_id: int):
    """Начало пошагового ввода цен (вызывается из callback)"""
    session = get_session(user_id)
    materials = session.get('materials_list', [])
    nodes = session.get('nodes_list', [])
    
    all_items = materials + nodes
    all_items.sort(key=lambda x: x.get('number', 0))
    
    session['price_input_items'] = all_items
    session['current_material'] = 0
    session['step'] = 'price_input_waiting'
    
    await _process_next_price(query, user_id, is_callback=True)


async def _process_next_price(update_obj, user_id: int, is_callback: bool = True):
    """Ввод цены для следующего элемента"""
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
    elif hasattr(update_obj, 'message') and hasattr(update_obj.message, 'reply_text'):
        await update_obj.message.reply_text(text, reply_markup=cancel_button(user_id))
    else:
        await update_obj.reply_text(text, reply_markup=cancel_button(user_id))


async def process_price_input_value(update: Update, user_id: int, text: str):
    """Обработка введённой цены (вызывается из текстового обработчика)"""
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
        
        save_material_price(item['name'], price)
        
        if item.get('type') == 'material':
            for m in session.get('materials_list', []):
                if m['name'] == item['name']:
                    m['price'] = price
        else:
            for n in session.get('nodes_list', []):
                if n['name'] == item['name']:
                    n['price'] = price
        
        session['current_material'] = current + 1
        await _process_next_price(update, user_id, is_callback=False)


async def auto_prices(query, user_id: int):
    """Автоматическая подстановка цен (вызывается из callback)"""
    session = get_session(user_id)
    materials = session.get('materials_list', [])
    nodes = session.get('nodes_list', [])
    all_items = materials + nodes
    
    missing = [i for i in all_items if i.get('price', 0) == 0]
    
    if missing:
        text = "🤖 АВТОМАТИЧЕСКАЯ ПОДСТАНОВКА ЦЕН\n\n"
        text += f"✅ Цены подставлены для: {len(all_items) - len(missing)} элементов\n"
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
    """Ввод только недостающих цен (вызывается из callback)"""
    session = get_session(user_id)
    missing = session.get('missing_materials', [])
    
    session['price_input_items'] = missing
    session['current_material'] = 0
    session['step'] = 'price_input_missing_waiting'
    
    await _process_next_missing_price(query, user_id, is_callback=True)


async def _process_next_missing_price(update_obj, user_id: int, is_callback: bool = True):
    """Ввод цены для недостающего элемента"""
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
    elif hasattr(update_obj, 'message') and hasattr(update_obj.message, 'reply_text'):
        await update_obj.message.reply_text(text, reply_markup=cancel_button(user_id))
    else:
        await update_obj.reply_text(text, reply_markup=cancel_button(user_id))


async def process_missing_price_value(update: Update, user_id: int, text: str):
    """Обработка введённой цены для недостающего элемента"""
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
        
        save_material_price(item['name'], price)
        
        if item.get('type') == 'material':
            for m in session.get('materials_list', []):
                if m['name'] == item['name']:
                    m['price'] = price
        else:
            for n in session.get('nodes_list', []):
                if n['name'] == item['name']:
                    n['price'] = price
        
        session['current_material'] = current + 1
        await _process_next_missing_price(update, user_id, is_callback=False)
