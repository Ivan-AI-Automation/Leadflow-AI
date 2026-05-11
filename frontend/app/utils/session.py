from __future__ import annotations

from typing import Any

import streamlit as st

from app.services.api_client import (
    ACCESS_TOKEN_SESSION_KEY,
    CURRENT_USER_SESSION_KEY,
    clear_access_token,
    get_access_token,
    get_current_user_from_session,
)

AUTH_ERROR_SESSION_KEY = "auth_error"


def initialize_session_state() -> None:
    st.session_state.setdefault(ACCESS_TOKEN_SESSION_KEY, None)
    st.session_state.setdefault(CURRENT_USER_SESSION_KEY, None)
    st.session_state.setdefault(AUTH_ERROR_SESSION_KEY, None)


def is_authenticated() -> bool:
    return bool(get_access_token())


def current_user() -> dict[str, Any] | None:
    return get_current_user_from_session()


def current_user_email() -> str:
    user = current_user()
    if not user:
        return "Not signed in"
    return str(user.get("email") or "Unknown user")


def set_auth_error(message: str | None) -> None:
    st.session_state[AUTH_ERROR_SESSION_KEY] = message


def get_auth_error() -> str | None:
    error = st.session_state.get(AUTH_ERROR_SESSION_KEY)
    return str(error) if error else None


def logout() -> None:
    clear_access_token()
    set_auth_error(None)


def redirect_to_login() -> None:
    st.switch_page("pages/login.py")


def redirect_to_dashboard() -> None:
    st.switch_page("app/main.py")


def require_authentication() -> None:
    initialize_session_state()
    if not is_authenticated():
        redirect_to_login()
