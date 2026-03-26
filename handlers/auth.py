"""
Модуль для проверки прав доступа
"""
from config import MASTER_ADMIN_ID, ADMIN_IDS
from excel_handler import get_excel_handler


def is_admin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором
    
    Args:
        user_id: Telegram ID пользователя
    
    Returns:
        True если администратор, иначе False
    """
    # Главный администратор всегда имеет доступ
    if user_id == MASTER_ADMIN_ID:
        return True
    
    # Проверяем в списке из конфига (на время разработки)
    if user_id in ADMIN_IDS:
        return True
    
    # Проверяем в Excel
    excel = get_excel_handler()
    if excel:
        return excel.is_admin(user_id)
    
    return False
