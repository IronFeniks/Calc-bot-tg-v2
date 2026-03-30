import logging
from keyboards.calculator import clear_user_mapping

logger = logging.getLogger(__name__)

# Словарь для хранения сессий пользователей
sessions = {}


def get_session(user_id: int) -> dict:
    """Получить сессию пользователя"""
    if user_id not in sessions:
        sessions[user_id] = {
            # Основные параметры
            'step': None,              # текущий шаг
            'mode': None,              # 'single' или 'multi'
            
            # Категории
            'category_path': [],       # путь по категориям
            'category_tree': None,     # дерево категорий
            
            # Параметры расчёта
            'efficiency': None,        # эффективность (%)
            'tax': None,               # налог (%)
            
            # Одиночный режим
            'selected_product': None,  # выбранное изделие
            'qty': None,               # количество
            'market_price': None,      # рыночная цена
            'drawing_price': None,     # стоимость чертежа изделия
            
            # Множественный режим
            'selected_products': [],   # выбранные названия
            'current_products': [],    # список изделий на текущей странице
            'multi_products': [],      # полные данные изделий
            'multi_products_data': [], # собранные данные после ввода параметров
            'current_product_index': 0,
            'temp_quantity': None,
            'temp_market_price': None,
            
            # Режим расчёта (покупка узлов / производство узлов)
            'calculation_mode': 'buy_nodes',  # 'buy_nodes' или 'produce_nodes'
            
            # Материалы и узлы
            'materials_list': [],      # список материалов
            'nodes_list': [],          # список узлов
            'drawings_list': [],       # список чертежей узлов (для режима produce_nodes)
            'unified_price_items': [], # унифицированный список для ввода цен
            'materials_page': 0,       # текущая страница материалов
            'price_input_items': [],   # элементы для пошагового ввода цен
            'current_material': 0,     # индекс текущего элемента для ввода цены
            'missing_materials': [],   # материалы без цен
            
            # Данные для одиночного режима
            'single_product_detail': {},
            
            # Данные для множественного режима
            'products_with_details': [],
            'multi_result': {},
            'result_page': 0,
            
            # Результаты
            'last_result_text': None,
            'last_result_keyboard': None,
            'last_calculation_data': None,
            'calculation_mode_name': None,
            
            # Сравнительный расчёт
            'first_calculation_completed': None,
            'first_calculation_mode': None,
            'first_calculation_tax': None,
            'first_calculation_result': None,
            'first_calculation_data': None,
            'first_calculation_mode_name': None,
            'second_calculation_result': None,
            'second_calculation_mode_name': None,
            'second_calculation_data': None,
            'comparison_mode': False,
            'comparison_target_mode': None,
            'comparison_page': 0,
            'has_nodes': False,
            'product_name': None,
            'quantity': 0
        }
    return sessions[user_id]


def clear_session(user_id: int):
    """Очистить сессию пользователя"""
    if user_id in sessions:
        del sessions[user_id]
        clear_user_mapping(user_id)
        logger.info(f"🗑️ Сессия пользователя {user_id} очищена")


def reset_session_for_new_calculation(user_id: int, mode: str, category_path: list = None, category_tree: dict = None):
    """Сброс сессии для нового расчёта с сохранением пути категории"""
    old_session = get_session(user_id)
    
    sessions[user_id] = {
        'step': 'efficiency' if mode == 'single' else 'multi_efficiency',
        'mode': mode,
        'category_path': category_path.copy() if category_path else [],
        'category_tree': category_tree or old_session.get('category_tree'),
        
        # Параметры расчёта (будут заполнены)
        'efficiency': None,
        'tax': None,
        
        # Одиночный режим
        'selected_product': None,
        'qty': None,
        'market_price': None,
        'drawing_price': None,
        
        # Множественный режим
        'selected_products': [],
        'current_products': [],
        'multi_products': [],
        'multi_products_data': [],
        'current_product_index': 0,
        'temp_quantity': None,
        'temp_market_price': None,
        
        # Режим расчёта (по умолчанию — покупка узлов)
        'calculation_mode': 'buy_nodes',
        
        # Материалы и узлы
        'materials_list': [],
        'nodes_list': [],
        'drawings_list': [],
        'unified_price_items': [],
        'materials_page': 0,
        'price_input_items': [],
        'current_material': 0,
        'missing_materials': [],
        
        # Данные для одиночного режима
        'single_product_detail': {},
        
        # Данные для множественного режима
        'products_with_details': [],
        'multi_result': {},
        'result_page': 0,
        
        # Результаты
        'last_result_text': None,
        'last_result_keyboard': None,
        'last_calculation_data': None,
        'calculation_mode_name': None,
        
        # Сравнительный расчёт (сбрасываем)
        'first_calculation_completed': None,
        'first_calculation_mode': None,
        'first_calculation_tax': None,
        'first_calculation_result': None,
        'first_calculation_data': None,
        'first_calculation_mode_name': None,
        'second_calculation_result': None,
        'second_calculation_mode_name': None,
        'second_calculation_data': None,
        'comparison_mode': False,
        'comparison_target_mode': None,
        'comparison_page': 0,
        'has_nodes': False,
        'product_name': None,
        'quantity': 0
    }
    
    logger.info(f"🔄 Сессия пользователя {user_id} сброшена для нового расчёта (mode={mode})")
