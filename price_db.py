import sqlite3
import os
import logging
from config import PRICES_DB

logger = logging.getLogger(__name__)

def init_prices_db():
    """Создаёт таблицы для хранения цен, если их нет"""
    os.makedirs(os.path.dirname(PRICES_DB), exist_ok=True)
    conn = sqlite3.connect(PRICES_DB)
    cursor = conn.cursor()
    
    # Таблица для цен материалов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS material_prices (
            material_name TEXT PRIMARY KEY,
            price REAL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица для цен чертежей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drawing_prices (
            product_code TEXT PRIMARY KEY,
            price REAL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ База данных цен инициализирована")

def save_material_price(material_name: str, price: float):
    """Сохраняет цену материала"""
    try:
        conn = sqlite3.connect(PRICES_DB)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO material_prices (material_name, price, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (material_name, price))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка сохранения цены материала: {e}")

def get_material_price(material_name: str) -> float:
    """Получает цену материала"""
    try:
        conn = sqlite3.connect(PRICES_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT price FROM material_prices WHERE material_name = ?", (material_name,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception as e:
        logger.error(f"Ошибка получения цены материала: {e}")
        return 0

def get_all_material_prices() -> dict:
    """Получает все цены материалов"""
    try:
        conn = sqlite3.connect(PRICES_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT material_name, price FROM material_prices")
        rows = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in rows}
    except Exception as e:
        logger.error(f"Ошибка получения цен: {e}")
        return {}

def save_drawing_price(product_code: str, price: float):
    """Сохраняет цену чертежа"""
    try:
        conn = sqlite3.connect(PRICES_DB)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO drawing_prices (product_code, price, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (product_code, price))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка сохранения цены чертежа: {e}")

def get_drawing_price(product_code: str) -> float:
    """Получает цену чертежа"""
    try:
        conn = sqlite3.connect(PRICES_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT price FROM drawing_prices WHERE product_code = ?", (product_code,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception as e:
        logger.error(f"Ошибка получения цены чертежа: {e}")
        return 0
