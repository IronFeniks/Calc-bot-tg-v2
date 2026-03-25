import math

def calculate_with_efficiency(base_qty: float, user_efficiency: float) -> float:
    """
    Рассчитывает количество материала/узла на 1 чертёж изделия
    Формула: raw = base_qty × (user_efficiency / 150)
    """
    if base_qty is None or base_qty <= 0:
        return 0
    raw = base_qty * (user_efficiency / 150)
    return raw

def round_quantity(value: float) -> int:
    """
    Округление количества:
    - Если значение > 20 → округление вверх (ceil)
    - Если значение ≤ 20 → математическое округление (0.5 вверх)
    """
    if value > 20:
        return math.ceil(value)
    return round(value)

def calculate_node_drawings(needed_qty: float, multiplicity: int) -> tuple:
    """
    Рассчитывает количество чертежей узла и остаток
    
    Returns:
        (drawings, leftover)
    """
    if multiplicity <= 0:
        multiplicity = 1
    
    needed = math.ceil(needed_qty)  # Сначала округляем нужное количество до целого
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

def merge_materials(materials_list: list) -> list:
    """
    Объединяет одинаковые материалы/узлы из списка
    
    Args:
        materials_list: список словарей с ключами 'name', 'qty', 'price', 'type'
    
    Returns:
        объединённый список
    """
    merged = {}
    for item in materials_list:
        name = item['name']
        if name not in merged:
            merged[name] = {
                'name': name,
                'qty': 0,
                'price': item.get('price', 0),
                'type': item.get('type', 'material')
            }
        merged[name]['qty'] += item['qty']
    
    # Преобразуем обратно в список, сортируем по имени
    result = list(merged.values())
    result.sort(key=lambda x: x['name'])
    
    # Добавляем номера
    for i, item in enumerate(result, 1):
        item['number'] = i
    
    return result
