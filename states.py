from enum import Enum, auto

class CalculatorStates(Enum):
    """Состояния калькулятора"""
    INSTRUCTION = auto()
    MODE_SELECTION = auto()
    CATEGORIES = auto()
    EFFICIENCY = auto()
    TAX = auto()
    PRODUCT_SELECTION = auto()
    PRODUCT_SELECTION_MULTI = auto()
    QUANTITY = auto()
    MARKET_PRICE = auto()
    DRAWING_PRICE = auto()
    MATERIALS_LIST = auto()
    PRICE_INPUT = auto()
    PRICE_INPUT_MISSING = auto()
    RESULT = auto()
    RESULT_DETAIL = auto()
    EXPLANATION = auto()


class AdminStates(Enum):
    """Состояния админки"""
    MAIN_MENU = auto()
    
    # Категории
    CATEGORY_LIST = auto()
    CATEGORY_ADD_NAME = auto()
    CATEGORY_ADD_PARENT = auto()
    CATEGORY_EDIT_SELECT = auto()
    CATEGORY_EDIT_NAME = auto()
    CATEGORY_DELETE_CONFIRM = auto()
    
    # Изделия
    PRODUCT_LIST = auto()
    PRODUCT_ADD_NAME = auto()
    PRODUCT_ADD_CATEGORY = auto()
    PRODUCT_ADD_MULTIPLICITY = auto()
    PRODUCT_ADD_PRICE = auto()
    PRODUCT_LINK_MENU = auto()
    PRODUCT_LINK_NODE_SELECT = auto()
    PRODUCT_LINK_NODE_QUANTITY = auto()
    PRODUCT_LINK_MATERIAL_SELECT = auto()
    PRODUCT_LINK_MATERIAL_QUANTITY = auto()
    PRODUCT_CREATE_NODE_NAME = auto()
    PRODUCT_CREATE_NODE_MULTIPLICITY = auto()
    PRODUCT_CREATE_NODE_PRICE = auto()
    PRODUCT_CREATE_MATERIAL_NAME = auto()
    PRODUCT_CREATE_MATERIAL_PRICE = auto()
    PRODUCT_EDIT_SELECT = auto()
    PRODUCT_EDIT_FIELD = auto()
    PRODUCT_EDIT_NAME = auto()
    PRODUCT_EDIT_CATEGORY = auto()
    PRODUCT_EDIT_MULTIPLICITY = auto()
    PRODUCT_EDIT_PRICE = auto()
    PRODUCT_DELETE_CONFIRM = auto()
    PRODUCT_SEARCH = auto()
    
    # Узлы
    NODE_LIST = auto()
    NODE_ADD_NAME = auto()
    NODE_ADD_CATEGORY = auto()
    NODE_ADD_MULTIPLICITY = auto()
    NODE_ADD_PRICE = auto()
    NODE_LINK_MENU = auto()
    NODE_LINK_MATERIAL_SELECT = auto()
    NODE_LINK_MATERIAL_QUANTITY = auto()
    NODE_CREATE_MATERIAL_NAME = auto()
    NODE_CREATE_MATERIAL_PRICE = auto()
    NODE_EDIT_SELECT = auto()
    NODE_EDIT_FIELD = auto()
    NODE_EDIT_NAME = auto()
    NODE_EDIT_CATEGORY = auto()
    NODE_EDIT_MULTIPLICITY = auto()
    NODE_EDIT_PRICE = auto()
    NODE_DELETE_CONFIRM = auto()
    NODE_SEARCH = auto()
    
    # Материалы
    MATERIAL_LIST = auto()
    MATERIAL_ADD_NAME = auto()
    MATERIAL_ADD_CATEGORY = auto()
    MATERIAL_ADD_PRICE = auto()
    MATERIAL_EDIT_SELECT = auto()
    MATERIAL_EDIT_FIELD = auto()
    MATERIAL_EDIT_NAME = auto()
    MATERIAL_EDIT_CATEGORY = auto()
    MATERIAL_EDIT_PRICE = auto()
    MATERIAL_DELETE_CONFIRM = auto()
    MATERIAL_SEARCH = auto()
    
    # Спецификации
    SPEC_SELECT_PARENT = auto()
    SPEC_MENU = auto()
    SPEC_LINK_NODE_SELECT = auto()
    SPEC_LINK_NODE_QUANTITY = auto()
    SPEC_LINK_MATERIAL_SELECT = auto()
    SPEC_LINK_MATERIAL_QUANTITY = auto()
    SPEC_UNLINK_CONFIRM = auto()
    
    # Администраторы
    ADMIN_LIST = auto()
    ADMIN_ADD_ID = auto()
    ADMIN_ADD_CONFIRM = auto()
    ADMIN_DELETE_CONFIRM = auto()
    ADMIN_TOGGLE_CONFIRM = auto()
    
    # Поиск
    SEARCH_QUERY = auto()
    SEARCH_RESULTS = auto()
