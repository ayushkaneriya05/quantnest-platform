"""Typed access to the authentication library's dynamic cookie settings."""
from typing import Protocol, cast

from dj_rest_auth.app_settings import api_settings


class CookieSettings(Protocol):
    JWT_AUTH_COOKIE: str
    JWT_AUTH_SECURE: bool
    JWT_AUTH_SAMESITE: str
    JWT_AUTH_COOKIE_DOMAIN: str | None
    JWT_AUTH_REFRESH_COOKIE_PATH: str


auth_settings = cast(CookieSettings, api_settings)
