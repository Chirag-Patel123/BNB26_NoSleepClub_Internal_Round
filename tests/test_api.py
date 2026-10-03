from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_start_run():
    response = client.post("/runs", json={
        "scenario_id": "flight_basic",
        "seed": 42,
        "failure_type": "invalid_tool_output",
        "target_step": "step-5"
    })
    assert response.status_code == 200
    assert "run_id" in response.json()
    assert response.json()["status"] in ["running", "failure", "success"]
    assert response.json()["status"] == "failure"

def test_get_run():
    response = client.get("/runs/run-123")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == "run-123"
    assert "ordered_steps" in data
    assert len(data["ordered_steps"]) > 0
    assert data["ordered_steps"][0]["step_id"] == "step-5"

def test_get_diagnosis():
    response = client.get("/runs/run-123/diagnosis")
    assert response.status_code == 200
    data = response.json()
    assert len(data["ranked_steps"]) > 0
    assert data["ranked_steps"][0]["score"] == 0.91

def test_replay_run():
    response = client.post("/runs/run-123/replay", json={
        "checkpoint_id": "ckpt-5",
        "modification_type": "change_tool_result",
        "modification_payload": {
            "step_id": "step-5",
            "value": {"available": True}
        }
    })
    assert response.status_code == 200
    assert response.json()["alternative_run_id"] == "run-456"

def test_compare_runs():
    response = client.get("/runs/compare?original_id=run-123&alternative_id=run-456")
    assert response.status_code == 200
    data = response.json()
    assert data["original_run_id"] == "run-123"
    assert data["changed_steps"] == ["step-5"]
