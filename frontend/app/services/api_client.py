from __future__ import annotations

from dataclasses import dataclass
from typing import Any, BinaryIO

import requests
import streamlit as st

from app.config import get_config

ACCESS_TOKEN_SESSION_KEY = "access_token"
CURRENT_USER_SESSION_KEY = "current_user"


@dataclass
class DownloadedFile:
    content: bytes
    filename: str
    content_type: str


class APIClientError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str = "api_client_error",
        details: Any | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        super().__init__(message)


class APIClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: int | None = None) -> None:
        config = get_config()
        self.base_url = (base_url or config.api_base_url).rstrip("/")
        self.timeout_seconds = timeout_seconds or config.request_timeout_seconds

    def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        return self.request("GET", path, params=params, authenticated=authenticated)

    def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        return self.request(
            "POST",
            path,
            json=json,
            data=data,
            files=files,
            authenticated=authenticated,
        )

    def patch(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        return self.request("PATCH", path, json=json, authenticated=authenticated)

    def delete(self, path: str, *, authenticated: bool = True) -> Any:
        return self.request("DELETE", path, authenticated=authenticated)

    def download(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> DownloadedFile:
        response = self._send_request(
            "GET",
            path,
            params=params,
            authenticated=authenticated,
        )
        filename = self._filename_from_response(response) or "leadflow_export"
        return DownloadedFile(
            content=response.content,
            filename=filename,
            content_type=response.headers.get("content-type", "application/octet-stream"),
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        response = self._send_request(
            method,
            path,
            params=params,
            json=json,
            data=data,
            files=files,
            authenticated=authenticated,
        )

        if response.status_code == 204:
            return None

        if not response.content:
            return None

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()

        return response.text

    def _send_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> requests.Response:
        url = self._url(path)
        headers = self._headers(authenticated=authenticated)

        try:
            response = requests.request(
                method,
                url,
                params=self._clean_params(params),
                json=json,
                data=data,
                files=files,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise APIClientError(
                "Could not connect to the LeadFlow AI API. Please check that the backend is running.",
                code="connection_error",
            ) from exc

        if response.status_code >= 400:
            self._raise_for_api_error(response)

        return response

    def _url(self, path: str) -> str:
        normalized_path = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{normalized_path}"

    def _headers(self, *, authenticated: bool) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if authenticated:
            token = get_access_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
        return headers

    @staticmethod
    def _clean_params(params: dict[str, Any] | None) -> dict[str, Any] | None:
        if not params:
            return None
        return {key: value for key, value in params.items() if value is not None}

    @staticmethod
    def _raise_for_api_error(response: requests.Response) -> None:
        try:
            payload = response.json()
        except ValueError:
            raise APIClientError(
                "The API returned an unexpected error response.",
                status_code=response.status_code,
                code="unexpected_api_error",
            )

        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            message = str(error.get("message") or "The API request failed.")
            code = str(error.get("code") or "api_error")
            details = error.get("details")
        else:
            message = (
                str(payload.get("detail") or "The API request failed.")
                if isinstance(payload, dict)
                else "The API request failed."
            )
            code = "api_error"
            details = payload

        raise APIClientError(
            message,
            status_code=response.status_code,
            code=code,
            details=details,
        )

    @staticmethod
    def _filename_from_response(response: requests.Response) -> str | None:
        content_disposition = response.headers.get("content-disposition", "")
        parts = [part.strip() for part in content_disposition.split(";")]
        for part in parts:
            if part.startswith("filename="):
                return part.removeprefix("filename=").strip('"')
        return None


def get_access_token() -> str | None:
    token = st.session_state.get(ACCESS_TOKEN_SESSION_KEY)
    return str(token) if token else None


def set_access_token(token: str) -> None:
    st.session_state[ACCESS_TOKEN_SESSION_KEY] = token


def clear_access_token() -> None:
    st.session_state.pop(ACCESS_TOKEN_SESSION_KEY, None)
    st.session_state.pop(CURRENT_USER_SESSION_KEY, None)


def set_current_user(user: dict[str, Any]) -> None:
    st.session_state[CURRENT_USER_SESSION_KEY] = user


def get_current_user_from_session() -> dict[str, Any] | None:
    user = st.session_state.get(CURRENT_USER_SESSION_KEY)
    return user if isinstance(user, dict) else None


def make_upload_file(file: BinaryIO, *, filename: str, content_type: str | None = None) -> tuple[str, BinaryIO, str]:
    return (filename, file, content_type or "application/octet-stream")


api_client = APIClient()
