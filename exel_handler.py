import pandas as pd
import os
import logging
from typing import Tuple, List, Dict, Optional, Any
from datetime import datetime

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
    
    # ==================== ЗАГРУЗКА И СОХРАНЕНИЕ ====================
    
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
    
    def save_data(self) -> Tuple[bool, str]:
        """Сохраняет данные в Excel файл"""
        try:
            # Создаём временный файл для безопасного сохранения
            temp_file = self.file_path + ".tmp"
            
            with pd.ExcelWriter(temp_file, engine='openpyxl') as writer:
                if self.df_nomenclature is not None:
                    self.df_nomenclature.to_excel(writer, sheet_name='Номенклатура', index=False)
                if self.df_specifications is not None:
                    self.df_specifications.to_excel(writer, sheet_name='Спецификации', index=False)
                if self.df_counters is not None:
                    self.df_counters.to_excel(writer, sheet_name='Счётчики', index=False)
                if self.df_admins is not None:
                    self.df_admins.to_excel(writer, sheet_name='Администраторы', index=False)
            
            # Заменяем оригинал
            if os.path.exists(temp_file):
                if os.path.exists(self.file_path):
                    os.remove(self.file_path)
                os.rename(temp_file, self.file_path)
            
            logger.info("✅ Данные сохранены в Excel")
            return True, "✅ Данные сохранены"
            
        except Exception as e:
            logger.error(f"Ошибка сохранения Excel: {e}")
            return False, f"❌ Ошибка сохранения: {e}"
    
    # ==================== СЧЁТЧИКИ ====================
    
    def _load_or_create_counters(self, excel_file):
        """Загружает или создаёт лист счётчиков"""
        try:
            if 'Счётчики' in excel_file.sheet_names:
                self.df_counters = pd.read_excel(excel_file, sheet_name='Счётчики').fillna('')
                logger.info("✅ Лист 'Счётчики' загружен")
            else:
                # Создаём новый лист, сканируем существующие данные
                counters = self._scan_max_numbers()
                self.df_counters = pd.DataFrame([
                    {'Тип': 'изделие', 'Максимальный номер': counters['изделие']},
                    {'Тип': 'узел', 'Максимальный номер': counters['узел']},
                    {'Тип': 'материал', 'Максимальный номер': counters['материал']}
                ])
                logger.info(f"✅ Создан лист 'Счётчики' с номерами: {counters}")
        except Exception as e:
            logger.error(f"Ошибка загрузки счётчиков: {e}")
            self.df_counters = pd.DataFrame([
                {'Тип': 'изделие', 'Максимальный номер': 0},
                {'Тип': 'узел', 'Максимальный номер': 0},
                {'Тип': 'материал', 'Максимальный номер': 0}
            ])
    
    def _scan_max_numbers(self) -> Dict[str, int]:
        """Сканирует существующую номенклатуру для определения максимальных номеров"""
        counters = {'изделие': 0, 'узел': 0, 'материал': 0}
        
        if self.df_nomenclature is None:
            return counters
        
        for _, row in self.df_nomenclature.iterrows():
            code = str(row['Код'])
            type_name = str(row['Тип']).lower()
            
            if type_name == 'изделие' and code.startswith('изд.'):
                try:
                    num = int(code.replace('изд.', '').strip())
                    if num > counters['изделие']:
                        counters['изделие'] = num
                except:
                    pass
            elif type_name == 'узел' and code.startswith('узел'):
                try:
                    num = int(code.replace('узел', '').strip())
                    if num > counters['узел']:
                        counters['узел'] = num
                except:
                    pass
            elif type_name == 'материал' and code.startswith('мат'):
                try:
                    num = int(code.replace('мат', '').strip())
                    if num > counters['материал']:
                        counters['материал'] = num
                except:
                    pass
        
        return counters
    
    def _get_counter(self, type_name: str) -> int:
        """Получает текущий счётчик для типа"""
        if self.df_counters is None:
            return 0
        mask = self.df_counters['Тип'] == type_name
        if mask.any():
            return int(self.df_counters.loc[mask, 'Максимальный номер'].iloc[0])
        return 0
    
    def _update_counter(self, type_name: str, new_value: int):
        """Обновляет счётчик"""
        if self.df_counters is None:
            return
        mask = self.df_counters['Тип'] == type_name
        if mask.any():
            self.df_counters.loc[mask, 'Максимальный номер'] = new_value
    
    def _generate_code(self, prefix: str, type_name: str) -> str:
        """Генерирует следующий код"""
        current = self._get_counter(type_name)
        next_num = current + 1
        self._update_counter(type_name, next_num)
        
        if next_num > 999:
            return f"{prefix} {next_num}"
        else:
            return f"{prefix} {next_num:03d}"
    
    def get_next_product_code(self) -> str:
        """Генерирует следующий код для изделия"""
        return self._generate_code('изд.', 'изделие')
    
    def get_next_node_code(self) -> str:
        """Генерирует следующий код для узла"""
        return self._generate_code('узел', 'узел')
    
    def get_next_material_code(self) -> str:
        """Генерирует следующий код для материала"""
        return self._generate_code('мат', 'материал')
    
    # ==================== АДМИНИСТРАТОРЫ ====================
    
    def _load_or_create_admins(self, excel_file):
        """Загружает или создаёт лист администраторов"""
        from config import MASTER_ADMIN_ID
        
        try:
            if 'Администраторы' in excel_file.sheet_names:
                self.df_admins = pd.read_excel(excel_file, sheet_name='Администраторы').fillna('')
                logger.info("✅ Лист 'Администраторы' загружен")
            else:
                # Создаём новый лист с главным админом
                self.df_admins = pd.DataFrame([{
                    'user_id': MASTER_ADMIN_ID,
                    'username': '',
                    'first_name': '',
                    'added_by': MASTER_ADMIN_ID,
                    'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'is_active': 1
                }])
                logger.info("✅ Создан лист 'Администраторы' с главным админом")
        except Exception as e:
            logger.error(f"Ошибка загрузки администраторов: {e}")
            from config import MASTER_ADMIN_ID
            self.df_admins = pd.DataFrame([{
                'user_id': MASTER_ADMIN_ID,
                'username': '',
                'first_name': '',
                'added_by': MASTER_ADMIN_ID,
                'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'is_active': 1
            }])
    
    def is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        from config import MASTER_ADMIN_ID
        
        if user_id == MASTER_ADMIN_ID:
            return True
        
        if self.df_admins is not None:
            admins = self.df_admins[
                (self.df_admins['user_id'] == user_id) & 
                (self.df_admins['is_active'] == 1)
            ]
            return len(admins) > 0
        return False
    
    def add_admin(self, user_id: int, username: str = '', first_name: str = '', added_by: int = 0) -> Tuple[bool, str]:
        """Добавляет нового администратора"""
        if self.is_admin(user_id):
            return False, "❌ Пользователь уже является администратором"
        
        new_row = pd.DataFrame([{
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'added_by': added_by,
            'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_active': 1
        }])
        
        self.df_admins = pd.concat([self.df_admins, new_row], ignore_index=True)
        return True, f"✅ Администратор {first_name or username or user_id} добавлен"
    
    def remove_admin(self, user_id: int) -> Tuple[bool, str]:
        """Удаляет администратора (мягкое удаление)"""
        from config import MASTER_ADMIN_ID
        
        if user_id == MASTER_ADMIN_ID:
            return False, "❌ Нельзя удалить главного администратора"
        
        mask = self.df_admins['user_id'] == user_id
        if mask.any():
            self.df_admins.loc[mask, 'is_active'] = 0
            return True, "✅ Администратор удалён"
        return False, "❌ Пользователь не найден в списке администраторов"
    
    def get_admins_list(self) -> List[Dict]:
        """Возвращает список активных администраторов"""
        if self.df_admins is None:
            return []
        
        admins = self.df_admins[self.df_admins['is_active'] == 1]
        result = []
        for _, row in admins.iterrows():
            result.append({
                'user_id': int(row['user_id']),
                'username': str(row['username']),
                'first_name': str(row['first_name']),
                'added_at': str(row['added_at'])
            })
        return result
    
    # ==================== НОМЕНКЛАТУРА ====================
    
    def get_product_by_code(self, code: str) -> Optional[Dict]:
        """Возвращает запись по коду"""
        if self.df_nomenclature is None:
            return None
        mask = self.df_nomenclature['Код'] == code
        if mask.any():
            return self.df_nomenclature[mask].iloc[0].to_dict()
        return None
    
    def get_product_by_name(self, name: str) -> Optional[Dict]:
        """Возвращает запись по названию (точное совпадение)"""
        if self.df_nomenclature is None:
            return None
        mask = self.df_nomenclature['Наименование'] == name
        if mask.any():
            return self.df_nomenclature[mask].iloc[0].to_dict()
        return None
    
    def get_products_by_type(self, type_name: str, page: int = 0, per_page: int = 10) -> Tuple[List[Dict], int]:
        """Возвращает продукты определённого типа с пагинацией"""
        if self.df_nomenclature is None:
            return [], 0
        
        mask = self.df_nomenclature['Тип'].str.lower() == type_name.lower()
        filtered = self.df_nomenclature[mask]
        
        total = len(filtered)
        start = page * per_page
        end = min(start + per_page, total)
        
        items = []
        for _, row in filtered.iloc[start:end].iterrows():
            items.append({
                'code': row['Код'],
                'name': row['Наименование'],
                'type': row['Тип'],
                'category': row.get('Категории', ''),
                'price': row.get('Цена производства', '0 ISK'),
                'multiplicity': row.get('Кратность', 1)
            })
        
        return items, total
    
    def add_product(self, name: str, type_name: str, category: str = '', 
                   price: str = '0 ISK', multiplicity: int = 1) -> Tuple[bool, str, str]:
        """Добавляет новое изделие/узел с автоматическим кодом"""
        try:
            if type_name.lower() == 'изделие':
                code = self.get_next_product_code()
            elif type_name.lower() == 'узел':
                code = self.get_next_node_code()
            else:
                return False, f"❌ Неизвестный тип: {type_name}", ""
            
            new_row = pd.DataFrame([{
                'Код': code,
                'Наименование': name,
                'Тип': type_name,
                'Цена производства': price,
                'Категории': category,
                'Кратность': multiplicity
            }])
            
            self.df_nomenclature = pd.concat([self.df_nomenclature, new_row], ignore_index=True)
            
            return True, f"✅ {type_name} добавлено с кодом {code}", code
            
        except Exception as e:
            logger.error(f"Ошибка добавления {type_name}: {e}")
            return False, f"❌ Ошибка: {e}", ""
    
    def add_material(self, name: str, category: str = '') -> Tuple[bool, str, str]:
        """Добавляет новый материал с автоматическим кодом"""
        try:
            code = self.get_next_material_code()
            
            new_row = pd.DataFrame([{
                'Код': code,
                'Наименование': name,
                'Тип': 'материал',
                'Цена производства': '',
                'Категории': category,
                'Кратность': ''
            }])
            
            self.df_nomenclature = pd.concat([self.df_nomenclature, new_row], ignore_index=True)
            
            return True, f"✅ Материал добавлен с кодом {code}", code
            
        except Exception as e:
            logger.error(f"Ошибка добавления материала: {e}")
            return False, f"❌ Ошибка: {e}", ""
    
    def update_product_field(self, code: str, field: str, value) -> Tuple[bool, str]:
        """Обновляет конкретное поле изделия/материала"""
        try:
            mask = self.df_nomenclature['Код'] == code
            if not mask.any():
                return False, f"❌ Запись с кодом {code} не найдена"
            
            self.df_nomenclature.loc[mask, field] = value
            return True, f"✅ Поле '{field}' обновлено"
            
        except Exception as e:
            logger.error(f"Ошибка обновления: {e}")
            return False, f"❌ Ошибка: {e}"
    
    def delete_product(self, code: str) -> Tuple[bool, str]:
        """Удаляет продукт и все связанные спецификации"""
        try:
            product = self.get_product_by_code(code)
            if not product:
                return False, f"❌ Запись с кодом {code} не найдена"
            
            product_name = product['Наименование']
            product_type = product['Тип']
            
            # Удаляем из номенклатуры
            self.df_nomenclature = self.df_nomenclature[self.df_nomenclature['Код'] != code]
            
            # Удаляем все спецификации, где этот код является родителем или потомком
            before_count = len(self.df_specifications)
            self.df_specifications = self.df_specifications[
                (self.df_specifications['Родитель'] != code) & 
                (self.df_specifications['Потомок'] != code)
            ]
            after_count = len(self.df_specifications)
            deleted_specs = before_count - after_count
            
            return True, f"✅ {product_type} '{product_name}' удалён\nУдалено связанных спецификаций: {deleted_specs}"
            
        except Exception as e:
            logger.error(f"Ошибка удаления: {e}")
            return False, f"❌ Ошибка: {e}"
    
    # ==================== СПЕЦИФИКАЦИИ ====================
    
    def get_specifications(self, parent_code: str) -> List[Dict]:
        """Возвращает спецификации для родителя"""
        if self.df_specifications is None:
            return []
        
        specs = self.df_specifications[self.df_specifications['Родитель'] == parent_code]
        result = []
        for _, row in specs.iterrows():
            result.append({
                'parent': row['Родитель'],
                'child': row['Потомок'],
                'quantity': float(row['Количество']) if row['Количество'] else 0
            })
        return result
    
    def link_node_to_product(self, parent_code: str, node_code: str, quantity: int) -> Tuple[bool, str]:
        """Привязывает узел к изделию"""
        try:
            existing = self.df_specifications[
                (self.df_specifications['Родитель'] == parent_code) & 
                (self.df_specifications['Потомок'] == node_code)
            ]
            
            if not existing.empty:
                return False, "❌ Такая связь уже существует"
            
            new_row = pd.DataFrame([{
                'Родитель': parent_code,
                'Потомок': node_code,
                'Количество': quantity
            }])
            
            self.df_specifications = pd.concat([self.df_specifications, new_row], ignore_index=True)
            
            return True, "✅ Узел привязан"
            
        except Exception as e:
            logger.error(f"Ошибка привязки узла: {e}")
            return False, f"❌ Ошибка: {e}"
    
    def link_material_to_product(self, parent_code: str, material_code: str, quantity: int) -> Tuple[bool, str]:
        """Привязывает материал к изделию/узлу"""
        try:
            existing = self.df_specifications[
                (self.df_specifications['Родитель'] == parent_code) & 
                (self.df_specifications['Потомок'] == material_code)
            ]
            
            if not existing.empty:
                return False, "❌ Такая связь уже существует"
            
            new_row = pd.DataFrame([{
                'Родитель': parent_code,
                'Потомок': material_code,
                'Количество': quantity
            }])
            
            self.df_specifications = pd.concat([self.df_specifications, new_row], ignore_index=True)
            
            return True, "✅ Материал привязан"
            
        except Exception as e:
            logger.error(f"Ошибка привязки материала: {e}")
            return False, f"❌ Ошибка: {e}"
    
    def remove_link(self, parent_code: str, child_code: str) -> Tuple[bool, str]:
        """Удаляет связь между родителем и потомком"""
        try:
            before = len(self.df_specifications)
            self.df_specifications = self.df_specifications[
                ~((self.df_specifications['Родитель'] == parent_code) & 
                  (self.df_specifications['Потомок'] == child_code))
            ]
            after = len(self.df_specifications)
            
            if before == after:
                return False, "❌ Связь не найдена"
            
            return True, "✅ Связь удалена"
            
        except Exception as e:
            logger.error(f"Ошибка удаления связи: {e}")
            return False, f"❌ Ошибка: {e}"
    
    def update_link_quantity(self, parent_code: str, child_code: str, quantity: int) -> Tuple[bool, str]:
        """Обновляет количество в связи"""
        try:
            mask = (self.df_specifications['Родитель'] == parent_code) & (self.df_specifications['Потомок'] == child_code)
            if not mask.any():
                return False, "❌ Связь не найдена"
            
            self.df_specifications.loc[mask, 'Количество'] = quantity
            return True, "✅ Количество обновлено"
            
        except Exception as e:
            logger.error(f"Ошибка обновления количества: {e}")
            return False, f"❌ Ошибка: {e}"
    
    # ==================== КАТЕГОРИИ ====================
    
    def get_unique_categories(self) -> List[str]:
        """Возвращает список уникальных категорий"""
        categories = set()
        
        if self.df_nomenclature is None:
            return []
        
        for cat in self.df_nomenclature['Категории']:
            if cat and str(cat).strip():
                parts = str(cat).split(' > ')
                for part in parts:
                    if part.strip():
                        categories.add(part.strip())
        
        return sorted(list(categories))
    
    def get_category_tree(self) -> dict:
        """Строит дерево категорий из номенклатуры"""
        tree = {}
        
        if self.df_nomenclature is None:
            return tree
        
        for _, row in self.df_nomenclature.iterrows():
            category_str = str(row.get('Категории', ''))
            if not category_str or pd.isna(category_str):
                continue
            
            path = [cat.strip() for cat in category_str.split(' > ') if cat.strip()]
            if not path:
                continue
            
            current = tree
            for i, cat in enumerate(path):
                if cat not in current:
                    current[cat] = {'_subcategories': {}, '_items': []}
                
                if i == len(path) - 1:
                    item_type = str(row.get('Тип', '')).lower()
                    if 'изделие' in item_type or 'узел' in item_type:
                        exists = False
                        for existing in current[cat]['_items']:
                            if existing['code'] == row['Код']:
                                exists = True
                                break
                        if not exists:
                            current[cat]['_items'].append({
                                'code': row['Код'],
                                'name': row['Наименование'],
                                'type': row['Тип']
                            })
                
                current = current[cat]['_subcategories']
        
        return tree
    
    def get_items_at_level(self, tree: dict, path: list) -> list:
        """Возвращает изделия на указанном уровне"""
        if not path:
            return []
        
        current = tree
        for cat in path:
            if cat in current:
                current = current[cat]['_subcategories']
            else:
                return []
        
        # Возвращаем изделия из последней категории
        last_cat = path[-1]
        temp = tree
        for cat in path:
            if cat in temp:
                if cat == last_cat:
                    return temp[cat].get('_items', [])
                temp = temp[cat]['_subcategories']
        
        return []
