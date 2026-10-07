import os
from pathlib import Path

import pytest

flask = pytest.importorskip("flask")
import app as app_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Isolate every Flask test from the user's real data.
    monkeypatch.setattr(app_module, "BASE_DIR", Path(tmp_path))
    app_module.app.config.update(TESTING=True, SECRET_KEY="test-secret")
    app_module.blockchain = app_module.Blockchain(str(tmp_path / "blockchain.json"))
    app_module.database = app_module.Database(str(tmp_path / "records.db"))
    with app_module.app.test_client() as client:
        yield client


def login(client):
    response = client.post("/login", data={"username": "admin", "password": "admin123"})
    assert response.status_code == 302


def add_record(client, certificate="CERT001", marks=85):
    return client.post(
        "/api/records",
        json={
            "certificate_id": certificate,
            "student_name": "Mahendra MN",
            "srn": "R25EJ064",
            "course": "BCA",
            "subject": "Python",
            "marks": marks,
        },
    )


def test_flow_create_verify_and_public_chain(client):
    login(client)
    response = add_record(client)
    assert response.status_code == 201
    data = response.get_json()
    assert data["block"]["index"] == 1
    assert len(data["block"]["hash"]) == 64

    verify = client.get("/api/records/CERT001")
    assert verify.status_code == 200
    payload = verify.get_json()
    assert payload["verified"] is True
    assert payload["record"]["marks"] == 85

    chain = client.get("/api/chain").get_json()
    assert chain["valid"] is True
    assert len(chain["chain"]) == 2


def test_duplicate_and_invalid_marks_are_rejected(client):
    login(client)
    assert add_record(client).status_code == 201
    assert add_record(client).status_code == 409
    assert add_record(client, "CERT002", 101).status_code == 400
    assert add_record(client, "CERT003", -1).status_code == 400
    assert add_record(client, "CERT004", "abc").status_code == 400


def test_legitimate_correction_creates_new_block_without_editing_original(client):
    login(client)
    assert add_record(client, "CERT001", 85).status_code == 201
    correction = client.post(
        "/api/records/CERT001/correct",
        json={"marks": 90, "reason": "Teacher correction"},
    )
    assert correction.status_code == 201
    assert correction.get_json()["block"]["record"]["type"] == "MARKS_CORRECTION"

    chain = client.get("/api/chain").get_json()
    assert chain["valid"] is True
    assert chain["chain"][1]["record"]["marks"] == 85
    assert chain["chain"][2]["record"]["marks"] == 90

    verify = client.get("/api/records/CERT001").get_json()
    assert verify["verified"] is True
    assert verify["record"]["marks"] == 90
    assert len(verify["corrections"]) == 1
    assert verify["corrections"][0]["previous_marks"] == 85
    assert verify["corrections"][0]["new_marks"] == 90


def test_tampering_is_detected_and_reset_restores_chain(client):
    login(client)
    assert add_record(client, "CERT001", 85).status_code == 201
    assert add_record(client, "CERT002", 92).status_code == 201

    attack = client.post("/api/tamper", json={"block_index": 1, "field": "marks", "value": 99})
    assert attack.status_code == 200
    assert attack.get_json()["valid"] is False
    assert any(e["type"] == "HASH_MISMATCH" for e in attack.get_json()["errors"])

    # No new normal record/correction may be added while integrity is broken.
    assert add_record(client, "CERT003", 77).status_code == 409
    assert client.post("/api/records/CERT001/correct", json={"marks": 90}).status_code == 409

    reset = client.post("/api/reset-demo")
    assert reset.status_code == 200
    assert reset.get_json()["valid"] is True

    verify = client.get("/api/records/CERT001").get_json()
    assert verify["verified"] is True
    assert verify["record"]["marks"] == 85


def test_authentication_and_protected_routes(client):
    assert client.get("/dashboard").status_code == 302
    assert client.post("/api/records", json={}).status_code == 401
    assert client.post("/login", data={"username": "admin", "password": "wrong"}).status_code == 200
    login(client)
    assert client.get("/dashboard").status_code == 200
    assert client.get("/blockchain").status_code == 200
