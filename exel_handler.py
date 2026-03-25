import pandas as pd
import os
import logging
from typing import Tuple, List, Dict, Optional

logger = logging.getLogger(__name__)

_excel_handler = None

def set_excel_handler(handler):
    global _excel_handler
    _excel_handler = handler

def get_excel_handler():
    return _excel_handler

class ExcelHandler:
    def __init__(self):
        self.file_path = "/app/data/База для приложения.xlsx"
        self.df_nomenclature = None
        self.df_specifications = None
        self.df_counters = None
        self.df_admins = None
        self.load_data()
    
    def load_data(self) -> Tuple[bool, str]:
        """Загружает данные из Excel файла"""
        try:
            if not os.path.exists(self.file_path):
                logger.warning(f"Файл не найден: {self.file_path}")
                return False, f"❌ Файл не найден: {self.file_path}"
            
            excel_file = pd.ExcelFile(self.file_path)
            
            # Загружаем Номенклатуру
            if 'Номенклатура' in excel_file.sheet_names:
                self.df_nomenclature = pd.read_excel(excel_file, sheet_name='Номенклатура').fillna('')
                logger.info(f"✅ Загружено {len(self.df_nomenclature)} записей номенклатуры")
            else:
                return False, "❌ В файле нет листа 'Номенклатура'"
            
            # Загружаем Спецификации
            if 'Спецификации' in excel_file.sheet_names:
                self.df_specifications = pd.read_excel(excel_file, sheet_name='Спецификации').fillna('')
                logger.info(f"✅ Загружено {len(self.df_specifications)} спецификаций")
            else:
                return False, "❌ В файле нет листа 'Спецификации'"
            
            # Загружаем или создаём Счётчики
            self._load_or_create_counters(excel_file)
            
            # Загружаем или создаём Администраторы
            self._load_or_create_admins(excel_file)
            
            return True, "✅ Данные загружены"
            
        except Exception as e:
            logger.error(f"Ошибка загрузки Excel: {e}")
            return False, f"❌ Ошибка загрузки: {e}"
    
    def _load_or_create_counters(self, excel_file):
        """Загружает или создаёт лист счётчиков"""
        try:
            if 'Счётчики' in excel_file.sheet_names:
                self.df_counters = pd.read_excel(excel_file, sheet_name='Счётчики').fillna('')
                logger.info("✅ Лист 'Счётчики' загружен")
            else:
                # Создаём новый лист
                self.df_counters = pd.DataFrame({
                    'Тип': ['изделие', 'узел', 'материал'],
                    'Максимальный номер': [0, 0, 0]
                })
                logger.info("✅ Создан новый лист 'Счётчики'")
        except Exception as e:
            logger.error(f"Ошибка загрузки счётчиков: {e}")
            self.df_counters = pd.DataFrame({
                'Тип': ['изделие', 'узел', 'материал'],
                'Максимальный номер': [0, 0, 0]
            })
    
    def _load_or_create_admins(self, excel_file):
        """Загружает или создаёт лист администраторов"""
        from config import MASTER_ADMIN_ID
        
        try:
            if 'Администраторы' in excel_file.sheet_names:
                self.df_admins = pd.read_excel(excel_file, sheet_name='Администраторы').fillna('')
                logger.info("✅ Лист 'Администраторы' загружен")
            else:
                # Создаём новый лист с главным админом
                import datetime
                self.df_admins = pd.DataFrame([{
                    'user_id': MASTER_ADMIN_ID,
                    'username': '',
                    'first_name': '',
                    'added_by': MASTER_ADMIN_ID,
                    'added_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'is_active': 1
                }])
                logger.info("✅ Создан новый лист 'Администраторы' с главным админом")
        except Exception as e:
            logger.error(f"Ошибка загрузки администраторов: {e}")
            import datetime
            self.df_admins = pd.DataFrame([{
                'user_id': MASTER_ADMIN_ID,
                'username': '',
                'first_name': '',
                'added_by': MASTER_ADMIN_ID,
                'added_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'is_active': 1
            }])
    
    def save_data(self) -> Tuple[bool, str]:
        """Сохраняет данные в Excel файл"""
        try:
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                self.df_nomenclature.to_excel(writer, sheet_name='Номенклатура', index=False)
                self.df_specifications.to_excel(writer, sheet_name='Спецификации', index=False)
                self.df_counters.to_excel(writer, sheet_name='Счётчики', index=False)
                self.df_admins.to_excel(writer, sheet_name='Администраторы', index=False)
            
            logger.info("✅ Данные сохранены в Excel")
            return True, "✅ Данные сохранены"
            
        except Exception as e:
            logger.error(f"Ошибка сохранения Excel: {e}")
            return False, f"❌ Ошибка сохранения: {e}"
    
    def is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        from config import MASTER_ADMIN_ID
        
        if user_id == MASTER_ADMIN_ID:
            return True
        
        if self.df_admins is not None:
            admins = self.df_admins[self.df_admins['user_id'] == user_id]
            return len(admins) > 0 and admins.iloc[0].get('is_active', 1) == 1
        return False
    
    def get_category_tree(self) -> dict:
        """Строит дерево категорий из номенклатуры"""
        tree = {}
        # TODO: полная реализация позже
        return tree
    
    def get_products_in_category(self, category_path: list) -> list:
        """Получает изделия в категории"""
        # TODO: полная реализация позже
        return []
