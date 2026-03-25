#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
import os

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from config import BOT_TOKEN, GROUP_ID, TOPIC_ID
from price_db import init_prices_db
from handlers.router import router_handler
from handlers.calculator import start_calculator, cancel_calculator, help_calculator
from handlers.admin import start_admin, cancel_admin, help_admin
from keyboards.admin import main_menu_keyboard

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', mode='a', encoding='utf-8')
    ]
)

logging.getLogger('httpx').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info("🚀 Запуск объединённого бота...")

# ==================== ГЛОБАЛЬНЫЕ ОБРАБОТЧИКИ ====================

async def start_command(update, context):
    """Обработчик /start — маршрутизирует в зависимости от контекста"""
    await router_handler(update, context, command="start")

async def admin_command(update, context):
    """Обработчик /admin — переход в режим администрирования"""
    await router_handler(update, context, command="admin")

async def cancel_command(update, context):
    """Обработчик /cancel — отмена текущего действия"""
    await router_handler(update, context, command="cancel")

async def help_command(update, context):
    """Обработчик /help — справка"""
    await router_handler(update, context, command="help")

async def message_handler(update, context):
    """Обработчик текстовых сообщений"""
    await router_handler(update, context, command="message")

async def callback_handler(update, context):
    """Обработчик callback кнопок"""
    await router_handler(update, context, command="callback")

# ==================== POST_INIT ====================

async def post_init(application: Application):
    """Действия после инициализации бота"""
    logger.info("⚙️ Выполняется post_init...")
    
    try:
        # Инициализируем SQLite
        init_prices_db()
        logger.info("✅ SQLite инициализирован")
        
        # Инициализируем ExcelHandler (будет создан позже)
        from excel_handler import ExcelHandler, set_excel_handler
        excel_handler = ExcelHandler()
        set_excel_handler(excel_handler)
        logger.info("✅ ExcelHandler инициализирован")
        
        # Устанавливаем команды бота
        await application.bot.set_my_commands([
            ("start", "🏠 Главное меню / Калькулятор"),
            ("admin", "⚙️ Режим администрирования"),
            ("cancel", "❌ Отмена текущего действия"),
            ("help", "📖 Помощь")
        ])
        logger.info("✅ Команды бота установлены")
        
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка в post_init: {e}")

# ==================== MAIN ====================

def main():
    logger.info("=" * 50)
    logger.info("⚙️ ЗАПУСК MAIN ФУНКЦИИ")
    logger.info("=" * 50)
    
    try:
        if not BOT_TOKEN:
            logger.critical("❌ BOT_TOKEN не найден!")
            return
        
        logger.info("🔄 Создание приложения...")
        application = Application.builder() \
            .token(BOT_TOKEN) \
            .post_init(post_init) \
            .build()
        logger.info("✅ Приложение создано")
        
        logger.info("🔄 Добавление обработчиков...")
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("admin", admin_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(callback_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        logger.info("✅ Все обработчики добавлены")
        
        logger.info("🔄 Запуск polling...")
        application.run_polling(allowed_updates=['message', 'callback_query'])
        
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка в main: {e}")
        raise

if __name__ == '__main__':
    main()
