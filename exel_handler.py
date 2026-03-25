import pandas as pd
import os
import logging

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
    
    def load_data(self) -> tuple:
        """Загружает данные из Excel файла"""
        try:
            if not os.path.exists(self.file_path):
                logger.warning(f"Файл не найден: {self.file_path}")
                return False, f"❌ Файл не найден: {self.file_path}"
            
            excel_file = pd.ExcelFile(self.file_path)
            
            if 'Номенклатура' in excel_file.sheet_names:
                self.df_nomenclature = pd.read_excel(excel_file, sheet_name='Номенклатура').fillna('')
            else:
                return False, "❌ В файле нет листа 'Номенклатура'"
            
            if 'Спецификации' in excel_file.sheet_names:
                self.df_specifications = pd.read_excel(excel_file, sheet_name='Спецификации').fillna('')
            else:
                return False, "❌ В файле нет листа 'Спецификации'"
            
            # Загружаем или создаём лист Счётчики
            self._load_or_create_counters(excel_file)
            
            # Загружаем или создаём лист Администраторы
            self._load_or_create_admins(excel_file)
            
            logger.info(f"✅ Загружено: {len(self.df_nomenclature)} записей номенклатуры, {len(self.df_specifications)} спецификаций")
            return True, "✅ Данные загружены"
            
        except Exception as e:
            logger.error(f"Ошибка загрузки Excel: {e}")
            return False, f"❌ Ошибка загрузки: {e}"
    
    def _load_or_create_counters(self, excel_file):
        """Загружает или создаёт лист счётчиков"""
        # TODO: реализация
        pass
    
    def _load_or_create_admins(self, excel_file):
        """Загружает или создаёт лист администраторов"""
        # TODO: реализация
        pass
    
    def save_data(self) -> tuple:
        """Сохраняет данные в Excel файл"""
        # TODO: реализация
        return True, "✅ Данные сохранены"
