import logging
from telegram import Update
from telegram.ext import ContextTypes
from keyboards.calculator import products_keyboard, multi_select_products_keyboard, back_button
from utils.formatters import format_category_path
from excel_handler import get_excel_handler
from .session import get_session

logger = logging.getLogger(__name__)


async def show_products(query, user_id: int, page: int):
    """Показывает список изделий в текущей категории (одиночный режим)"""
    session = get_session(user_id)
    tree = session.get('category_tree', {})
    path = session.get('category_path', [])
    
    # Получаем изделия на текущем уровне
    items = []
    if path:
        current = tree
        for cat in path:
            if cat in current:
                if cat == path[-1]:
                    items = current[cat].get('_items', [])
                    break
                current = current[cat]['_subcategories']
    
    if not items:
        await query.edit_message_text(
            "❌ В этой категории нет изделий",
            reply_markup=back_button(user_id, "categories")
        )
        return
    
    # Сохраняем список изделий в сессию
    session['current_products'] = items
    
    total_pages = (len(items) + 9) // 10
    start = (page - 1) * 10
    end = start + 10
    page_items = items[start:end]
    
    text = "🏗️ ВЫБОР ИЗДЕЛИЯ"
    if path:
        text += f"\n\n📁 {format_category_path(path)}"
    text += f"\n\nСтраница {page} из {total_pages}\n\n"
    
    for i, item in enumerate(page_items, start + 1):
        text += f"{i}. {item['name']}\n"
    text += "\n👉 Введите номер изделия для выбора"
    
    await query.edit_message_text(
        text,
        reply_markup=products_keyboard(page_items, user_id, page, total_pages)
    )


async def select_product_by_name(query, user_id: int, product_name: str):
    """Выбор изделия по названию (одиночный режим)"""
    session = get_session(user_id)
    excel = get_excel_handler()
    
    product = excel.get_product_by_name(product_name)
    if not product:
        await query.edit_message_text("❌ Изделие не найдено")
        return
    
    session['selected_product'] = product
    session['step'] = 'quantity'
    
    multiplicity = product.get('Кратность', 1)
    
    await query.edit_message_text(
        f"✅ Выбрано: {product['Наименование']}\n"
        f"📦 Кратность: {multiplicity}\n\n"
        f"📦 Введите количество продукции (шт):\n"
        f"(должно быть кратно {multiplicity})",
        reply_markup=back_button(user_id, "products")
    )


async def show_multi_products(query, user_id: int, page: int):
    """Показывает список изделий с чекбоксами (множественный режим)"""
    session = get_session(user_id)
    tree = session.get('category_tree', {})
    path = session.get('category_path', [])
    
    # Получаем изделия на текущем уровне
    items = []
    if path:
        current = tree
        for cat in path:
            if cat in current:
                if cat == path[-1]:
                    items = current[cat].get('_items', [])
                    break
                current = current[cat]['_subcategories']
    
    if not items:
        await query.edit_message_text(
            "❌ В этой категории нет изделий",
            reply_markup=back_button(user_id, "categories")
        )
        return
    
    total_pages = (len(items) + 9) // 10
    start = (page - 1) * 10
    end = start + 10
    page_items = items[start:end]
    
    selected = set(session.get('selected_products', []))
    
    text = "📊 ВЫБОР ИЗДЕЛИЙ (множественный режим)"
    if path:
        text += f"\n\n📁 {format_category_path(path)}"
    text += f"\n\nСтраница {page} из {total_pages}\n\n"
    text += "Выберите изделия для расчёта (можно несколько):\n\n"
    
    for i, item in enumerate(page_items, start + 1):
        checkbox = "☑️" if item['name'] in selected else "☐"
        text += f"{checkbox} {i}. {item['name']}\n"
    
    await query.edit_message_text(
        text,
        reply_markup=multi_select_products_keyboard(page_items, user_id, page, total_pages, selected)
    )


async def toggle_product(query, user_id: int, product_name: str):
    """Переключение выбора изделия (множественный режим)"""
    session = get_session(user_id)
    selected = session.get('selected_products', [])
    
    if product_name in selected:
        selected.remove(product_name)
    else:
        selected.append(product_name)
    
    session['selected_products'] = selected
    
    # Обновляем текущую страницу
    await show_multi_products(query, user_id, 1)


async def confirm_products(query, user_id: int):
    """Подтверждение выбора изделий (множественный режим)"""
    session = get_session(user_id)
    selected = session.get('selected_products', [])
    
    if not selected:
        await query.answer("❌ Выберите хотя бы одно изделие", show_alert=True)
        return
    
    session['step'] = 'multi_efficiency'
    
    await query.edit_message_text(
        f"✅ Выбрано изделий: {len(selected)}\n\n"
        f"📊 ПАРАМЕТРЫ РАСЧЁТА (1/2)\n\n"
        f"Введите эффективность производства (%):\n"
        f"(общая для всех изделий)\n\n"
        f"Пример: 110",
        reply_markup=back_button(user_id, "categories")
    )
