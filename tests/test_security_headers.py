"""
test_security_headers.py
========================
Automated test suite verifying HTTPS/TLS Enforcement & Security Headers per Section 33:
1. All API responses carry OWASP recommended security headers:
   - X-Content-Type-Options: nosniff
   - X-Frame-Options: DENY
   - X-XSS-Protection: 1; mode=block
   - Referrer-Policy: strict-origin-when-cross-origin
   - Content-Security-Policy: default-src 'self' ...
   - Permissions-Policy
2. HSTS (Strict-Transport-Security) header is injected for HTTPS requests and when HTTPS is enforced.
3. Plain HTTP requests are redirected (HTTP 307) or rejected when ENFORCE_HTTPS=true or in production.
4. Plain HTTP requests are allowed in development/local environments (ENFORCE_HTTPS=false).
5. Secure cookie utility sets HttpOnly, Secure, and SameSite=Lax flags.
"""

import os
import unittest
from unittest.mock import patch
from fastapi import Response
from fastapi.testclient import TestClient

# Ensure test JWT_SECRET is set
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-running-automated-test-suite-2026-64-byte-secure-key")

from app.main import app
from app.middleware.security_headers import set_secure_auth_cookie
from app.models.config import is_cookie_secure, is_https_enforced, get_hsts_max_age


class TestSecurityHeadersAndHTTPS(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, follow_redirects=False)

    def test_security_headers_present_on_standard_response(self):
        """DoD: All API responses carry OWASP security headers per Section 33."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # Verify OWASP Security Headers
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(response.headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertEqual(response.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("default-src 'self'", response.headers.get("Content-Security-Policy", ""))
        self.assertIn("frame-ancestors 'none'", response.headers.get("Content-Security-Policy", ""))
        self.assertIn("camera=()", response.headers.get("Permissions-Policy", ""))

    def test_hsts_header_on_https_request(self):
        """DoD: HSTS header is emitted when request arrives over HTTPS."""
        response = self.client.get("/", headers={"X-Forwarded-Proto": "https"})
        self.assertEqual(response.status_code, 200)

        hsts = response.headers.get("Strict-Transport-Security")
        self.assertIsNotNone(hsts, "HSTS header must be present on HTTPS responses")
        self.assertIn("max-age=", hsts)
        self.assertIn("includeSubDomains", hsts)

    def test_plain_http_redirected_when_https_enforced(self):
        """DoD: Plain HTTP is redirected to HTTPS in production/enforced configuration."""
        with patch.dict(os.environ, {"ENFORCE_HTTPS": "true"}):
            self.assertTrue(is_https_enforced())

            # Plain HTTP request (no https scheme / no X-Forwarded-Proto: https)
            response = self.client.get("/", headers={"X-Forwarded-Proto": "http"})
            self.assertEqual(response.status_code, 307, "Plain HTTP must be redirected with HTTP 307")
            self.assertTrue(response.headers["Location"].startswith("https://"))

            # HTTPS request under ENFORCE_HTTPS succeeds
            https_response = self.client.get("/", headers={"X-Forwarded-Proto": "https"})
            self.assertEqual(https_response.status_code, 200)
            self.assertIn("Strict-Transport-Security", https_response.headers)

    def test_production_environment_auto_enforces_https(self):
        """DoD: ENVIRONMENT=production automatically activates HTTPS enforcement."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "ENFORCE_HTTPS": ""}):
            self.assertTrue(is_https_enforced())

            response = self.client.get("/", headers={"X-Forwarded-Proto": "http"})
            self.assertEqual(response.status_code, 307)
            self.assertTrue(response.headers["Location"].startswith("https://"))

    def test_plain_http_allowed_in_dev_mode(self):
        """In local development (ENFORCE_HTTPS=false), plain HTTP requests are accepted directly."""
        with patch.dict(os.environ, {"ENFORCE_HTTPS": "false", "ENVIRONMENT": "development"}):
            self.assertFalse(is_https_enforced())

            response = self.client.get("/")
            self.assertEqual(response.status_code, 200)

    def test_secure_auth_cookie_flags_in_production(self):
        """DoD: Auth cookies marked Secure and HttpOnly in production/HTTPS config."""
        with patch.dict(os.environ, {"ENFORCE_HTTPS": "true"}):
            self.assertTrue(is_cookie_secure())

            response = Response()
            set_secure_auth_cookie(response, key="dfss_session", value="mock_session_token_123")

            # Verify Set-Cookie header contains required security flags
            cookie_header = response.headers.get("set-cookie", "")
            self.assertIn("dfss_session=mock_session_token_123", cookie_header)
            self.assertIn("HttpOnly", cookie_header)
            self.assertIn("Secure", cookie_header)
            self.assertIn("SameSite=lax", cookie_header)

    def test_auth_cookie_flags_in_development(self):
        """In development mode without COOKIE_SECURE override, HttpOnly is still enforced."""
        with patch.dict(os.environ, {"ENFORCE_HTTPS": "false", "COOKIE_SECURE": "false", "ENVIRONMENT": "development"}):
            self.assertFalse(is_cookie_secure())

            response = Response()
            set_secure_auth_cookie(response, key="dfss_session", value="mock_session_token_dev")

            cookie_header = response.headers.get("set-cookie", "")
            self.assertIn("HttpOnly", cookie_header)
            self.assertIn("SameSite=lax", cookie_header)
            self.assertNotIn("Secure", cookie_header)


if __name__ == "__main__":
    unittest.main(verbosity=2)
