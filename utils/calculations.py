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
    if user_efficiency is None:
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
    if value is None:
        return 0
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
    
    if needed_qty is None:
        needed_qty = 0
    
    needed = math.ceil(needed_qty)
    drawings = math.ceil(needed / multiplicity)
    leftover = (drawings * multiplicity) - needed
    
    return drawings, leftover


def calculate_node_cost(drawings: int, node_price: float) -> float:
    """Рассчитывает стоимость чертежей узла"""
    if drawings is None:
        drawings = 0
    if node_price is None:
        node_price = 0
    return drawings * node_price


def calculate_total_cost(materials_cost: float, production_cost: float, drawings_cost: float) -> float:
    """Рассчитывает себестоимость"""
    return (materials_cost or 0) + (production_cost or 0) + (drawings_cost or 0)


def calculate_profit(revenue: float, total_cost: float) -> float:
    """Рассчитывает прибыль до налога"""
    return (revenue or 0) - (total_cost or 0)


def calculate_tax(profit: float, tax_rate: float) -> float:
    """Рассчитывает налог (только при положительной прибыли)"""
    if profit is None or profit <= 0:
        return 0
    if tax_rate is None:
        return 0
    return profit * (tax_rate / 100)


def calculate_profit_after_tax(profit: float, tax: float) -> float:
    """Рассчитывает прибыль после налога"""
    return (profit or 0) - (tax or 0)


def merge_materials(materials_list: List[Dict]) -> List[Dict]:
    """
    Объединяет одинаковые материалы/узлы из списка
    
    Args:
        materials_list: список словарей с ключами 'name', 'qty', 'price', 'type', 'code', 'multiplicity'
    
    Returns:
        объединённый список с пронумерованными элементами
    """
    if not materials_list:
        return []
    
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
