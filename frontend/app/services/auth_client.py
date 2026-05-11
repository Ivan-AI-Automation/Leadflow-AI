from __future__ import annotations

from typing import Any

from app.services.api_client import api_client, set_access_token, set_current_user


def register(email: str, password: str) -> dict[str, Any]:
    payload = api_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
        },
        authenticated=False,
    )
    token = payload.get("token", {}).get("access_token")
    user = payload.get("user")
    if token:
        set_access_token(token)
    if isinstance(user, dict):
        set_current_user(user)
    return payload


def login(email: str, password: str) -> dict[str, Any]:
    payload = api_client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
        authenticated=False,
    )
    token = payload.get("access_token")
    if token:
        set_access_token(token)
        current_user = get_current_user()
        set_current_user(current_user)
    return payload


def get_current_user() -> dict[str, Any]:
    user = api_client.get("/api/v1/auth/me")
    set_current_user(user)
    return user
