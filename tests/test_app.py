import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app("sqlite:///:memory:")
    return app.test_client()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_list(client):
    resp = client.post("/tickets", json={"title": "Printer on fire"})
    assert resp.status_code == 201
    assert resp.get_json()["status"] == "open"
    assert len(client.get("/tickets").get_json()) == 1


def test_title_required(client):
    assert client.post("/tickets", json={}).status_code == 400


def test_close_ticket(client):
    created = client.post("/tickets", json={"title": "VPN down"})
    ticket_id = created.get_json()["id"]
    resp = client.patch(f"/tickets/{ticket_id}/close")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "closed"


def test_close_missing_ticket(client):
    assert client.patch("/tickets/999/close").status_code == 404
