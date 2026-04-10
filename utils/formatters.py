import math
import re
from typing import List, Dict, Any, Optional

# ==================== ФОРМАТИРОВАНИЕ ЧИСЕЛ ====================

def format_number(num: float) -> str:
    """
    Форматирует число с пробелами между разрядами (целая часть)
    
    Args:
        num: число для форматирования
    
    Returns:
        строка с пробелами между разрядами
    """
    if num is None:
        return "0"
    if isinstance(num, float) and num.is_integer():
        return f"{int(num):,}".replace(",", " ")
    return f"{num:,.0f}".replace(",", " ")


def format_number_decimal(num: float, decimals: int = 2) -> str:
    """
    Форматирует число с пробелами между разрядами и десятичной частью
    
    Args:
        num: число для форматирования
        decimals: количество знаков после запятой
    
    Returns:
        строка с пробелами между разрядами
    """
    if num is None:
        return "0"
    formatted = f"{num:,.{decimals}f}".replace(",", " ")
    return formatted


def format_price(price: float) -> str:
    """
    Форматирует цену с пробелами и суффиксом ISK
    
    Args:
        price: цена в ISK
    
    Returns:
        строка вида "5 400 000 000 ISK"
    """
    if price is None or price == 0:
        return "0 ISK"
    return f"{format_number(price)} ISK"


def format_price_inline(price: float) -> str:
    """
    Форматирует цену для встраивания в текст (без суффикса ISK)
    
    Args:
        price: цена в ISK
    
    Returns:
        строка вида "5 400 000 000"
    """
    if price is None or price == 0:
        return "0"
    return format_number(price)


# ==================== ПАРСИНГ ВВОДА ====================

def parse_price_input(text: str) -> Optional[float]:
    """
    Парсит ввод цены (убирает пробелы, проверяет число)
    
    Args:
        text: строка с ценой (например "5 400 000 000" или "5400000000")
    
    Returns:
        число или None если не удалось распарсить
    """
    cleaned = re.sub(r'[^\d.-]', '', text.strip())
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_int_input(text: str) -> Optional[int]:
    """
    Парсит ввод целого числа
    
    Args:
        text: строка с числом
    
    Returns:
        целое число или None
    """
    cleaned = re.sub(r'[^\d-]', '', text.strip())
    try:
        return int(cleaned)
    except ValueError:
        return None


def parse_float_input(text: str) -> Optional[float]:
    """
    Парсит ввод числа с плавающей точкой
    
    Args:
        text: строка с числом
    
    Returns:
        число или None
    """
    cleaned = re.sub(r'[^\d.-]', '', text.strip())
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_excel_price(price_str: str) -> float:
    """
    Парсит цену из Excel (формат "5 400 000 000 ISK")
    
    Args:
        price_str: строка цены из Excel
    
    Returns:
        число в ISK
    """
    if not price_str:
        return 0
    cleaned = re.sub(r'[^\d]', '', str(price_str))
    try:
        return float(cleaned)
    except ValueError:
        return 0


# ==================== ФОРМАТИРОВАНИЕ СПИСКОВ ====================

def format_material_line(number: int, name: str, qty: float, price: float = None) -> str:
    """
    Форматирует строку материала для списка (экран выбора цен)
    
    Args:
        number: порядковый номер
        name: название материала/узла
        qty: количество
        price: цена (опционально)
    
    Returns:
        отформатированная строка
    """
    qty_str = format_number(qty)
    if price is not None:
        price_str = format_price(price) if price > 0 else "не установлена"
        return f"{number}. {name}: нужно {qty_str} шт | цена: {price_str}"
    return f"{number}. {name}: нужно {qty_str} шт"


def format_material_result_line(number: int, name: str, qty: float, price: float, cost: float) -> str:
    """
    Форматирует строку материала для результата
    
    Args:
        number: порядковый номер
        name: название
        qty: количество
        price: цена за единицу
        cost: общая стоимость
    
    Returns:
        отформатированная строка
    """
    qty_str = format_number(qty)
    price_str = format_price_inline(price)
    cost_str = format_price(cost)
    return f"{number}. {name}: {qty_str} шт x {price_str} = {cost_str}"


def format_node_result_line(number: int, name: str, needed_qty: float, 
                            drawings: int, multiplicity: int, leftover: int = None) -> str:
    """
    Форматирует строку узла для результата
    
    Args:
        number: порядковый номер
        name: название узла
        needed_qty: необходимое количество
        drawings: количество чертежей
        multiplicity: кратность
        leftover: остаток (опционально)
    
    Returns:
        отформатированная строка
    """
    qty_str = format_number(needed_qty)
    if leftover is not None and leftover > 0:
        return f"{number}. {name}: нужно {qty_str} шт | чертежей: {drawings} шт (кратность {multiplicity}) | остаток: {leftover} шт"
    return f"{number}. {name}: нужно {qty_str} шт | чертежей: {drawings} шт (кратность {multiplicity})"


