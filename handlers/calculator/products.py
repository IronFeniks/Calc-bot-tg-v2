import logging
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from keyboards.calculator import products_keyboard, multi_select_products_keyboard, back_button, cancel_button, restore_callback_data, clear_user_mapping
from utils.formatters import format_category_path
from excel_handler import get_excel_handler
from .session import get_session

logger = logging.getLogger(__name__)


async def show_products(query, user_id: int, page: int):
    """Показывает список изделий в текущей категории (одиночный режим)"""
    session = get_session(user_id)
    tree = session.get('category_tree', {})
    path = session.get('category_path', [])
    
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


async def select_product_by_number(update_obj, user_id: int, number: int):
    """Выбор изделия по номеру (одиночный режим)"""
    session = get_session(user_id)
    items = session.get('current_products', [])
    
    if number < 1 or number > len(items):
        await send_reply(update_obj, f"❌ Введите число от 1 до {len(items)}", back_button(user_id, "products"))
        return
    
    product_info = items[number - 1]
    await select_product_by_name(update_obj, user_id, product_info['name'])


async def select_product_by_name(update_obj, user_id: int, product_name_or_hash: str):
    """Выбор изделия по названию или хэшу (одиночный режим)"""
    session = get_session(user_id)
    excel = get_excel_handler()
    
    # Пытаемся восстановить оригинальное название из хэша
    original_name = restore_callback_data(user_id, "select_product", product_name_or_hash)
    search_name = original_name.strip()
    
    product = excel.get_product_by_name(search_name)
    
    if not product:
        excel.load_data()
        for _, row in excel.df_nomenclature.iterrows():
            row_name = str(row['Наименование']).strip().lower()
            if row_name == search_name.lower():
                product = row.to_dict()
                break
    
    if not product:
        logger.warning(f"Изделие не найдено: {search_name} (исходный хэш: {product_name_or_hash})")
        await send_reply(update_obj, "❌ Изделие не найдено. Попробуйте выбрать из списка.", back_button(user_id, "products"))
        return
    
    session['selected_product'] = product
    session['step'] = 'quantity'
    
    multiplicity = product.get('Кратность', 1)
    
    await send_reply(
        update_obj,
        f"✅ Выбрано: {product['Наименование']}\n"
        f"📦 Кратность: {multiplicity}\n\n"
        f"📦 Введите количество продукции (шт):\n"
        f"(должно быть кратно {multiplicity})",
        cancel_button(user_id)
    )


async def show_multi_products(query, user_id: int, page: int):
    """Показывает список изделий с чекбоксами (множественный режим)"""
    session = get_session(user_id)
    tree = session.get('category_tree', {})
    path = session.get('category_path', [])
    
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
        await query.message.reply_text(
            text,
            reply_markup=multi_select_products_keyboard(page_items, user_id, page, total_pages, selected)
        )


async def toggle_product(query, user_id: int, product_name_or_hash: str):
    """Переключение выбора изделия (множественный режим)"""
    session = get_session(user_id)
    selected = session.get('selected_products', [])
    
    # Восстанавливаем оригинальное название из хэша
    original_name = restore_callback_data(user_id, "toggle_product", product_name_or_hash)
    product_name = original_name.strip()
    
    if product_name in selected:
        selected.remove(product_name)
        logger.info(f"Удалён из выбора: {product_name}")
    else:
        selected.append(product_name)
        logger.info(f"Добавлен в выбор: {product_name}")
    
    session['selected_products'] = selected
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


async def send_reply(update_obj, text: str, reply_markup=None):
    """
    Универсальная функция отправки ответа
    Поддерживает как Message, так и CallbackQuery
    """
    if isinstance(update_obj, CallbackQuery):
        await update_obj.message.reply_text(text, reply_markup=reply_markup)
    elif hasattr(update_obj, 'message') and update_obj.message:
        await update_obj.message.reply_text(text, reply_markup=reply_markup)
    elif hasattr(update_obj, 'reply_text'):
        await update_obj.reply_text(text, reply_markup=reply_markup)
    else:
        logger.error(f"Не удалось отправить сообщение: неизвестный тип update_obj {type(update_obj)}")
