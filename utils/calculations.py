import math
from typing import Tuple, List, Dict, Any

def calculate_with_efficiency(base_qty: float, user_efficiency: float) -> float:
    """
    Рассчитывает количество материала/узла на 1 чертёж изделия
    Формула: raw = base_qty × (user_efficiency / 150)
    
    Args:
        base_qty: количество из Excel (при 150% эффективности)
        user_efficiency: эффективность пользователя (от 90% до 150%)
    
    Returns:
        количество на 1 чертёж (без округления)
    """
    if base_qty is None or base_qty <= 0:
        return 0
    return base_qty * (user_efficiency / 150)


def round_quantity(value: float) -> int:
    """
    Округление количества:
    - Если значение > 20 → округление вверх (ceil)
    - Если значение ≤ 20 → математическое округление (0.5 вверх)
    
    Args:
        value: значение для округления
    
    Returns:
        округлённое целое число
    """
    if value > 20:
        return math.ceil(value)
    return round(value)


def calculate_node_drawings(needed_qty: float, multiplicity: int) -> Tuple[int, int]:
    """
    Рассчитывает количество чертежей узла и остаток
    
    Args:
        needed_qty: необходимое количество узлов
        multiplicity: кратность узла (сколько получается из одного чертежа)
    
    Returns:
        (drawings, leftover) — количество чертежей и остаток
    """
    if multiplicity <= 0:
        multiplicity = 1
    
    needed = math.ceil(needed_qty)
    drawings = math.ceil(needed / multiplicity)
    leftover = (drawings * multiplicity) - needed
    
    return drawings, leftover


def calculate_node_cost(drawings: int, node_price: float) -> float:
    """Рассчитывает стоимость чертежей узла"""
    return drawings * node_price


def calculate_total_cost(materials_cost: float, production_cost: float, drawings_cost: float) -> float:
    """Рассчитывает себестоимость"""
    return materials_cost + production_cost + drawings_cost


def calculate_profit(revenue: float, total_cost: float) -> float:
    """Рассчитывает прибыль до налога"""
    return revenue - total_cost


def calculate_tax(profit: float, tax_rate: float) -> float:
    """Рассчитывает налог (только при положительной прибыли)"""
    if profit <= 0:
        return 0
    return profit * (tax_rate / 100)


def calculate_profit_after_tax(profit: float, tax: float) -> float:
    """Рассчитывает прибыль после налога"""
    return profit - tax


def merge_materials(materials_list: List[Dict]) -> List[Dict]:
    """
    Объединяет одинаковые материалы/узлы из списка
    
    Args:
        materials_list: список словарей с ключами 'name', 'qty', 'price', 'type', 'code', 'multiplicity'
    
    Returns:
        объединённый список с пронумерованными элементами
    """
    merged = {}
    for item in materials_list:
        name = item['name']
        if name not in merged:
            merged[name] = {
                'name': name,
                'qty': 0,
                'price': item.get('price', 0),
                'type': item.get('type', 'material'),
                'code': item.get('code', ''),
                'multiplicity': item.get('multiplicity', 1)
            }
        merged[name]['qty'] += item['qty']
    
    # Преобразуем обратно в список, сортируем по имени
    result = list(merged.values())
    result.sort(key=lambda x: x['name'])
    
    # Добавляем номера
    for i, item in enumerate(result, 1):
        item['number'] = i
    
    return result


