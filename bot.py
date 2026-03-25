#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import sys
import os

# ==================== ИМПОРТЫ ДЛЯ ТИПОВ (до автоустановки) ====================
# Эти импорты нужны для аннотаций типов, они не требуют установленных пакетов
from typing import Any

# ==================== АВТОУСТАНОВКА ЗАВИСИМОСТЕЙ ====================
def install_requirements():
    """Автоматически устанавливает зависимости из requirements.txt"""
    try:
        req_file = '/app/requirements.txt'
        if not os.path.exists(req_file):
            print("⚠️ requirements.txt не найден")
            return
        
        print("📦 Проверка и установка зависимостей...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', req_file])
        print("✅ Все зависимости установлены")
    except Exception as e:
        print(f"⚠️ Ошибка установки зависимостей: {e}")

install_requirements()

# ==================== ИМПОРТЫ ПОСЛЕ УСТАНОВКИ ====================
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

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

# ==================== ИМПОРТЫ МОДУЛЕЙ ПРОЕКТА ====================
from config import BOT_TOKEN
from price_db import init_prices_db
from handlers.router import router_handler

# ==================== ГЛОБАЛЬНЫЕ ОБРАБОТЧИКИ ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start — маршрутизирует в зависимости от контекста"""
    await router_handler(update, context, command="start")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /admin — переход в режим администрирования"""
    await router_handler(update, context, command="admin")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /cancel — отмена текущего действия"""
    await router_handler(update, context, command="cancel")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /help — справка"""
    await router_handler(update, context, command="help")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    await router_handler(update, context, command="message")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        # Инициализируем ExcelHandler
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
