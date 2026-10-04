"""
rate_limiter.py
===============
Thread-safe rate limiting and brute-force protection service for authentication routes.
Implements the rate-limiting principle per Section 33:
- Tracks failed login attempts per source/client identifier.
- Throttles and temporarily locks sources exceeding maximum failed attempts.
- Enforces an automated cooldown period before permitting further attempts.
- Cleans up stale timestamps and resets counters on successful authentication.
"""

import math
import os
import threading
import time
from typing import Dict, List, Optional, Tuple


class AuthRateLimiter:
    """
    In-memory, thread-safe sliding window rate limiter with temporary lockouts for brute-force mitigation.
    """

    def __init__(
        self,
        max_attempts: Optional[int] = None,
        cooldown_seconds: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ):
        self._max_attempts = max_attempts
        self._cooldown_seconds = cooldown_seconds
        self._window_seconds = window_seconds

        # Storage mapping source_key -> list of failure timestamps
        self._attempts: Dict[str, List[float]] = {}
        # Storage mapping source_key -> lockout expiry timestamp
        self._lockouts: Dict[str, float] = {}
        self._lock = threading.Lock()

    @property
    def max_attempts(self) -> int:
        if self._max_attempts is not None:
            return self._max_attempts
        try:
            return int(os.environ.get("AUTH_RATE_LIMIT_MAX_ATTEMPTS", "5"))
        except (ValueError, TypeError):
            return 5

    @property
    def cooldown_seconds(self) -> int:
        if self._cooldown_seconds is not None:
            return self._cooldown_seconds
        try:
            return int(os.environ.get("AUTH_RATE_LIMIT_COOLDOWN_SECONDS", "60"))
        except (ValueError, TypeError):
            return 60

    @property
    def window_seconds(self) -> int:
        if self._window_seconds is not None:
            return self._window_seconds
        try:
            return int(os.environ.get("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60"))
        except (ValueError, TypeError):
            return 60

    def is_rate_limited(self, key: str, now: Optional[float] = None) -> Tuple[bool, int]:
        """
        Checks whether the specified source key is currently rate limited or locked out.

        Args:
            key: The unique source identifier (e.g. IP address or client host).
            now: Optional timestamp override for time travel / deterministic testing.

        Returns:
            Tuple of (is_limited: bool, retry_after_seconds: int).
        """
        current_time = now if now is not None else time.time()

        with self._lock:
            # 1. Check active lockout
            if key in self._lockouts:
                lockout_until = self._lockouts[key]
                if current_time < lockout_until:
                    retry_after = max(1, int(math.ceil(lockout_until - current_time)))
                    return True, retry_after
                else:
                    # Lockout expired — clear lockout and prior attempts for a fresh start
                    del self._lockouts[key]
                    self._attempts.pop(key, None)

            # 2. Clean up attempts outside sliding window
            cutoff = current_time - self.window_seconds
            if key in self._attempts:
                valid_attempts = [ts for ts in self._attempts[key] if ts > cutoff]
                if valid_attempts:
                    self._attempts[key] = valid_attempts
                else:
                    del self._attempts[key]

                if len(valid_attempts) >= self.max_attempts:
                    # Trigger lockout
                    lockout_until = current_time + self.cooldown_seconds
                    self._lockouts[key] = lockout_until
                    return True, self.cooldown_seconds

            return False, 0

    def record_failed_attempt(self, key: str, now: Optional[float] = None) -> Tuple[bool, int]:
        """
        Records a failed login attempt for the given key. If the failure count reaches
        the configured threshold, locks out the source for the cooldown duration.

        Args:
            key: The unique source identifier.
            now: Optional timestamp override.

        Returns:
            Tuple of (is_locked_out: bool, retry_after_seconds: int).
        """
        current_time = now if now is not None else time.time()

        with self._lock:
            # Clean up old attempts
            cutoff = current_time - self.window_seconds
            existing = [ts for ts in self._attempts.get(key, []) if ts > cutoff]
            existing.append(current_time)
            self._attempts[key] = existing

            if len(existing) >= self.max_attempts:
                lockout_until = current_time + self.cooldown_seconds
                self._lockouts[key] = lockout_until
                retry_after = self.cooldown_seconds
                return True, retry_after

            return False, 0

    def record_successful_attempt(self, key: str) -> None:
        """
        Clears failed attempts and lockouts upon a successful login from the source.
        """
        with self._lock:
            self._attempts.pop(key, None)
            self._lockouts.pop(key, None)

    def get_remaining_attempts(self, key: str, now: Optional[float] = None) -> int:
        """
        Returns the number of remaining allowed failed attempts before triggering lockout.
        """
        current_time = now if now is not None else time.time()

        with self._lock:
            if key in self._lockouts and current_time < self._lockouts[key]:
                return 0

            cutoff = current_time - self.window_seconds
            existing = [ts for ts in self._attempts.get(key, []) if ts > cutoff]
            return max(0, self.max_attempts - len(existing))

    def reset(self) -> None:
        """
        Resets all rate limiter state (used for testing and administrative resets).
        """
        with self._lock:
            self._attempts.clear()
            self._lockouts.clear()


# Global default instance
auth_rate_limiter = AuthRateLimiter()
