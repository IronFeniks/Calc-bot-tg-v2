import logging
from telegram import Update
from telegram.ext import ContextTypes
from keyboards.calculator import products_keyboard, multi_select_products_keyboard, back_button, cancel_button
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
    
    try:
        await query.edit_message_text(
            text,
            reply_markup=products_keyboard(page_items, user_id, page, total_pages)
        )
    except Exception as e:
        logger.error(f"Ошибка при показе изделий: {e}")
        await query.edit_message_text(
            "❌ Ошибка при загрузке изделий",
            reply_markup=back_button(user_id, "categories")
        )


async def select_product_by_number(update, user_id: int, number: int):
    """Выбор изделия по номеру (одиночный режим)"""
    session = get_session(user_id)
    items = session.get('current_products', [])
    
    if number < 1 or number > len(items):
        await update.message.reply_text(
            f"❌ Введите число от 1 до {len(items)}",
            reply_markup=back_button(user_id, "products")
        )
        return
    
    product_info = items[number - 1]
    await select_product_by_name(update, user_id, product_info['name'])


async def select_product_by_name(update, user_id: int, product_name: str):
    """Выбор изделия по названию (одиночный режим)"""
    session = get_session(user_id)
    excel = get_excel_handler()
    
    # Нормализуем название для поиска
    search_name = product_name.strip()
    
    # Прямой поиск по названию
    product = excel.get_product_by_name(search_name)
    
    # Если не нашли, пробуем поиск без учёта регистра
    if not product:
        excel.load_data()
        for _, row in excel.df_nomenclature.iterrows():
            row_name = str(row['Наименование']).strip().lower()
            if row_name == search_name.lower():
                product = row.to_dict()
                break
    
    if not product:
        logger.warning(f"Изделие не найдено: {search_name}")
        await update.message.reply_text(
            "❌ Изделие не найдено. Попробуйте выбрать из списка.",
            reply_markup=back_button(user_id, "products")
        )
        return
    
    session['selected_product'] = product
    session['step'] = 'quantity'
    
    multiplicity = product.get('Кратность', 1)
    
    await update.message.reply_text(
        f"✅ Выбрано: {product['Наименование']}\n"
        f"📦 Кратность: {multiplicity}\n\n"
        f"📦 Введите количество продукции (шт):\n"
        f"(должно быть кратно {multiplicity})",
        reply_markup=cancel_button(user_id)
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
        try:
            await query.edit_message_text(
                "❌ В этой категории нет изделий",
                reply_markup=back_button(user_id, "categories")
            )
        except Exception as e:
            logger.error(f"Ошибка при показе сообщения: {e}")
            await query.message.reply_text(
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
    
    try:
        await query.edit_message_text(
            text,
            reply_markup=multi_select_products_keyboard(page_items, user_id, page, total_pages, selected)
        )
    except Exception as e:
        logger.error(f"Ошибка при показе множественного выбора: {e}")
        # Пробуем отправить новое сообщение вместо редактирования
        await query.message.reply_text(
            text,
            reply_markup=multi_select_products_keyboard(page_items, user_id, page, total_pages, selected)
        )


async def toggle_product(query, user_id: int, product_name: str):
    """Переключение выбора изделия (множественный режим)"""
    session = get_session(user_id)
    selected = session.get('selected_products', [])
    
    # Нормализуем название
    product_name = product_name.strip()
    
    if product_name in selected:
        selected.remove(product_name)
        logger.info(f"Удалён из выбора: {product_name}")
    else:
        selected.append(product_name)
        logger.info(f"Добавлен в выбор: {product_name}")
    
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
    
    logger.info(f"Подтверждён выбор: {selected}")
    session['step'] = 'multi_efficiency'
    
    await query.edit_message_text(
        f"✅ Выбрано изделий: {len(selected)}\n\n"
        f"📊 ПАРАМЕТРЫ РАСЧЁТА (1/2)\n\n"
        f"Введите эффективность производства (%):\n"
        f"(общая для всех изделий)\n\n"
        f"Пример: 110",
        reply_markup=cancel_button(user_id)
    )
