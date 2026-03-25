"""
Валидаторы для проверки ввода пользователя
"""

import re
from typing import Optional, Union


def validate_efficiency(value: str) -> Optional[float]:
    """
    Проверяет корректность ввода эффективности
    
    Args:
        value: строка с числом
    
    Returns:
        число от 50 до 150 или None если невалидно
    """
    try:
        cleaned = re.sub(r'[^\d.-]', '', value.strip())
        efficiency = float(cleaned)
        if 50 <= efficiency <= 150:
            return efficiency
        return None
    except ValueError:
        return None


def validate_tax(value: str) -> Optional[float]:
    """
    Проверяет корректность ввода налога
    
    Args:
        value: строка с числом
    
    Returns:
        число от 0 до 100 или None если невалидно
    """
    try:
        cleaned = re.sub(r'[^\d.-]', '', value.strip())
        tax = float(cleaned)
        if 0 <= tax <= 100:
            return tax
        return None
    except ValueError:
        return None


def validate_quantity(value: str, multiplicity: int = 1) -> Optional[int]:
    """
    Проверяет корректность ввода количества
    
    Args:
        value: строка с числом
        multiplicity: кратность (количество должно быть кратно этому числу)
    
    Returns:
        целое положительное число, кратное multiplicity, или None
    """
    try:
        cleaned = re.sub(r'[^\d]', '', value.strip())
        qty = int(cleaned)
        if qty > 0 and qty % multiplicity == 0:
            return qty
        return None
    except ValueError:
        return None


def validate_price(value: str) -> Optional[float]:
    """
    Проверяет корректность ввода цены
    
    Args:
        value: строка с числом
    
    Returns:
        неотрицательное число или None
    """
    try:
        cleaned = re.sub(r'[^\d.-]', '', value.strip())
        price = float(cleaned)
        if price >= 0:
            return price
        return None
    except ValueError:
        return None


def validate_int(value: str, min_val: int = None, max_val: int = None) -> Optional[int]:
    """
    Проверяет корректность ввода целого числа
    
    Args:
        value: строка с числом
        min_val: минимальное значение (опционально)
        max_val: максимальное значение (опционально)
    
    Returns:
        целое число или None
    """
    try:
        cleaned = re.sub(r'[^\d-]', '', value.strip())
        num = int(cleaned)
        if min_val is not None and num < min_val:
            return None
        if max_val is not None and num > max_val:
            return None
        return num
    except ValueError:
        return None


def validate_float(value: str, min_val: float = None, max_val: float = None) -> Optional[float]:
    """
    Проверяет корректность ввода числа с плавающей точкой
    
    Args:
        value: строка с числом
        min_val: минимальное значение (опционально)
        max_val: максимальное значение (опционально)
    
    Returns:
        число или None
    """
    try:
        cleaned = re.sub(r'[^\d.-]', '', value.strip())
        num = float(cleaned)
        if min_val is not None and num < min_val:
            return None
        if max_val is not None and num > max_val:
            return None
        return num
    except ValueError:
        return None


def validate_category_name(value: str) -> Optional[str]:
    """
    Проверяет корректность ввода названия категории
    
    Args:
        value: строка с названием
    
    Returns:
        очищенная строка или None
    """
    if not value:
        return None
    
    cleaned = value.strip()
    if len(cleaned) < 2:
        return None
    
    return cleaned


def validate_product_name(value: str) -> Optional[str]:
    """
    Проверяет корректность ввода названия изделия/узла/материала
    
    Args:
        value: строка с названием
    
    Returns:
        очищенная строка или None
    """
    if not value:
        return None
    
    cleaned = value.strip()
    if len(cleaned) < 2:
        return None
    
    return cleaned


def validate_multiplicity(value: str) -> Optional[int]:
    """
    Проверяет корректность ввода кратности
    
    Args:
        value: строка с числом
    
    Returns:
        целое положительное число или None
    """
    try:
        cleaned = re.sub(r'[^\d]', '', value.strip())
        mult = int(cleaned)
        if mult > 0:
            return mult
        return None
    except ValueError:
        return None


def validate_user_id(value: str) -> Optional[int]:
    """
    Проверяет корректность ввода Telegram ID
    
    Args:
        value: строка с числом
    
    Returns:
        целое положительное число или None
    """
    try:
        cleaned = re.sub(r'[^\d]', '', value.strip())
        user_id = int(cleaned)
        if user_id > 0:
            return user_id
        return None
    except ValueError:
        return None


def validate_search_query(value: str) -> Optional[str]:
    """
    Проверяет корректность поискового запроса
    
    Args:
        value: строка для поиска
    
    Returns:
        очищенная строка или None
    """
    if not value:
        return None
    
    cleaned = value.strip().lower()
    if len(cleaned) < 2:
        return None
    
    return cleaned
