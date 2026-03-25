import math
import re

def format_number(num: float) -> str:
    """Форматирует число с пробелами между разрядами"""
    if num is None:
        return "0"
    return f"{num:,.0f}".replace(",", " ")

def format_price(price: float) -> str:
    """Форматирует цену с пробелами и суффиксом ISK"""
    if price is None or price == 0:
        return "0 ISK"
    return f"{format_number(price)} ISK"

def parse_price_input(text: str) -> float:
    """Парсит ввод цены (убирает пробелы, проверяет число)"""
    cleaned = re.sub(r'[^\d.-]', '', text.strip())
    try:
        return float(cleaned)
    except ValueError:
        return None

def parse_int_input(text: str) -> int:
    """Парсит ввод целого числа"""
    cleaned = re.sub(r'[^\d-]', '', text.strip())
    try:
        return int(cleaned)
    except ValueError:
        return None

def parse_float_input(text: str) -> float:
    """Парсит ввод числа с плавающей точкой"""
    cleaned = re.sub(r'[^\d.-]', '', text.strip())
    try:
        return float(cleaned)
    except ValueError:
        return None

def format_material_line(number: int, name: str, qty: float, price: float = None) -> str:
    """Форматирует строку материала для списка"""
    if price is not None:
        return f"{number}. {name}: нужно {format_number(qty)} шт | цена: {format_price(price)}"
    return f"{number}. {name}: нужно {format_number(qty)} шт"

def format_material_result_line(number: int, name: str, qty: float, price: float, cost: float) -> str:
    """Форматирует строку материала для результата"""
    return f"{number}. {name}: {format_number(qty)} шт × {format_number(price)} = {format_number(cost)} ISK"

def format_node_result_line(number: int, name: str, qty: float, drawings: int, multiplicity: int) -> str:
    """Форматирует строку узла для результата"""
    return f"{number}. {name}: нужно {format_number(qty)} шт | чертежей: {drawings} шт (кратность {multiplicity})"

def format_leftover_line(name: str, leftover: int) -> str:
    """Форматирует строку остатка узла"""
    return f"• {name}: {format_number(leftover)} шт"

def format_category_path(path: list) -> str:
    """Форматирует путь категории"""
    return " > ".join(path) if path else ""

def truncate_text(text: str, max_length: int = 30) -> str:
    """Обрезает текст до max_length, добавляя ..."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
