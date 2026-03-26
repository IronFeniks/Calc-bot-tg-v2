import logging
from telegram import Update
from telegram.ext import ContextTypes
from keyboards.calculator import categories_keyboard, back_button
from utils.formatters import format_category_path
from .session import get_session

logger = logging.getLogger(__name__)


async def show_categories(query, user_id: int, page: int):
    """Показывает категории на текущем уровне"""
    session = get_session(user_id)
    tree = session.get('category_tree', {})
    path = session.get('category_path', [])
    
    # Получаем текущий уровень
    current = tree
    for cat in path:
        if cat in current:
            current = current[cat]['_subcategories']
        else:
            current = {}
    
    categories = list(current.keys())
    
    if not categories:
        # Если нет подкатегорий, переходим к выбору изделий
        from .products import show_products, show_multi_products
        if session['mode'] == 'single':
            await show_products(query, user_id, 1)
        else:
            await show_multi_products(query, user_id, 1)
        return
    
    total_pages = (len(categories) + 9) // 10
    start = (page - 1) * 10
    end = start + 10
    page_categories = categories[start:end]
    
    text = "📂 ВЫБОР КАТЕГОРИИ"
    if path:
        text += f"\n\n📁 {format_category_path(path)}"
    
    await query.edit_message_text(
        text,
        reply_markup=categories_keyboard(page_categories, user_id, page, total_pages)
    )


async def select_category(query, user_id: int, category: str):
    """Выбор категории"""
    session = get_session(user_id)
    tree = session.get('category_tree', {})
    path = session.get('category_path', [])
    
    # Добавляем категорию в путь
    path.append(category)
    session['category_path'] = path
    
    # Получаем подкатегории
    current = tree
    for cat in path:
        if cat in current:
            current = current[cat]['_subcategories']
        else:
            current = {}
    
    if current:
        # Есть подкатегории — показываем их
        categories = list(current.keys())
        total_pages = (len(categories) + 9) // 10
        page_categories = categories[:10]
        
        await query.edit_message_text(
            f"📂 ВЫБОР КАТЕГОРИИ\n\n📁 {format_category_path(path)}",
            reply_markup=categories_keyboard(page_categories, user_id, 1, total_pages)
        )
    else:
        # Нет подкатегорий — переходим к выбору изделий
        from .products import show_products, show_multi_products
        if session['mode'] == 'single':
            await show_products(query, user_id, 1)
        else:
            await show_multi_products(query, user_id, 1)


async def back_to_categories(query, user_id: int):
    """Возврат на уровень выше"""
    session = get_session(user_id)
    path = session.get('category_path', [])
    
    if path:
        path.pop()
        session['category_path'] = path
    
    await show_categories(query, user_id, 1)
