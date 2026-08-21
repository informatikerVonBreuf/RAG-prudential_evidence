from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_describes_loaded_corpus() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["documents"] == 4
    assert payload["chunks"] >= 13


def test_documents_are_publicly_described() -> None:
    response = client.get("/api/documents")
    assert response.status_code == 200
    documents = response.json()
    assert any(document["status"] == "reviewed" for document in documents)
    assert all(document["source_url"].startswith("https://") for document in documents)
