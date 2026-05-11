from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
import app.models as _models  # noqa: F401


FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=engine)

    settings = get_settings()
    original_upload_dir = settings.upload_dir
    original_max_upload_size_mb = settings.max_upload_size_mb
    settings.upload_dir = tmp_path / "uploads"
    settings.max_upload_size_mb = 1

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    settings.upload_dir = original_upload_dir
    settings.max_upload_size_mb = original_max_upload_size_mb
    Base.metadata.drop_all(bind=engine)


def auth_header(client: TestClient, email: str = "owner@example.com") -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )
    token = response.json()["token"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_upload_csv_creates_import_metadata(client: TestClient) -> None:
    headers = auth_header(client)
    sample_file = FIXTURE_DIR / "sample_leads.csv"

    with sample_file.open("rb") as file_handle:
        response = client.post(
            "/api/v1/imports/upload",
            headers=headers,
            files={"file": ("sample_leads.csv", file_handle, "text/csv")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["original_filename"] == "sample_leads.csv"
    assert payload["file_type"] == "csv"
    assert payload["rows_count"] == 2
    assert payload["columns_count"] == 7
    assert payload["columns_json"] == [
        "first_name",
        "last_name",
        "company_name",
        "email",
        "phone",
        "source",
        "interest_level",
    ]
    assert "email" in payload["dtypes_json"]
    assert payload["status"] == "uploaded"

    settings = get_settings()
    assert (settings.upload_dir / payload["stored_filename"]).exists()


def test_upload_rejects_unsupported_file_format(client: TestClient) -> None:
    headers = auth_header(client)

    response = client.post(
        "/api/v1/imports/upload",
        headers=headers,
        files={"file": ("leads.txt", b"not,a,supported,file", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_upload_rejects_file_over_size_limit(client: TestClient) -> None:
    headers = auth_header(client)
    get_settings().max_upload_size_mb = 0

    response = client.post(
        "/api/v1/imports/upload",
        headers=headers,
        files={"file": ("leads.csv", b"first_name,email\nMaya,maya@example.com\n", "text/csv")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_user_can_access_only_their_own_imports(client: TestClient) -> None:
    owner_headers = auth_header(client, "owner@example.com")
    other_headers = auth_header(client, "other@example.com")
    sample_file = FIXTURE_DIR / "sample_leads.csv"

    with sample_file.open("rb") as file_handle:
        upload_response = client.post(
            "/api/v1/imports/upload",
            headers=owner_headers,
            files={"file": ("sample_leads.csv", file_handle, "text/csv")},
        )

    import_id = upload_response.json()["id"]

    owner_response = client.get(f"/api/v1/imports/{import_id}", headers=owner_headers)
    other_response = client.get(f"/api/v1/imports/{import_id}", headers=other_headers)

    assert owner_response.status_code == 200
    assert other_response.status_code == 404


def test_delete_import_removes_metadata_and_file(client: TestClient) -> None:
    headers = auth_header(client)
    sample_file = FIXTURE_DIR / "sample_leads.csv"

    with sample_file.open("rb") as file_handle:
        upload_response = client.post(
            "/api/v1/imports/upload",
            headers=headers,
            files={"file": ("sample_leads.csv", file_handle, "text/csv")},
        )

    payload = upload_response.json()
    import_id = payload["id"]
    stored_path = get_settings().upload_dir / payload["stored_filename"]
    assert stored_path.exists()

    delete_response = client.delete(f"/api/v1/imports/{import_id}", headers=headers)
    get_response = client.get(f"/api/v1/imports/{import_id}", headers=headers)

    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Lead import deleted successfully."
    assert get_response.status_code == 404
    assert not stored_path.exists()
