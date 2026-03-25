import time
import logging

logger = logging.getLogger(__name__)

class UserLock:
    """Блокировка для работы в топике (только один пользователь)"""
    
    def __init__(self, timeout_seconds: int = 300):
        self.current_user = None
        self.lock_time = 0
        self.username = None
        self.first_name = None
        self.timeout = timeout_seconds
    
    def acquire(self, user_id: int, username: str = None, first_name: str = None) -> bool:
        """Захватить блокировку"""
        # Проверяем таймаут
        if self.current_user and (time.time() - self.lock_time) > self.timeout:
            self.release()
        
        if self.current_user is None:
            self.current_user = user_id
            self.lock_time = time.time()
            self.username = username
            self.first_name = first_name
            logger.info(f"🔒 Блокировка захвачена пользователем {user_id}")
            return True
        return False
    
    def release(self) -> None:
        """Освободить блокировку"""
        if self.current_user:
            logger.info(f"🔓 Блокировка освобождена (пользователь {self.current_user})")
            self.current_user = None
            self.username = None
            self.first_name = None
            self.lock_time = 0
    
    def is_locked(self) -> bool:
        """Проверка, заблокирован ли бот"""
        return self.current_user is not None
    
    def get_lock_info(self) -> dict:
        """Получить информацию о текущем блокирующем пользователе"""
        if self.current_user:
            return {
                'user_id': self.current_user,
                'username': self.username,
                'first_name': self.first_name
            }
        return None
    
    def check_timeout(self) -> bool:
        """Проверить и сбросить блокировку по таймауту"""
        if self.current_user and (time.time() - self.lock_time) > self.timeout:
            logger.info(f"⏰ Тайма
