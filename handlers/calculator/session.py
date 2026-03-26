import logging

logger = logging.getLogger(__name__)

# Словарь для хранения сессий пользователей
sessions = {}


def get_session(user_id: int) -> dict:
    """Получить сессию пользователя"""
    if user_id not in sessions:
        sessions[user_id] = {
            'step': None,
            'mode': None,              # 'single' или 'multi'
            'category_path': [],
            'category_tree': None,
            'current_products': [],    # список изделий на текущей странице
            'selected_products': [],   # выбранные названия (для multi)
            'efficiency': None,
            'tax': None,
            'selected_product': None,  # для single
            'qty': None,
            'market_price': None,
            'drawing_price': None,
            'multi_products': [],      # полные данные изделий для multi
            'multi_products_data': [], # собранные данные после ввода параметров
            'current_product_index': 0,
            'materials_list': [],
            'nodes_list': [],
            'materials_page': 0,
            'price_input_items': [],
            'current_material': 0,
            'missing_materials': [],
            'single_product_detail': {},
            'products_with_details': [],
            'multi_result': {},
            'result_page': 0,
            'last_result_text': None,
            'last_result_keyboard': None
        }
    return sessions[user_id]


def clear_session(user_id: int):
    """Очистить сессию пользователя"""
    if user_id in sessions:
        del sessions[user_id]
        logger.info(f"🗑️ Сессия пользователя {user_id} очищена")


def reset_session_for_new_calculation(user_id: int, mode: str, category_path: list = None, category_tree: dict = None):
    """Сброс сессии для нового расчёта с сохранением пути категории"""
    old_session = get_session(user_id)
    
    sessions[user_id] = {
        'step': 'efficiency' if mode == 'single' else 'multi_efficiency',
        'mode': mode,
        'category_path': category_path.copy() if category_path else [],
        'category_tree': category_tree or old_session.get('category_tree'),
        'current_products': [],
        'selected_products': [],
        'efficiency': None,
        'tax': None,
        'selected_product': None,
        'qty': None,
        'market_price': None,
        'drawing_price': None,
        'multi_products': [],
        'multi_products_data': [],
        'current_product_index': 0,
        'materials_list': [],
        'nodes_list': [],
        'materials_page': 0,
        'price_input_items': [],
        'current_material': 0,
        'missing_materials': [],
        'single_product_detail': {},
        'products_with_details': [],
        'multi_result': {},
        'result_page': 0,
        'last_result_text': None,
        'last_result_keyboard': None
    }
    
    logger.info(f"🔄 Сессия пользователя {user_id} сброшена для нового расчёта (mode={mode})")
