import json
import os
import zipfile
from io import BytesIO
from uuid import uuid4

os.environ["DATABASE_URL"] = f"sqlite:///./test_{uuid4().hex}.db"
os.environ["LOCAL_ONLY_MODE"] = "true"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from app import models, schema_upgrades
from app.db import SessionLocal
from app.main import app
from app.routes import settings as settings_routes

client = TestClient(app)


def create_transcription_model(model_id: str, name: str, available: bool = True, local_path: str | None = None):
    return {
        "id": model_id,
        "name": name,
        "repo_id": model_id,
        "description": f"{name} model",
        "languages": "Multiple languages",
        "available": available,
        "local_path": local_path,
    }


def test_auth_flow():
    response = client.post("/auth/signup", json={"email": "test@example.com", "password": "secret123"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token

    response = client.post("/auth/login", json={"email": "test@example.com", "password": "secret123"})
    assert response.status_code == 200


def test_transcription_settings_endpoint(monkeypatch):
    monkeypatch.setattr(settings_routes.transcription, "get_default_transcription_backend", lambda: "mlx_audio")
    monkeypatch.setattr(
        settings_routes.transcription,
        "get_transcription_backends",
        lambda: [
            {
                "id": "server",
                "label": "Built-in Server",
                "supported": True,
                "live": True,
                "detail": "Server path",
                "models": [
                    create_transcription_model("openai/whisper-small", "Whisper Small", available=False),
                    create_transcription_model("openai/whisper-medium", "Whisper Medium", available=True),
                ],
                "default_model": "openai/whisper-small",
            },
            {
                "id": "mlx_audio",
                "label": "MLX Audio",
                "supported": True,
                "live": True,
                "detail": "Apple Silicon local ASR.",
                "models": [
                    create_transcription_model(
                        "mlx-community/parakeet-tdt-0.6b-v3",
                        "Parakeet",
                        local_path="/tmp/models/parakeet",
                    )
                ],
                "default_model": "mlx-community/parakeet-tdt-0.6b-v3",
            },
        ],
    )
    monkeypatch.setattr(
        settings_routes,
        "get_all_engine_statuses",
        lambda: [
            {
                "id": "ollama",
                "label": "Ollama",
                "base_url": "http://127.0.0.1:11434",
                "live": True,
                "detail": "Connected",
                "available_models": ["qwen3-asr"],
            }
        ],
    )
    response = client.post("/auth/login", json={"email": "admin", "password": "admin"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/settings/transcription", headers=headers)
    assert response.status_code == 200
    assert response.json()["default_backend"] == "mlx_audio"
    assert response.json()["backends"][1]["id"] == "mlx_audio"
    assert response.json()["backends"][1]["models"][0]["id"] == "mlx-community/parakeet-tdt-0.6b-v3"
    assert response.json()["backends"][1]["models"][0]["available"] is True
    assert response.json()["text_inference_engines"][0]["id"] == "ollama"


def test_transcription_settings_endpoint_marks_unsupported_mlx_audio(monkeypatch):
    monkeypatch.setattr(settings_routes.transcription, "get_default_transcription_backend", lambda: "server")
    monkeypatch.setattr(
        settings_routes.transcription,
        "get_transcription_backends",
        lambda: [
            {
                "id": "server",
                "label": "Built-in Server",
                "supported": True,
                "live": True,
                "detail": "Server path",
                "models": [create_transcription_model("openai/whisper-small", "Whisper Small", available=False)],
                "default_model": "openai/whisper-small",
            },
            {
                "id": "mlx_audio",
                "label": "MLX Audio",
                "supported": False,
                "live": False,
                "detail": "MLX Audio requires macOS on Apple Silicon.",
                "models": [create_transcription_model("mlx-community/parakeet-tdt-0.6b-v3", "Parakeet", available=False)],
                "default_model": None,
            },
        ],
    )
    monkeypatch.setattr(settings_routes, "get_all_engine_statuses", lambda: [])
    response = client.post("/auth/login", json={"email": "admin", "password": "admin"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/settings/transcription", headers=headers)
    assert response.status_code == 200
    assert response.json()["default_backend"] == "server"
    assert response.json()["backends"][1]["supported"] is False
    assert response.json()["backends"][1]["models"][0]["available"] is False


def test_transcription_model_download_endpoint(monkeypatch):
    monkeypatch.setattr(
        settings_routes.transcription,
        "download_transcription_model",
        lambda backend_id, model_id: create_transcription_model(
            model_id,
            "Parakeet",
            available=True,
            local_path="/tmp/models/parakeet",
        ),
    )
    response = client.post("/auth/login", json={"email": "admin", "password": "admin"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/settings/transcription/models/download",
        json={"backend": "mlx_audio", "model": "mlx-community/parakeet-tdt-0.6b-v3"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == "mlx-community/parakeet-tdt-0.6b-v3"
    assert response.json()["available"] is True
    assert response.json()["local_path"] == "/tmp/models/parakeet"


def test_local_inference_check_endpoint(monkeypatch):
    monkeypatch.setattr(
        settings_routes,
        "check_engine",
        lambda engine_id, base_url=None: {
            "id": engine_id,
            "label": "LM Studio",
            "base_url": base_url or "http://127.0.0.1:1234/v1",
            "live": True,
            "detail": "Connected",
            "available_models": ["mistralai/Voxtral-Mini-4B-Realtime-2602"],
        },
    )
    response = client.post("/auth/login", json={"email": "admin", "password": "admin"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/settings/local-inference/check",
        json={"engine_id": "lmstudio", "base_url": "http://localhost:1234/v1"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["live"] is True
    assert response.json()["available_models"] == ["mistralai/Voxtral-Mini-4B-Realtime-2602"]


def test_session_create_and_upload():
    response = client.post("/auth/login", json={"email": "admin", "password": "admin"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "title": "Test",
        "mode": "Interview",
        "duration_ms": 1000,
        "wpm_avg": 120,
        "filler_count": 0,
        "eye_contact_pct": 0.8,
        "tags": ["demo"],
        "transcript_segments": [{"start_ms": 0, "end_ms": 1000, "text": "Hello"}],
        "metrics": [{"t": 0, "wpm": 120, "rms": 50, "eye_contact": 0.8, "smile": 0.3, "yaw": 0.1, "pitch": 0.2, "roll": 0.1, "filler_count": 0, "pause_ms": 800}],
    }
    response = client.post("/sessions", json=payload, headers=headers)
    assert response.status_code == 200
    session_id = response.json()["id"]

    video_data = BytesIO(b"\x00\x01\x02")
    files = {"file": ("test.webm", video_data, "video/webm")}
    response = client.post(f"/sessions/{session_id}/upload", files=files, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "complete"

    response = client.get("/sessions", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_export_includes_recording_file():
    response = client.post("/auth/login", json={"email": "admin", "password": "admin"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "title": "Export",
        "mode": "Interview",
        "duration_ms": 1000,
        "transcript_segments": [{"start_ms": 0, "end_ms": 1000, "text": "Hello"}],
        "metrics": [],
    }
    response = client.post("/sessions", json=payload, headers=headers)
    session_id = response.json()["id"]

    files = {"file": ("test.webm", BytesIO(b"\x1a\x45\xdf\xa3webm-data"), "video/webm")}
    upload_response = client.post(f"/sessions/{session_id}/upload", files=files, headers=headers)
    assert upload_response.status_code == 200

    export_response = client.get(f"/sessions/{session_id}/export", headers=headers)
    assert export_response.status_code == 200
    with zipfile.ZipFile(BytesIO(export_response.content)) as archive:
        assert "recording.webm" in archive.namelist()
        assert "transcript.txt" in archive.namelist()
        assert "transcript.pdf" in archive.namelist()


def test_transcript_download_formats():
    response = client.post("/auth/login", json={"email": "admin", "password": "admin"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "title": "Transcript Download",
        "mode": "Upload",
        "duration_ms": 61000,
        "transcript_segments": [
            {"start_ms": 0, "end_ms": 1000, "text": "Hello world"},
            {"start_ms": 1000, "end_ms": 2000, "text": "This is a transcript"},
        ],
        "metrics": [],
    }
    response = client.post("/sessions", json=payload, headers=headers)
    session_id = response.json()["id"]

    db_response = client.get(f"/sessions/{session_id}", headers=headers)
    assert db_response.status_code == 200

    txt_response = client.get(f"/sessions/{session_id}/transcript.txt", headers=headers)
    assert txt_response.status_code == 200
    assert txt_response.headers["content-type"].startswith("text/plain")
    assert "Hello world" in txt_response.text

    pdf_response = client.get(f"/sessions/{session_id}/transcript.pdf", headers=headers)
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")


def test_delete_video_keeps_session_transcript():
    response = client.post("/auth/login", json={"email": "admin", "password": "admin"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "title": "Delete Video",
        "mode": "Upload",
        "duration_ms": 5000,
        "transcript_segments": [{"start_ms": 0, "end_ms": 1000, "text": "Keep transcript"}],
        "metrics": [],
    }
    response = client.post("/sessions", json=payload, headers=headers)
    session_id = response.json()["id"]

    files = {"file": ("test.webm", BytesIO(b"\x1a\x45\xdf\xa3webm-data"), "video/webm")}
    upload_response = client.post(f"/sessions/{session_id}/upload", files=files, headers=headers)
    assert upload_response.status_code == 200

    delete_response = client.delete(f"/sessions/{session_id}/video", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"
    assert delete_response.json()["transcription_status"] == "complete"

    session_response = client.get(f"/sessions/{session_id}", headers=headers)
    assert session_response.status_code == 200
    assert session_response.json()["video_path"] is None

    video_response = client.get(f"/sessions/{session_id}/video", headers=headers)
    assert video_response.status_code == 404

    txt_response = client.get(f"/sessions/{session_id}/transcript.txt", headers=headers)
    assert txt_response.status_code == 200
    assert "Keep transcript" in txt_response.text


def test_session_document_upload_round_trip_and_full_delete():
    response = client.post("/auth/login", json={"email": "admin", "password": "admin"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "title": "Document Session",
        "mode": "Interview",
        "duration_ms": 5000,
        "transcript_segments": [],
        "metrics": [],
    }
    response = client.post("/sessions", json=payload, headers=headers)
    session_id = response.json()["id"]

    document_blocks = [{"index": 0, "text": "Read this paragraph aloud."}]
    upload_response = client.post(
        f"/sessions/{session_id}/document",
        files={"file": ("script.txt", BytesIO(b"Read this paragraph aloud."), "text/plain")},
        data={"blocks_json": json.dumps(document_blocks)},
        headers=headers,
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["name"] == "script.txt"
    assert upload_response.json()["mime_type"] == "text/plain"

    session_response = client.get(f"/sessions/{session_id}", headers=headers)
    assert session_response.status_code == 200
    assert session_response.json()["document"]["name"] == "script.txt"
    assert session_response.json()["document"]["blocks"][0]["text"] == "Read this paragraph aloud."

    with SessionLocal() as db:
        stored = db.query(models.Session).filter(models.Session.id == session_id).first()
        assert stored is not None
        assert stored.document_path is not None
        document_path = stored.document_path
        assert os.path.exists(document_path)

    delete_response = client.delete(f"/sessions/{session_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"
    assert not os.path.exists(document_path)

    missing_response = client.get(f"/sessions/{session_id}", headers=headers)
    assert missing_response.status_code == 404


def test_document_upload_rejects_unsupported_types():
    response = client.post("/auth/login", json={"email": "admin", "password": "admin"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "title": "Unsupported Doc",
        "mode": "Interview",
        "duration_ms": 1000,
        "transcript_segments": [],
        "metrics": [],
    }
    response = client.post("/sessions", json=payload, headers=headers)
    session_id = response.json()["id"]

    upload_response = client.post(
        f"/sessions/{session_id}/document",
        files={
            "file": (
                "script.docx",
                BytesIO(b"fake-docx"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        data={"blocks_json": json.dumps([{"index": 0, "text": "Unsupported"}])},
        headers=headers,
    )
    assert upload_response.status_code == 400
    assert "Unsupported document type" in upload_response.json()["detail"]


def test_schema_upgrade_adds_document_columns(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title VARCHAR(255),
                mode VARCHAR(80),
                prompt TEXT,
                goal VARCHAR(255),
                started_at DATETIME,
                ended_at DATETIME,
                duration_ms INTEGER,
                wpm_avg FLOAT,
                filler_count INTEGER,
                eye_contact_pct FLOAT,
                video_path VARCHAR(1024),
                transcription_status VARCHAR(32),
                created_at DATETIME
            )
            """
        )

    monkeypatch.setattr(schema_upgrades, "engine", engine)
    schema_upgrades.apply_startup_schema_upgrades()

    columns = {column["name"] for column in inspect(engine).get_columns("sessions")}
    assert {"document_path", "document_name", "document_mime_type", "document_blocks_json"}.issubset(columns)
