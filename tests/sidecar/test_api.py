"""Tests for api."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus" / "out"
TOKEN = "0" * 64


@pytest.fixture(scope="module", autouse=True)
def corpus() -> None:
    if not (CORPUS / "rechnung_din5008.pdf").exists():
        subprocess.run(
            [sys.executable, str(ROOT / "corpus" / "generate.py")],
            check=True, capture_output=True,
        )


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory):
    data = tmp_path_factory.mktemp("appdata")
    previous_environment = dict(os.environ)
    os.environ.update(
        {
            "SUBSTRAKT_TOKEN": TOKEN,
            "SUBSTRAKT_MODE": "airgap",
            "SUBSTRAKT_DATA_DIR": str(data),
            "SUBSTRAKT_ROOTS": str(CORPUS),
        }
    )
    os.environ.pop("SUBSTRAKT_DEV", None)

    import substrakt.app as app_module

    importlib.reload(app_module)

    # `test_non_local_request_is_rejected` creates its own client.
    with TestClient(app_module.app, client=("127.0.0.1", 51234)) as c:
        yield c

    os.environ.clear()
    os.environ.update(previous_environment)
    importlib.reload(app_module)


def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


# --- Security -----------------------------------------------------------


def test_health_does_not_require_token(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "airgap"


def test_access_without_token_is_denied(client: TestClient) -> None:
    response = client.post("/documents", json={"path": str(CORPUS / "rechnung_din5008.pdf")})
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith("not-authorized")


def test_access_with_wrong_token_is_denied(client: TestClient) -> None:
    response = client.post(
        "/documents",
        json={"path": str(CORPUS / "rechnung_din5008.pdf")},
        headers={"Authorization": "Bearer " + "f" * 64},
    )
    assert response.status_code == 401


def test_non_local_request_is_rejected(tmp_path: Path) -> None:
    import substrakt.app as app_module

    with TestClient(app_module.app, client=("10.0.0.5", 40000)) as unknown:
        response = unknown.get("/health")

    assert response.status_code == 403
    assert response.json()["type"].endswith("not-local")


def test_path_outside_read_roots_is_rejected(client: TestClient) -> None:
    response = client.post("/documents", json={"path": "/etc/passwd"}, headers=auth())
    assert response.status_code == 403
    assert response.json()["type"].endswith("path-not-allowed")
    
    assert "/etc/passwd" not in response.text


# --- Documents -------------------------------------------------------------


@pytest.fixture
def doc_id(client: TestClient) -> str:
    response = client.post(
        "/documents",
        json={"path": str(CORPUS / "rechnung_din5008.pdf")},
        headers=auth(),
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_loading_document_omits_word_index(client: TestClient, doc_id: str) -> None:
    response = client.get(f"/documents/{doc_id}", headers=auth())
    data = response.json()

    assert response.status_code == 200
    assert "words" not in data
    assert data["kind"] == "pdf"
    assert data["meta"]["word_count"] > 0
    assert len(data["pages"]) == 1


def test_page_words(client: TestClient, doc_id: str) -> None:
    response = client.get(f"/documents/{doc_id}/pages/0/words", headers=auth())
    assert response.status_code == 200

    words = response.json()["words"]
    assert len(words) > 40

    first = words[0]
    assert first["locator"]["kind"] == "pdf_rect"
    assert first["locator"]["x0"] >= 0
    assert first["confidence"] is None, "The text layer is exact, not an estimate"


def test_page_out_of_range(client: TestClient, doc_id: str) -> None:
    response = client.get(f"/documents/{doc_id}/pages/99/words", headers=auth())
    assert response.status_code == 404
    assert response.json()["type"].endswith("page-not-found")


def test_plain_text(client: TestClient, doc_id: str) -> None:
    response = client.get(f"/documents/{doc_id}/text", headers=auth())
    data = response.json()

    assert response.status_code == 200
    assert data["text_source"] == "text_layer"
    assert "2026-0147" in data["chunks"][0]["text"]


def test_render_page_returns_png(client: TestClient, doc_id: str) -> None:
    response = client.get(f"/documents/{doc_id}/pages/0/render?scale=1", headers=auth())
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_document_bytes(client: TestClient, doc_id: str) -> None:
    response = client.get(f"/documents/{doc_id}/file", headers=auth())
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")

    missing = client.get("/documents/gibtsnicht/file", headers=auth())
    assert missing.status_code == 404


def test_unknown_document(client: TestClient) -> None:
    response = client.get("/documents/abc123/text", headers=auth())
    assert response.status_code == 404
    assert response.json()["type"].endswith("unknown-document")


# --- Spreadsheets --------------------------------------------------------------


def test_sheets_and_raster(client: TestClient) -> None:
    loaded = client.post(
        "/documents", json={"path": str(CORPUS / "positionen.xlsx")}, headers=auth()
    )
    assert loaded.status_code == 200
    doc_id = loaded.json()["id"]

    sheets = client.get(f"/documents/{doc_id}/sheets", headers=auth()).json()
    assert len(sheets) == 3
    assert sheets[0]["name"] == "Positionen"
    assert sheets[0]["columns"] <= 10, "Padded columns were not removed"

    raster = client.get(f"/documents/{doc_id}/sheets/0/raster", headers=auth()).json()
    assert raster["name"] == "Positionen"
    assert any("Bezeichnung" in cell for row in raster["rows"] for cell in row)





def test_corrupt_pdf_returns_problem_json(client: TestClient) -> None:
    response = client.post(
        "/documents", json={"path": str(CORPUS / "defekt.pdf")}, headers=auth()
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")

    data = response.json()
    assert data["type"].endswith("document-corrupt")
    assert data["title"]
    
    assert "Traceback" not in response.text
    assert "File \"" not in response.text


def test_empty_file(client: TestClient) -> None:
    response = client.post(
        "/documents", json={"path": str(CORPUS / "leer.csv")}, headers=auth()
    )
    assert response.status_code == 422
    assert response.json()["type"].endswith("document-empty")


def test_missing_file(client: TestClient) -> None:
    response = client.post(
        "/documents", json={"path": str(CORPUS / "does-not-exist.pdf")}, headers=auth()
    )
    assert response.status_code in (403, 404)


# --- OpenAPI ---------------------------------------------------------------


def test_sample_fields_come_from_document_kind(client: TestClient) -> None:
    response = client.get("/sample-fields", headers=auth())
    assert response.status_code == 200
    fields = {f["name"]: f for f in response.json()}
    assert fields["document_number"]["label_rule"]["value"] == "identifier"
    assert "Rechnungsnummer" in fields["document_number"]["label_rule"]["patterns"]


def test_invalid_custom_document_kind_returns_problem_json(client: TestClient) -> None:
    import substrakt.app as app_module

    custom = app_module.CONFIG.data_dir / "document_kinds"
    custom.mkdir(parents=True, exist_ok=True)
    file = custom / "invoice.yml"
    file.write_text(
        "name: invoice\ntitle: R\nfields:\n  - name: a\n    json_type: unsupported\n",
        encoding="utf-8",
    )
    try:
        response = client.get("/sample-fields", headers=auth())
    finally:
        file.unlink()
    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    data = response.json()
    assert data["type"].endswith("document-kind-invalid")
    assert data["key"] == "document-kind-invalid"
    assert data["file"] == "invoice.yml"
    assert data["error"][0]["location"] == "fields.0.json_type"
    assert "Traceback" not in response.text


def test_openapi_covers_contract(client: TestClient) -> None:
    """Make every endpoint required by the desktop contract visible."""
    spec = client.get("/openapi.json").json()
    paths = set(spec["paths"])

    expected = {
        "/health",
        "/documents",
        "/documents/{doc_id}",
        "/documents/{doc_id}/pages/{page}/words",
        "/documents/{doc_id}/pages/{page}/render",
        "/documents/{doc_id}/text",
        "/documents/{doc_id}/file",
        "/documents/{doc_id}/sheets",
        "/documents/{doc_id}/sheets/{index}/raster",
        "/documents/{doc_id}/extract",
        "/documents/{doc_id}/export",
        "/sample-fields",
        "/document-types",
        "/document-types/{type_id}",
        "/shutdown",
    }
    assert expected <= paths, f"Missing endpoints: {expected - paths}"
