"""Tests for the FastAPI hello world endpoint."""

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_read_root_returns_hello_world() -> None:
    """GET / should respond with the hello world payload."""
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "hello world"}