def format_leftover_line(name: str, leftover: int) -> str:
    """
    Форматирует строку остатка узла
    
    Args:
        name: название узла
        leftover: количество остатка
    
    Returns:
        отформатированная строка
    """
    return f"• {name}: {format_number(leftover)} шт"


def format_category_path(path: List[str]) -> str:
    """
    Форматирует путь категории
    
    Args:
        path: список категорий
    
    Returns:
        строка вида "Категория1 > Категория2 > Категория3"
    """
    return " > ".join(path) if path else ""


def truncate_text(text: str, max_length: int = 30) -> str:
    """
    Обрезает текст до max_length, добавляя ...
    
    Args:
        text: исходный текст
        max_length: максимальная длина
    
    Returns:
        обрезанный текст
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


# ==================== ФОРМАТИРОВАНИЕ РЕЗУЛЬТАТОВ ====================

def format_result_table(title: str, rows: List[tuple], width: int = 21) -> str:
    """
    Форматирует таблицу для результатов
    
    Args:
        title: заголовок таблицы (не используется, оставлен для совместимости)
        rows: список кортежей (label, value)
        width: ширина левой колонки
    
    Returns:
        отформатированная таблица
    """
    lines = []
    for label, value in rows:
        padding = width - len(label)
        if padding < 0:
            padding = 0
        lines.append(f"│ {label}{' ' * padding}│ {value} │")
    return "\n".join(lines)


def format_total_result(
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
    """
    Форматирует итоговую таблицу результатов (старая версия с таблицей)
    """
    lines = [
        "💰 ИТОГИ",
        "┌─────────────────────┬──────────────────┐",
        f"│ Материалы           │ {format_price(materials_cost):>16} │",
        f"│ Производство        │ {format_price(production_cost):>16} │",
        f"│ Чертежи             │ {format_price(drawings_cost):>16} │",
        "├─────────────────────┼──────────────────┤",
        f"│ СЕБЕСТОИМОСТЬ       │ {format_price(total_cost):>16} │",
        "├─────────────────────┼──────────────────┤",
        f"│ Выручка             │ {format_price(revenue):>16} │",
        f"│ Прибыль до налога   │ {format_price(profit_before_tax):>16} │",
        f"│ Налог               │ {format_price(tax):>16} │",
        "├─────────────────────┼──────────────────┤",
        f"│ ПРИБЫЛЬ ПОСЛЕ НАЛОГА│ {format_price(profit_after_tax):>16} │",
        "└─────────────────────┴──────────────────┘"
    ]
    
    if per_unit_cost is not None:
        lines.append("")
        lines.append("📏 НА 1 ШТУКУ:")
        lines.append(f"• Себестоимость: {format_price(per_unit_cost)}")
        if per_unit_profit is not None:
            lines.append(f"• Прибыль: {format_price(per_unit_profit)}")
    
    return "\n".join(lines)


def format_explanation() -> str:
    """
    Возвращает текст пояснения по расчётам
    БЕЗ Markdown-разметки, чтобы избежать ошибок парсинга
    """
    return """📖 ПОЯСНЕНИЕ ПО ЦИФРАМ

💰 МАТЕРИАЛЫ
• Сумма всех затрат на материалы
• Рассчитывается как: количество x цена за 1 шт

🏭 ПРОИЗВОДСТВО
• Фиксированная стоимость производства
• Берется из базы данных для выбранного изделия
• Умножается на количество чертежей

📄 ЧЕРТЕЖИ
• Стоимость разработки чертежей
• Включает: чертеж изделия + чертежи всех узлов
• Стоимость чертежа узла = цена производства узла x (нужное количество / кратность узла)

💵 СЕБЕСТОИМОСТЬ
• Материалы + Производство + Чертежи

📈 ВЫРУЧКА
• Рыночная цена x количество продукции

📊 ПРИБЫЛЬ ДО НАЛОГА
• Выручка - Себестоимость

💸 НАЛОГ
• Рассчитывается только при положительной прибыли
• Прибыль до налога x ставка налога / 100

✨ ПРИБЫЛЬ ПОСЛЕ НАЛОГА
• Прибыль до налога - Налог

📏 НА 1 ШТУКУ
• Все итоговые показатели делятся на количество продукции

⚙️ ЭФФЕКТИВНОСТЬ
• Влияет на расход материалов и узлов
• Чем ниже эффективность, тем меньше расход
• Формула: расход = базовый расход x (эффективность / 150)
• Округление: при >20 шт -> вверх, при <=20 шт -> математическое (0.5 вверх)"""
