"""
security_headers.py
===================
Security Headers & HTTPS Enforcement Middleware for DFSS per Section 33:
- Injects standard OWASP secure HTTP headers on all API responses.
- Injects HTTP Strict Transport Security (HSTS) when operating over TLS/HTTPS.
- Enforces HTTPS redirection or rejection of plain HTTP requests in production.
- Provides secure cookie utility enforcing HttpOnly, Secure, and SameSite flags.
"""

from typing import Optional
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.models.config import get_hsts_max_age, is_cookie_secure, is_https_enforced


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware applying Section 33 security headers and HTTPS/TLS enforcement.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Enforce HTTPS/TLS in production or when ENFORCE_HTTPS is active
        if is_https_enforced():
            is_https = (
                request.url.scheme == "https"
                or request.headers.get("x-forwarded-proto", "").lower() == "https"
                or request.headers.get("x-forwarded-ssl", "").lower() == "on"
            )

            if not is_https:
                # Redirect plain HTTP to HTTPS with status 307 (preserves HTTP method & body)
                https_url = str(request.url).replace("http://", "https://", 1)
                return RedirectResponse(
                    url=https_url,
                    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                    headers={
                        "Location": https_url,
                        "X-Content-Type-Options": "nosniff",
                    },
                )

        # 2. Process downstream request
        response = await call_next(request)

        # 3. Inject OWASP and Section 33 security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline';"
        )
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )

        # 4. Inject HSTS header if request is HTTPS or HTTPS is enforced
        if (
            is_https_enforced()
            or request.url.scheme == "https"
            or request.headers.get("x-forwarded-proto", "").lower() == "https"
        ):
            max_age = get_hsts_max_age()
            response.headers["Strict-Transport-Security"] = f"max-age={max_age}; includeSubDomains; preload"

        return response


def set_secure_auth_cookie(
    response: Response,
    key: str,
    value: str,
    max_age: Optional[int] = None,
    path: str = "/",
    domain: Optional[str] = None,
) -> None:
    """
    Sets an authentication cookie strictly marked HttpOnly, SameSite=Lax, and Secure
    (when operating over HTTPS / production) per Section 33.
    """
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        path=path,
        domain=domain,
        secure=is_cookie_secure(),
        httponly=True,
        samesite="lax",
    )
