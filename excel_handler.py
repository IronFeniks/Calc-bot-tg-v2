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
            
            if 'Номенклатура' in excel_file.sheet_names:
                self.df_nomenclature = pd.read_excel(excel_file, sheet_name='Номенклатура').fillna('')
                logger.info(f"✅ Загружено {len(self.df_nomenclature)} записей номенклатуры")
            else:
                return False, "❌ В файле нет листа 'Номенклатура'"
            
            if 'Спецификации' in excel_file.sheet_names:
                self.df_specifications = pd.read_excel(excel_file, sheet_name='Спецификации').fillna('')
                logger.info(f"✅ Загружено {len(self.df_specifications)} спецификаций")
            else:
                return False, "❌ В файле нет листа 'Спецификации'"
            
            self._load_or_create_counters(excel_file)
            self._load_or_create_admins(excel_file)
            
            return True, "✅ Данные загружены"
            
        except Exception as e:
            logger.error(f"Ошибка загрузки Excel: {e}")
            return False, f"❌ Ошибка загрузки: {e}"
    
    def save_data(self) -> Tuple[bool, str]:
        """Сохраняет данные в Excel файл"""
        try:
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
    
    def get_all_admins(self) -> List[Dict]:
        """Возвращает список всех администраторов"""
        if self.df_admins is None:
            return []
        return self.df_admins.to_dict('records')
    
    def add_admin(self, user_id: int, username: str, first_name: str, added_by: int) -> Tuple[bool, str]:
        """Добавляет нового администратора"""
        try:
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
            self.save_data()
            return True, "✅ Администратор добавлен"
        except Exception as e:
            return False, f"❌ Ошибка: {e}"
    
    def remove_admin(self, user_id: int) -> Tuple[bool, str]:
        """Удаляет администратора"""
        from config import MASTER_ADMIN_ID
        if user_id == MASTER_ADMIN_ID:
            return False, "❌ Нельзя удалить главного администратора"
        
        try:
            self.df_admins = self.df_admins[self.df_admins['user_id'] != user_id]
            self.save_data()
            return True, "✅ Администратор удалён"
        except Exception as e:
            return False, f"❌ Ошибка: {e}"
    
    def toggle_admin(self, user_id: int) -> Tuple[bool, str]:
        """Переключает статус администратора (активен/неактивен)"""
        from config import MASTER_ADMIN_ID
        if user_id == MASTER_ADMIN_ID:
            return False, "❌ Нельзя деактивировать главного администратора"
        
        try:
            mask = self.df_admins['user_id'] == user_id
            if mask.any():
                current = self.df_admins.loc[mask, 'is_active'].iloc[0]
                self.df_admins.loc[mask, 'is_active'] = 0 if current == 1 else 1
                self.save_data()
                status = "деактивирован" if current == 1 else "активирован"
                return True, f"✅ Администратор {status}"
            return False, "❌ Администратор не найден"
        except Exception as e:
            return False, f"❌ Ошибка: {e}"
    
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
        """Возвращает запись по названию (с нормализацией)"""
        if self.df_nomenclature is None:
            return None
        
        search_name = name.strip().lower()
        
        for _, row in self.df_nomenclature.iterrows():
            row_name = str(row['Наименование']).strip().lower()
            if row_name == search_name:
                return row.to_dict()
        
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
    
    def get_all_categories(self) -> List[str]:
        """Возвращает плоский список всех уникальных категорий"""
        categories = set()
        
        if self.df_nomenclature is None:
            return []
        
        for _, row in self.df_nomenclature.iterrows():
            category_str = str(row.get('Категории', ''))
            if category_str and not pd.isna(category_str):
                for cat in category_str.split(' > '):
                    if cat.strip():
                        categories.add(cat.strip())
        
        return sorted(list(categories))
    
    def get_category_paths(self) -> List[str]:
        """Возвращает все уникальные пути категорий"""
        paths = set()
        
        if self.df_nomenclature is None:
            return []
        
        for _, row in self.df_nomenclature.iterrows():
            category_str = str(row.get('Категории', ''))
            if category_str and not pd.isna(category_str):
                paths.add(category_str.strip())
        
        return sorted(list(paths))
    
    def is_category_empty(self, category_path: str) -> bool:
        """Проверяет, пуста ли категория (нет подкатегорий и элементов)"""
        if self.df_nomenclature is None:
            return True
        
        # Проверяем подкатегории
        prefix = category_path + " > "
        for _, row in self.df_nomenclature.iterrows():
            cat = str(row.get('Категории', ''))
            if cat.startswith(prefix):
                return False
        
        # Проверяем элементы в самой категории
        for _, row in self.df_nomenclature.iterrows():
            cat = str(row.get('Категории', ''))
            if cat == category_path:
                return False
        
        return True
    
    def add_category(self, category_path: str) -> Tuple[bool, str]:
        """Добавляет новую категорию (создаёт пустую запись-заглушку)"""
        try:
            # Проверяем, существует ли уже такая категория
            existing_paths = self.get_category_paths()
            if category_path in existing_paths:
                return False, "❌ Такая категория уже существует"
            
            # Создаём заглушку для категории
            # Используем специальный код для категорий
            new_row = pd.DataFrame([{
                'Код': f"CAT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'Наименование': f"[КАТЕГОРИЯ] {category_path}",
                'Тип': 'категория',
                'Категории': category_path,
                'Цена производства': '0 ISK',
                'Кратность': 1
            }])
            self.df_nomenclature = pd.concat([self.df_nomenclature, new_row], ignore_index=True)
            self.save_data()
            return True, f"✅ Категория '{category_path}' добавлена"
        except Exception as e:
            return False, f"❌ Ошибка: {e}"
    
    def rename_category(self, old_path: str, new_path: str) -> Tuple[bool, str]:
        """Переименовывает категорию и обновляет все связанные записи"""
        try:
            if self.df_nomenclature is None:
                return False, "❌ Нет данных"
            
            updated = 0
            prefix = old_path + " > "
            
            for idx, row in self.df_nomenclature.iterrows():
                cat = str(row.get('Категории', ''))
                if cat == old_path:
                    self.df_nomenclature.at[idx, 'Категории'] = new_path
                    updated += 1
                elif cat.startswith(prefix):
                    new_cat = new_path + " > " + cat[len(prefix):]
                    self.df_nomenclature.at[idx, 'Категории'] = new_cat
                    updated += 1
            
            self.save_data()
            return True, f"✅ Обновлено {updated} записей"
        except Exception as e:
            return False, f"❌ Ошибка: {e}"
    
    def delete_category(self, category_path: str) -> Tuple[bool, str]:
        """Удаляет категорию (только если пуста)"""
        try:
            if not self.is_category_empty(category_path):
                return False, "❌ Категория не пуста"
            
            if self.df_nomenclature is None:
                return False, "❌ Нет данных"
            
            # Удаляем заглушку категории
            mask = (self.df_nomenclature['Категории'] == category_path) & (self.df_nomenclature['Тип'] == 'категория')
            self.df_nomenclature = self.df_nomenclature[~mask]
            self.save_data()
            return True, f"✅ Категория '{category_path}' удалена"
        except Exception as e:
            return False, f"❌ Ошибка: {e}"
    
    # ==================== ДОБАВЛЕНИЕ / РЕДАКТИРОВАНИЕ ЭЛЕМЕНТОВ ====================
    
    def add_item(self, item_type: str, name: str, category: str, multiplicity: int = 1, price: float = 0) -> Tuple[bool, str, str]:
        """Добавляет новый элемент (изделие/узел/материал)"""
        try:
            # Проверяем уникальность названия
            existing = self.get_product_by_name(name)
            if existing:
                return False, "❌ Элемент с таким названием уже существует", ""
            
            # Генерируем код
            if item_type == 'изделие':
                code = self.get_next_product_code()
            elif item_type == 'узел':
                code = self.get_next_node_code()
            else:
                code = self.get_next_material_code()
            
            price_str = f"{price} ISK" if price > 0 else "0 ISK"
            
            new_row = pd.DataFrame([{
                'Код': code,
                'Наименование': name,
                'Тип': item_type,
                'Категории': category,
                'Цена производства': price_str,
                'Кратность': multiplicity
            }])
            self.df_nomenclature = pd.concat([self.df_nomenclature, new_row], ignore_index=True)
            self.save_data()
            return True, f"✅ {item_type.capitalize()} '{name}' добавлен", code
        except Exception as e:
            return False, f"❌ Ошибка: {e}", ""
    
    def update_item(self, code: str, field: str, value: any) -> Tuple[bool, str]:
        """Обновляет поле элемента"""
        try:
            mask = self.df_nomenclature['Код'] == code
            if not mask.any():
                return False, "❌ Элемент не найден"
            
            if field == 'Цена производства':
                value = f"{value} ISK" if value > 0 else "0 ISK"
            
            self.df_nomenclature.loc[mask, field] = value
            self.save_data()
            return True, f"✅ Поле '{field}' обновлено"
        except Exception as e:
            return False, f"❌ Ошибка: {e}"
    
    def delete_item(self, code: str) -> Tuple[bool, str]:
        """Удаляет элемент и все его спецификации"""
        try:
            # Удаляем элемент
            mask = self.df_nomenclature['Код'] == code
            if not mask.any():
                return False, "❌ Элемент не найден"
            
            self.df_nomenclature = self.df_nomenclature[~mask]
            
            # Удаляем спецификации, где элемент родитель или потомок
            if self.df_specifications is not None:
                spec_mask = (self.df_specifications['Родитель'] == code) | (self.df_specifications['Потомок'] == code)
                self.df_specifications = self.df_specifications[~spec_mask]
            
            self.save_data()
            return True, "✅ Элемент и связанные спецификации удалены"
        except Exception as e:
            return False, f"❌ Ошибка: {e}"
    
    # ==================== СПЕЦИФИКАЦИИ ====================
    
    def add_specification(self, parent_code: str, child_code: str, quantity: float) -> Tuple[bool, str]:
        """Добавляет связь между родителем и потомком"""
        try:
            # Проверяем, существует ли уже такая связь
            if self.df_specifications is not None:
                existing = self.df_specifications[
                    (self.df_specifications['Родитель'] == parent_code) &
                    (self.df_specifications['Потомок'] == child_code)
                ]
                if len(existing) > 0:
                    return False, "❌ Такая связь уже существует"
            
            new_row = pd.DataFrame([{
                'Родитель': parent_code,
                'Потомок': child_code,
                'Количество': quantity
            }])
            
            if self.df_specifications is None:
                self.df_specifications = new_row
            else:
                self.df_specifications = pd.concat([self.df_specifications, new_row], ignore_index=True)
            
            self.save_data()
            return True, "✅ Спецификация добавлена"
        except Exception as e:
            return False, f"❌ Ошибка: {e}"
    
    def update_specification(self, parent_code: str, child_code: str, quantity: float) -> Tuple[bool, str]:
        """Обновляет количество в спецификации"""
        try:
            if self.df_specifications is None:
                return False, "❌ Спецификация не найдена"
            
            mask = (self.df_specifications['Родитель'] == parent_code) & (self.df_specifications['Потомок'] == child_code)
            if not mask.any():
                return False, "❌ Спецификация не найдена"
            
            self.df_specifications.loc[mask, 'Количество'] = quantity
            self.save_data()
            return True, "✅ Количество обновлено"
        except Exception as e:
            return False, f"❌ Ошибка: {e}"
    
    def delete_specification(self, parent_code: str, child_code: str) -> Tuple[bool, str]:
        """Удаляет спецификацию"""
        try:
            if self.df_specifications is None:
                return False, "❌ Спецификация не найдена"
            
            mask = (self.df_specifications['Родитель'] == parent_code) & (self.df_specifications['Потомок'] == child_code)
            if not mask.any():
                return False, "❌ Спецификация не найдена"
            
            self.df_specifications = self.df_specifications[~mask]
            self.save_data()
            return True, "✅ Спецификация удалена"
        except Exception as e:
            return False, f"❌ Ошибка: {e}"
    
    def get_available_children(self, parent_type: str) -> List[Dict]:
        """Возвращает доступных потомков для родителя определённого типа"""
        if self.df_nomenclature is None:
            return []
        
        if parent_type == 'изделие':
            allowed_types = ['узел', 'материал']
        elif parent_type == 'узел':
            allowed_types = ['материал']
        else:
            return []
        
        result = []
        for _, row in self.df_nomenclature.iterrows():
            if row['Тип'] in allowed_types:
                result.append({
                    'code': row['Код'],
                    'name': row['Наименование'],
                    'type': row['Тип']
                })
        
        return result
    
    # ==================== ПОИСК ====================
    
    def search_items(self, query: str) -> List[Dict]:
        """Поиск по названию и коду"""
        if self.df_nomenclature is None:
            return []
        
        query_lower = query.lower()
        result = []
        
        for _, row in self.df_nomenclature.iterrows():
            name = str(row['Наименование']).lower()
            code = str(row['Код']).lower()
            
            if query_lower in name or query_lower in code:
                result.append({
                    'code': row['Код'],
                    'name': row['Наименование'],
                    'type': row['Тип'],
                    'category': row.get('Категории', ''),
                    'price': row.get('Цена производства', '0 ISK'),
                    'multiplicity': row.get('Кратность', 1)
                })
        
        return result
