import os
import tempfile
from pathlib import Path

os.environ["DUALMIND_TOKEN"] = "testing-secret-token-32-chars-long"
os.environ["DUALMIND_DB"] = str(Path(tempfile.mkdtemp()) / "test.sqlite3")

from fastapi.testclient import TestClient
from app import main

client = TestClient(main.app)
HEADERS = {"Authorization": "Bearer testing-secret-token-32-chars-long"}


def test_auth_and_rooms():
    assert client.get("/health").status_code == 200
    assert client.get("/rooms").status_code == 401
    created = client.post("/rooms", headers=HEADERS, json={"name": "Test"}).json()
    rid = created["id"]
    assert any(r["id"] == rid for r in client.get("/rooms", headers=HEADERS).json())
    assert client.post(f"/rooms/{rid}/messages", headers=HEADERS, json={"role": "system", "content": "bad"}).status_code == 422
    assert client.post(f"/rooms/{rid}/messages", headers=HEADERS, json={"role": "user", "content": "hello"}).status_code == 200
    assert client.get(f"/rooms/{rid}/messages", headers=HEADERS).json()[0]["content"] == "hello"
    assert client.put(f"/rooms/{rid}/notes/goal", headers=HEADERS, json={"value": "ship"}).status_code == 200
    assert client.get(f"/rooms/{rid}/notes", headers=HEADERS).json()["goal"] == "ship"


def test_legacy_collaboration_requires_explicit_new_contract():
    assert client.post('/rooms/x/collaborate',headers=HEADERS,json={'prompt':'test'}).status_code == 410
