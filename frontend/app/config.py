from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class FrontendConfig:
    api_base_url: str
    request_timeout_seconds: int = 30


@lru_cache
def get_config() -> FrontendConfig:
    api_base_url = os.getenv(
        "LEADFLOW_API_BASE_URL",
        os.getenv("BACKEND_API_URL", "http://localhost:8000"),
    ).rstrip("/")
    timeout = int(os.getenv("LEADFLOW_API_TIMEOUT_SECONDS", "30"))

    return FrontendConfig(
        api_base_url=api_base_url,
        request_timeout_seconds=timeout,
    )
