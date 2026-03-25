import logging
from telegram import Update
from telegram.ext import ContextTypes

from config import GROUP_ID, TOPIC_ID, ADMIN_IDS, MASTER_ADMIN_ID
from user_lock import UserLock
from handlers.calculator import start_calculator, calculator_text_handler, calculator_callback_handler, cancel_calculator, help_calculator
from handlers.admin import start_admin, admin_text_handler, admin_callback_handler, cancel_admin, help_admin
from keyboards.admin import mode_selection_keyboard

logger = logging.getLogger(__name__)

# Глобальная блокировка для топика
topic_lock = UserLock(timeout_seconds=300)

# Словарь для хранения режимов пользователей в личке
# user_id -> 'calculator' or 'admin'
user_modes = {}

def get_user_mode(user_id: int) -> str:
    """Получить текущий режим пользователя в личке"""
    return user_modes.get(user_id, 'calculator')

def set_user_mode(user_id: int, mode: str):
    """Установить режим пользователя в личке"""
    user_modes[user_id] = mode

def clear_user_mode(user_id: int):
    """Очистить режим пользователя"""
    if user_id in user_modes:
        del user_modes[user_id]

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    if user_id == MASTER_ADMIN_ID:
        return True
    # TODO: проверить в Excel (будет реализовано позже)
    return user_id in ADMIN_IDS

async def router_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
    """Главный маршрутизатор"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    is_topic = False
    
    # Определяем, где находится сообщение
if chat_id == GROUP_ID:
    # Сообщение в группе
    if update.message:
        topic_id = update.message.message_thread_id
        logger.info(f"🔍 Сообщение в группе: message_thread_id={topic_id}")
    elif update.callback_query:
        topic_id = update.callback_query.message.message_thread_id
        logger.info(f"🔍 Callback в группе: message_thread_id={topic_id}")
    else:
        topic_id = None
    
    # Проверяем, что сообщение в нужном топике
    if topic_id == TOPIC_ID:
        is_topic = True
        logger.info(f"✅ Сообщение в нашем топике (topic={topic_id})")
    else:
        logger.info(f"⏭️ Сообщение не в нашем топике (topic={topic_id}), ожидается {TOPIC_ID}")
        return
    
    # ==================== ТОПИК ====================
    if is_topic:
        # Топик — только калькулятор с блокировкой
        if command == "start":
            await start_calculator(update, context, is_topic=True, lock=topic_lock)
        elif command == "cancel":
            await cancel_calculator(update, context, is_topic=True, lock=topic_lock)
        elif command == "help":
            await help_calculator(update, context, is_topic=True)
        elif command == "message":
            await calculator_text_handler(update, context, is_topic=True, lock=topic_lock)
        elif command == "callback":
            await calculator_callback_handler(update, context, is_topic=True, lock=topic_lock)
        return
    
    # ==================== ЛИЧКА ====================
    # Личная переписка
    user_is_admin = is_admin(user_id)
    
    # Если команда /admin и пользователь админ — переключаем в админку
    if command == "admin" and user_is_admin:
        set_user_mode(user_id, 'admin')
        await start_admin(update, context)
        return
    
    # Если команда /start — показываем меню выбора режима (только для админов)
    if command == "start":
        if user_is_admin:
            # Админ — показываем меню выбора
            await update.message.reply_text(
                "🏭 ВЫБОР РЕЖИМА\n\n"
                "Вы вошли как администратор. Выберите режим работы:",
                reply_markup=mode_selection_keyboard(user_id)
            )
        else:
            # Обычный пользователь — сразу калькулятор
            set_user_mode(user_id, 'calculator')
            await start_calculator(update, context, is_topic=False, lock=None)
        return
    
    # Определяем текущий режим пользователя
    mode = get_user_mode(user_id)
    
    # Если режим не установлен и пользователь админ — показываем меню выбора
    if not mode and user_is_admin:
        await update.message.reply_text(
            "🏭 ВЫБОР РЕЖИМА\n\n"
            "Вы вошли как администратор. Выберите режим работы:",
            reply_markup=mode_selection_keyboard(user_id)
        )
        return
    
    # Если режим не установлен и пользователь не админ — включаем калькулятор
    if not mode:
        set_user_mode(user_id, 'calculator')
        mode = 'calculator'
    
    # Маршрутизация по режиму
    if mode == 'calculator':
        if command == "cancel":
            await cancel_calculator(update, context, is_topic=False, lock=None)
        elif command == "help":
            await help_calculator(update, context, is_topic=False)
        elif command == "message":
            await calculator_text_handler(update, context, is_topic=False, lock=None)
        elif command == "callback":
            await calculator_callback_handler(update, context, is_topic=False, lock=None)
    elif mode == 'admin':
        if command == "cancel":
            await cancel_admin(update, context)
        elif command == "help":
            await help_admin(update, context)
        elif command == "message":
            await admin_text_handler(update, context)
        elif command == "callback":
            await admin_callback_handler(update, context)
