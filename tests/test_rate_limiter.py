"""
test_rate_limiter.py
====================
Automated test suite verifying the AuthRateLimiter service per Section 33:
1. Failed attempts under threshold allow further requests.
2. Reaching max_attempts locks out the source for cooldown_seconds.
3. Requests during lockout return active rate limit and remaining cooldown time.
4. Cooldown expiration releases the lockout and permits attempts.
5. Successful login resets counters and removes lockouts.
6. Sliding window drops expired failed attempt timestamps.
7. Distinct source keys are isolated from one another.
8. Concurrent multi-threaded attempts are safely synchronized.
"""

import os
import threading
import time
import unittest
from unittest.mock import patch

from app.services.rate_limiter import AuthRateLimiter


class TestAuthRateLimiter(unittest.TestCase):

    def setUp(self):
        self.limiter = AuthRateLimiter(max_attempts=3, cooldown_seconds=10, window_seconds=20)

    def test_attempts_under_threshold_not_limited(self):
        """Under threshold, is_rate_limited returns False with full remaining attempts."""
        key = "192.168.1.100"
        self.assertFalse(self.limiter.is_rate_limited(key)[0])
        self.assertEqual(self.limiter.get_remaining_attempts(key), 3)

        # 1st failure
        locked, retry_after = self.limiter.record_failed_attempt(key)
        self.assertFalse(locked)
        self.assertEqual(retry_after, 0)
        self.assertFalse(self.limiter.is_rate_limited(key)[0])
        self.assertEqual(self.limiter.get_remaining_attempts(key), 2)

        # 2nd failure
        locked, retry_after = self.limiter.record_failed_attempt(key)
        self.assertFalse(locked)
        self.assertEqual(retry_after, 0)
        self.assertFalse(self.limiter.is_rate_limited(key)[0])
        self.assertEqual(self.limiter.get_remaining_attempts(key), 1)

    def test_reaching_threshold_triggers_lockout(self):
        """DoD: Repeated failed logins from one source are throttled/locked temporarily."""
        key = "192.168.1.101"
        base_time = 1000.0

        # Record 3 failures at base_time
        self.limiter.record_failed_attempt(key, now=base_time)
        self.limiter.record_failed_attempt(key, now=base_time + 1)
        locked, retry_after = self.limiter.record_failed_attempt(key, now=base_time + 2)

        # 3rd failure reaches max_attempts (3)
        self.assertTrue(locked)
        self.assertEqual(retry_after, 10)
        self.assertEqual(self.limiter.get_remaining_attempts(key, now=base_time + 2), 0)

        # Intermediate check at base_time + 4s (6s cooldown remaining)
        is_limited, remaining = self.limiter.is_rate_limited(key, now=base_time + 4)
        self.assertTrue(is_limited)
        self.assertEqual(remaining, 8)  # lockout was at 1002 + 10 = 1012; at 1004 => 8s left

    def test_cooldown_expiration_allows_retry(self):
        """DoD: Legitimate retries after cooldown succeed."""
        key = "192.168.1.102"
        base_time = 2000.0

        for _ in range(3):
            self.limiter.record_failed_attempt(key, now=base_time)

        # Locked at base_time (until base_time + 10 = 2010.0)
        self.assertTrue(self.limiter.is_rate_limited(key, now=base_time + 5)[0])

        # At base_time + 11.0, cooldown has expired
        is_limited, retry_after = self.limiter.is_rate_limited(key, now=base_time + 11)
        self.assertFalse(is_limited)
        self.assertEqual(retry_after, 0)
        self.assertEqual(self.limiter.get_remaining_attempts(key, now=base_time + 11), 3)

    def test_successful_attempt_resets_counters(self):
        """Successful login resets failed attempts and lockouts immediately."""
        key = "192.168.1.103"
        base_time = 3000.0

        # Record 2 failed attempts
        self.limiter.record_failed_attempt(key, now=base_time)
        self.limiter.record_failed_attempt(key, now=base_time + 1)
        self.assertEqual(self.limiter.get_remaining_attempts(key, now=base_time + 1), 1)

        # Success resets counter
        self.limiter.record_successful_attempt(key)
        self.assertEqual(self.limiter.get_remaining_attempts(key, now=base_time + 2), 3)
        self.assertFalse(self.limiter.is_rate_limited(key, now=base_time + 2)[0])

    def test_sliding_window_drops_stale_attempts(self):
        """Attempts older than window_seconds (20s) expire and do not trigger lockout."""
        key = "192.168.1.104"
        base_time = 4000.0

        # Attempt 1 at t=4000
        self.limiter.record_failed_attempt(key, now=base_time)
        # Attempt 2 at t=4005
        self.limiter.record_failed_attempt(key, now=base_time + 5)

        # At t=4025 (25s later), Attempt 1 (at t=4000) and Attempt 2 (at t=4005) are outside window (20s)
        # So only Attempt 3 remains in window; remaining attempts should be 3 - 1 = 2
        self.limiter.record_failed_attempt(key, now=base_time + 25)
        is_limited, _ = self.limiter.is_rate_limited(key, now=base_time + 25)
        self.assertFalse(is_limited)
        self.assertEqual(self.limiter.get_remaining_attempts(key, now=base_time + 25), 2)

    def test_isolated_source_keys(self):
        """Failed attempts from attacker IP do not lock out victim IP."""
        attacker_ip = "192.168.1.200"
        victim_ip = "192.168.1.201"
        base_time = 5000.0

        for _ in range(3):
            self.limiter.record_failed_attempt(attacker_ip, now=base_time)

        self.assertTrue(self.limiter.is_rate_limited(attacker_ip, now=base_time)[0])
        self.assertFalse(self.limiter.is_rate_limited(victim_ip, now=base_time)[0])
        self.assertEqual(self.limiter.get_remaining_attempts(victim_ip, now=base_time), 3)

    def test_thread_safety(self):
        """Concurrent multi-threaded failure recordings are thread-safe."""
        limiter = AuthRateLimiter(max_attempts=50, cooldown_seconds=30, window_seconds=60)
        key = "10.0.0.1"

        def worker():
            for _ in range(10):
                limiter.record_failed_attempt(key)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly 50 attempts recorded => locked out
        is_limited, _ = limiter.is_rate_limited(key)
        self.assertTrue(is_limited)

    def test_environment_variable_configuration(self):
        """Limiter reads fallback defaults from environment variables when unconfigured."""
        with patch.dict(os.environ, {
            "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "7",
            "AUTH_RATE_LIMIT_COOLDOWN_SECONDS": "45",
            "AUTH_RATE_LIMIT_WINDOW_SECONDS": "90"
        }):
            env_limiter = AuthRateLimiter()
            self.assertEqual(env_limiter.max_attempts, 7)
            self.assertEqual(env_limiter.cooldown_seconds, 45)
            self.assertEqual(env_limiter.window_seconds, 90)


if __name__ == "__main__":
    unittest.main(verbosity=2)
