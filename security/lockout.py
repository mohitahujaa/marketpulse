"""
Account security features: lockout, failed login tracking, etc.

Prevents brute force attacks by temporarily locking accounts after
multiple failed login attempts.
"""
import time
from collections import defaultdict
from typing import Dict, Tuple

from app.core.config import settings
from app.core.exceptions import AppException
from fastapi import status


class AccountLockedException(AppException):
    """Raised when account is temporarily locked due to too many failed attempts."""
    def __init__(self, retry_after: int):
        super().__init__(
            message=f"Account temporarily locked. Try again in {retry_after} seconds.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="ACCOUNT_LOCKED"
        )


class LoginAttemptTracker:
    """
    Track failed login attempts per email address.
    
    In production, use Redis instead of in-memory storage for:
    - Persistence across server restarts
    - Horizontal scaling support
    - Automatic TTL management
    """
    
    # Configuration
    MAX_ATTEMPTS = 5
    LOCKOUT_DURATION = 900  # 15 minutes in seconds
    
    def __init__(self):
        # email -> (failed_count, lockout_until_timestamp)
        self._attempts: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))
    
    def record_failed_attempt(self, email: str) -> None:
        """
        Record a failed login attempt.
        
        Args:
            email: User's email address
            
        Raises:
            AccountLockedException: If account is locked due to too many attempts
        """
        current_count, lockout_until = self._attempts[email]
        
        # Check if currently locked
        if lockout_until > time.time():
            retry_after = int(lockout_until - time.time())
            raise AccountLockedException(retry_after)
        
        # Reset count if lockout period has passed
        if lockout_until > 0 and lockout_until <= time.time():
            current_count = 0
        
        # Increment failed attempts
        current_count += 1
        
        # Lock account if max attempts reached
        if current_count >= self.MAX_ATTEMPTS:
            lockout_until = time.time() + self.LOCKOUT_DURATION
            self._attempts[email] = (current_count, lockout_until)
            raise AccountLockedException(self.LOCKOUT_DURATION)
        
        self._attempts[email] = (current_count, lockout_until)
    
    def record_successful_login(self, email: str) -> None:
        """
        Clear failed attempts on successful login.
        
        Args:
            email: User's email address
        """
        if email in self._attempts:
            del self._attempts[email]
    
    def is_locked(self, email: str) -> bool:
        """
        Check if account is currently locked.
        
        Args:
            email: User's email address
            
        Returns:
            True if locked, False otherwise
        """
        _, lockout_until = self._attempts.get(email, (0, 0.0))
        return lockout_until > time.time()


# Global instance (in production, replace with Redis-backed implementation)
login_tracker = LoginAttemptTracker()
