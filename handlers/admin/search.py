import logging
from telegram import CallbackQuery
from keyboards.admin import search_results_keyboard, back_to_main_button
from excel_handler import get_excel_handler

logger = logging.getLogger(__name__)


async def search_start(query: CallbackQuery, user_id: int):
    """Запрашивает поисковый запрос"""
    from .router import get_admin_session
    from states import AdminStates
    
    session = get_admin_session(user_id)
    session['state'] = AdminStates.SEARCH_QUERY
    
    await query.edit_message_text(
        "🔍 ПОИСК\n\n"
        "Введите название или код для поиска:\n"
        "(или нажмите Отмена)",
        reply_markup=back_to_main_button(user_id)
    )


async def search_execute(update, user_id: int, query_text: str):
    """Выполняет поиск и показывает результаты"""
    from .router import get_admin_session
    from keyboards.admin import main_menu_keyboard
    
    excel = get_excel_handler()
    results = excel.search_items(query_text)
    
    session = get_admin_session(user_id)
    session['data'] = {'search_results': results, 'query': query_text}
    
    if not results:
        await update.message.reply_text(
            f"🔍 ПОИСК: '{query_text}'\n\n"
            f"❌ Ничего не найдено.\n\n"
            f"Что делаем дальше?",
            reply_markup=main_menu_keyboard(user_id)
        )
        return
    
    await show_search_results(update, user_id, page=0)


async def show_search_results(update_obj, user_id: int, page: int = 0, highlight: str = None):
    """Показывает результаты поиска с пагинацией"""
    from .router import get_admin_session
    
    session = get_admin_session(user_id)
    results = session.get('data', {}).get('search_results', [])
    query_text = session.get('data', {}).get('query', '')
    
    if not results:
        if isinstance(update_obj, CallbackQuery):
            await update_obj.answer("❌ Нет результатов", show_alert=True)
        return
    
    items_per_page = 5
    total_pages = (len(results) + items_per_page - 1) // items_per_page
    start = page * items_per_page
    end = min(start + items_per_page, len(results))
    page_items = results[start:end]
    
    text = f"🔍 РЕЗУЛЬТАТЫ ПОИСКА: '{query_text}'\n\n"
    text += f"Найдено: {len(results)}\n"
    text += f"Страница {page + 1} из {total_pages}\n\n"
    
    for item in page_items:
        icon = "🏗️" if item['type'] == 'изделие' else ("🔩" if item['type'] == 'узел' else "🧱")
        text += f"{icon} {item['name']}\n"
        text += f"   Код: {item['code']}\n"
        text += f"   Тип: {item['type']}\n"
        text += f"   Категория: {item['category'] or '—'}\n"
        text += f"   Цена: {item['price']}\n"
        if item.get('multiplicity', 1) > 1:
            text += f"   Кратность: {item['multiplicity']}\n"
        text += "\n"
    
    keyboard = search_results_keyboard(user_id, page_items, page, total_pages)
    
    if isinstance(update_obj, CallbackQuery):
        await update_obj.edit_message_text(text, reply_markup=keyboard)
    else:
        await update_obj.message.reply_text(text, reply_markup=keyboard)
