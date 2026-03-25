import time
import logging

logger = logging.getLogger(__name__)

class UserLock:
    """
    Блокировка для работы в топике (только один пользователь)
    Используется только для сообщений из топика группы
    """
    
    def __init__(self, timeout_seconds: int = 300):
        """
        Инициализация блокировки
        
        Args:
            timeout_seconds: время автоматического снятия блокировки (секунд)
        """
        self.current_user = None
        self.lock_time = 0
        self.username = None
        self.first_name = None
        self.timeout = timeout_seconds
    
    def acquire(self, user_id: int, username: str = None, first_name: str = None) -> bool:
        """
        Захватить блокировку
        
        Args:
            user_id: ID пользователя
            username: имя пользователя (@username)
            first_name: имя пользователя
        
        Returns:
            True если блокировка захвачена, False если уже занято
        """
        # Проверяем таймаут у текущего владельца
        if self.current_user and (time.time() - self.lock_time) > self.timeout:
            logger.info(f"⏰ Таймаут блокировки для пользователя {self.current_user}, освобождаем")
            self.release()
        
        if self.current_user is None:
            self.current_user = user_id
            self.lock_time = time.time()
            self.username = username
            self.first_name = first_name
            logger.info(f"🔒 Блокировка захвачена пользователем {user_id} (username={username}, name={first_name})")
            return True
        
        logger.info(f"❌ Попытка захватить блокировку пользователем {user_id}, но уже занято пользователем {self.current_user}")
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
        """Проверить, заблокирован ли бот"""
        # Автоматически проверяем таймаут
        if self.current_user and (time.time() - self.lock_time) > self.timeout:
            logger.info(f"⏰ Таймаут блокировки для пользователя {self.current_user}, освобождаем")
            self.release()
        return self.current_user is not None
    
    def get_lock_info(self) -> dict:
        """
        Получить информацию о текущем блокирующем пользователе
        
        Returns:
            dict с ключами: user_id, username, first_name
            или None если блокировка свободна
        """
        # Автоматически проверяем таймаут
        if self.current_user and (time.time() - self.lock_time) > self.timeout:
            logger.info(f"⏰ Таймаут блокировки для пользователя {self.current_user}, освобождаем")
            self.release()
            return None
        
        if self.current_user:
            return {
                'user_id': self.current_user,
                'username': self.username,
                'first_name': self.first_name
            }
        return None
    
    def check_timeout(self) -> bool:
        """
        Проверить и сбросить блокировку по таймауту
        
        Returns:
            True если блокировка была сброшена, False если нет
        """
        if self.current_user and (time.time() - self.lock_time) > self.timeout:
            logger.info(f"⏰ Таймаут блокировки для пользователя {self.current_user}, освобождаем")
            self.release()
            return True
        return False
    
    def refresh(self, user_id: int) -> bool:
        """
        Обновить время блокировки (продлить сессию)
        
        Args:
            user_id: ID пользователя, который хочет продлить блокировку
        
        Returns:
            True если блокировка обновлена, False если пользователь не владелец
        """
        if self.current_user == user_id:
            self.lock_time = time.time()
            logger.info(f"🔄 Обновлено время блокировки для пользователя {user_id}")
            return True
        return False
    
    def get_remaining_time(self) -> int:
        """
        Получить оставшееся время блокировки в секундах
        
        Returns:
            оставшееся время в секундах, 0 если блокировка свободна
        """
        if self.current_user:
            remaining = self.timeout - (time.time() - self.lock_time)
            return max(0, int(remaining))
        return 0
