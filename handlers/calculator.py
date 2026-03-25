import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def start_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE, is_topic: bool, lock=None):
    """Запуск калькулятора"""
    user_id = update.effective_user.id
    
    # Проверка блокировки для топика
    if is_topic and lock and lock.is_locked() and lock.current_user != user_id:
        lock_info = lock.get_lock_info()
        name = lock_info['first_name'] or f"@{lock_info['username']}" if lock_info['username'] else f"ID {lock_info['user_id']}"
        await update.message.reply_text(
            f"⏳ *Бот занят*\n\nСейчас расчёты выполняет: *{name}*",
            parse_mode='Markdown'
        )
        return
    
    # Захват блокировки для топика
    if is_topic and lock:
        if not lock.acquire(user_id, update.effective_user.username, update.effective_user.first_name):
            await update.message.reply_text("❌ Не удалось начать расчёт. Попробуйте позже.")
            return
    
    # Определяем, какую инструкцию показывать
    if is_topic:
        instruction = """🏭 ПРОИЗВОДСТВЕННЫЙ КАЛЬКУЛЯТОР

📍 РЕЖИМ: ТОПИК

📌 ОСОБЕННОСТИ:
• Одновременно может работать только один пользователь
• Если бот занят, вы увидите имя текущего пользователя
• Таймаут сессии: 5 минут бездействия
• Бот отвечает только в этом топике

💾 СОХРАНЕНИЕ ЦЕН:
• Цены материалов и узлов сохраняются автоматически
• При повторном расчёте подставляются сохранённые цены

📋 РЕЖИМЫ РАСЧЁТА:
1. Одиночный — расчёт одного изделия или узла
2. Множественный — расчёт нескольких изделий/узлов с суммированием материалов

📖 КАК РАБОТАТЬ:
1. Введите /start
2. Выберите режим расчёта
3. Следуйте инструкциям бота
4. Все цены вводятся только числом, без ISK

👤 ПЕРЕХОД В ЛИЧНЫЙ РЕЖИМ:
• Если хотите использовать калькулятор без блокировки, перейдите в личную переписку с ботом
• В личке нет ограничений, цены сохраняются лично для вас

❗ ВАЖНО:
• Для отмены текущего расчёта нажмите ❌ Отмена
• Для нового расчёта используйте /start"""
    else:
        # Проверяем, админ ли пользователь (для отображения доп. информации)
        from handlers.router import is_admin
        if is_admin(user_id):
            instruction = """🏭 ПРОИЗВОДСТВЕННЫЙ КАЛЬКУЛЯТОР

📍 РЕЖИМ: АДМИНИСТРАТОР (калькулятор)

📌 ОСОБЕННОСТИ:
• Вы вошли как администратор
• Режим калькулятора — без ограничений
• Для перехода в админку используйте /admin

💾 СОХРАНЕНИЕ ЦЕН:
• Цены материалов и узлов сохраняются автоматически
• При повторном расчёте подставляются сохранённые цены

📋 РЕЖИМЫ РАСЧЁТА:
1. Одиночный — расчёт одного изделия или узла
2. Множественный — расчёт нескольких изделий/узлов с суммированием материалов

🔄 ПЕРЕКЛЮЧЕНИЕ РЕЖИМОВ:
• /admin — перейти в режим администрирования
• /start — вернуться в режим калькулятора

❗ ВАЖНО:
• Для отмены текущего расчёта нажмите ❌ Отмена или введите /cancel
• Для нового расчёта используйте /start"""
        else:
            instruction = """🏭 ПРОИЗВОДСТВЕННЫЙ КАЛЬКУЛЯТОР

📍 РЕЖИМ: ЛИЧНАЯ ПЕРЕПИСКА

📌 ОСОБЕННОСТИ:
• Нет ограничений на количество пользователей
• Сессия не имеет таймаута
• Вы можете пользоваться калькулятором в любое время

💾 СОХРАНЕНИЕ ЦЕН:
• Цены материалов и узлов сохраняются автоматически
• При повторном расчёте подставляются сохранённые цены
• Цены сохраняются лично для вас

📋 РЕЖИМЫ РАСЧЁТА:
1. Одиночный — расчёт одного изделия или узла
2. Множественный — расчёт нескольких изделий/узлов с суммированием материалов

📖 КАК РАБОТАТЬ:
1. Введите /start
2. Выберите режим расчёта
3. Следуйте инструкциям бота
4. Все цены вводятся только числом, без ISK

❗ ВАЖНО:
• Для отмены текущего расчёта нажмите ❌ Отмена или введите /cancel
• Для нового расчёта используйте /start"""
    
    # Показываем меню выбора режима
    from keyboards.calculator import mode_selection_keyboard
    
    await update.message.reply_text(
        instruction,
        reply_markup=mode_selection_keyboard(user_id),
        parse_mode='Markdown'
    )


async def calculator_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, is_topic: bool, lock=None):
    """Обработчик текстовых сообщений в калькуляторе"""
    # TODO: полная реализация
    await update.message.reply_text("📝 Калькулятор в разработке. Используйте кнопки меню.")


async def calculator_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, is_topic: bool, lock=None):
    """Обработчик callback кнопок в калькуляторе"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Проверка, что callback для этого пользователя
    if not data.startswith(f"user_{user_id}_") and data != "noop":
        await query.answer("⛔ Эта кнопка не для вас", show_alert=True)
        return
    
    # Обновляем время блокировки для топика
    if is_topic and lock and lock.current_user == user_id:
        lock.refresh(user_id)
    
    # Обработка режимов
    if data.endswith("single_mode") or "single_mode" in data:
        # TODO: переход в одиночный режим
        await query.edit_message_text("🧮 Одиночный расчёт (в разработке)")
    elif data.endswith("multi_mode") or "multi_mode" in data:
        # TODO: переход в множественный режим
        await query.edit_message_text("📊 Множественный расчёт (в разработке)")
    elif data.endswith("cancel") or "cancel" in data:
        await cancel_calculator(update, context, is_topic, lock)
    else:
        await query.edit_message_text("🔧 Функция в разработке")


async def cancel_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE, is_topic: bool, lock=None):
    """Отмена текущего расчёта"""
    user_id = update.effective_user.id
    
    if is_topic and lock and lock.current_user == user_id:
        lock.release()
    
    if update.callback_query:
        await update.callback_query.edit_message_text("❌ Расчет отменен")
    else:
        await update.message.reply_text("❌ Расчет отменен")


async def help_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE, is_topic: bool):
    """Справка по калькулятору"""
    help_text = """📖 ПОМОЩЬ ПО КАЛЬКУЛЯТОРУ

📋 РЕЖИМЫ РАСЧЁТА:
• Одиночный — выбор одного изделия, пошаговый ввод
• Множественный — выбор нескольких изделий, суммирование материалов

💾 СОХРАНЕНИЕ ЦЕН:
• Цены вводятся один раз и сохраняются
• При повторном расчёте подставляются автоматически

📊 ФОРМУЛЫ:
• Эффективность влияет на расход материалов
• Чем ниже эффективность, тем меньше расход материалов
• Налог рассчитывается только при положительной прибыли

🔧 КОМАНДЫ:
/start — начать новый расчёт
/cancel — отменить текущее действие
/help — эта справка

❓ Вопросы: обратитесь к администратору @arseniy_echo"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(help_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(help_text, parse_mode='Markdown')