def calculate_materials_for_product(
    product_code: str,
    quantity: int,
    efficiency: float,
    excel_handler,
    saved_prices: Dict[str, float]
) -> Tuple[List[Dict], int, float, List[Dict]]:
    """
    Рассчитывает все материалы и узлы для одного изделия
    
    Args:
        product_code: код изделия
        quantity: количество изделий
        efficiency: эффективность (%)
        excel_handler: обработчик Excel
        saved_prices: сохранённые цены материалов
    
    Returns:
        (materials_list, drawings_needed, drawing_cost, node_details)
        - materials_list: список материалов и узлов
        - drawings_needed: количество чертежей изделия
        - drawing_cost: стоимость чертежа изделия
        - node_details: детали по узлам (для отображения)
    """
    product = excel_handler.get_product_by_code(product_code)
    if not product:
        return [], 0, 0, []
    
    multiplicity = product.get('Кратность', 1)
    drawings_needed = math.ceil(quantity / multiplicity)
    
    materials_dict = {}
    node_details = []
    
    def collect_materials(code: str, multiplier: float, parent_is_node: bool = False):
        specs = excel_handler.get_specifications(code)
        for spec in specs:
            child_code = spec['child']
            child_qty = spec['quantity']
            child = excel_handler.get_product_by_code(child_code)
            
            if not child:
                continue
            
            child_type = child.get('Тип', '').lower()
            child_name = child.get('Наименование', '')
            child_price = child.get('Цена производства', '0 ISK')
            
            # Парсим цену
            try:
                child_price_value = float(str(child_price).replace(' ISK', '').replace(' ', ''))
            except:
                child_price_value = 0
            
            # Расчёт с учётом эффективности
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
                # Сохраняем детали узла
                node_multiplicity = child.get('Кратность', 1)
                node_drawings, node_leftover = calculate_node_drawings(total_qty, node_multiplicity)
                
                node_details.append({
                    'name': child_name,
                    'needed_qty': total_qty,
                    'drawings': node_drawings,
                    'multiplicity': node_multiplicity,
                    'leftover': node_leftover,
                    'price_per_drawing': child_price_value,
                    'total_cost': node_drawings * child_price_value
                })
                
                # Добавляем узел в общий список материалов (как отдельный элемент)
                if child_name not in materials_dict:
                    materials_dict[child_name] = {
                        'name': child_name,
                        'qty': total_qty,
                        'price': child_price_value,
                        'type': 'node',
                        'code': child_code,
                        'multiplicity': node_multiplicity
                    }
                else:
                    materials_dict[child_name]['qty'] += total_qty
                
                # Рекурсивно собираем материалы узла
                collect_materials(child_code, total_qty, parent_is_node=True)
    
    collect_materials(product_code, drawings_needed)
    
    # Преобразуем в список и сортируем
    materials_list = list(materials_dict.values())
    materials_list.sort(key=lambda x: x['name'])
    
    # Добавляем номера
    for i, item in enumerate(materials_list, 1):
        item['number'] = i
    
    return materials_list, drawings_needed, node_details


def calculate_total_summary(products_data: List[Dict]) -> Dict:
    """
    Рассчитывает общую сводку для множественного расчёта
    
    Args:
        products_data: список данных по каждому изделию
            каждый элемент: {
                'product': dict,
                'quantity': int,
                'market_price': float,
                'drawing_price': float,
                'materials_list': list,
                'drawings_needed': int,
                'node_details': list
            }
    
    Returns:
        словарь с общей сводкой
    """
    total_materials_cost = 0
    total_production_cost = 0
    total_drawings_cost = 0
    total_revenue = 0
    total_materials_dict = {}
    total_node_details = []
    
    for data in products_data:
        product = data['product']
        quantity = data['quantity']
        market_price = data['market_price']
        drawing_price = data['drawing_price']
        materials_list = data['materials_list']
        drawings_needed = data['drawings_needed']
        
        # Суммируем материалы
        for material in materials_list:
            name = material['name']
            qty = material['qty']
            price = material['price']
            cost = qty * price
            
            total_materials_cost += cost
            
            if name not in total_materials_dict:
                total_materials_dict[name] = {
                    'name': name,
                    'qty': 0,
                    'price': price,
                    'cost': 0
                }
            total_materials_dict[name]['qty'] += qty
            total_materials_dict[name]['cost'] += cost
        
        # Производство
        prod_price = 0
        prod_price_str = product.get('Цена производства', '0 ISK')
        try:
            prod_price = float(str(prod_price_str).replace(' ISK', '').replace(' ', ''))
        except:
            pass
        total_production_cost += prod_price * drawings_needed
        
        # Чертежи
        total_drawings_cost += drawing_price * drawings_needed
        
        # Выручка
        total_revenue += market_price * quantity
        
        # Собираем узлы
        for node in data.get('node_details', []):
            total_node_details.append(node)
    
    # Объединяем одинаковые узлы
    merged_nodes = {}
    for node in total_node_details:
        name = node['name']
        if name not in merged_nodes:
            merged_nodes[name] = {
                'name': name,
                'needed_qty': 0,
                'drawings': 0,
                'multiplicity': node['multiplicity'],
                'leftover': 0,
                'total_cost': 0
            }
        merged_nodes[name]['needed_qty'] += node['needed_qty']
        merged_nodes[name]['drawings'] += node['drawings']
        merged_nodes[name]['total_cost'] += node['total_cost']
    
    # Формируем итоговый список материалов
    total_materials = list(total_materials_dict.values())
    total_materials.sort(key=lambda x: x['name'])
    for i, item in enumerate(total_materials, 1):
        item['number'] = i
    
    # Формируем итоговый список узлов
    total_nodes = list(merged_nodes.values())
    total_nodes.sort(key=lambda x: x['name'])
    for i, item in enumerate(total_nodes, 1):
        item['number'] = i
    
    total_cost = total_materials_cost + total_production_cost + total_drawings_cost
    profit_before_tax = total_revenue - total_cost
    
    return {
        'materials': total_materials,
        'nodes': total_nodes,
        'materials_cost': total_materials_cost,
        'production_cost': total_production_cost,
        'drawings_cost': total_drawings_cost,
        'total_cost': total_cost,
        'revenue': total_revenue,
        'profit_before_tax': profit_before_tax
    }
