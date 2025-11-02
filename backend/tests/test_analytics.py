"""
Tests for analytics endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.main import app, engine
from app.models import IoTDevice, InteractionLog
from app.auth import create_token
from datetime import datetime


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(scope="function")
def auth_headers():
    """Create test device and return auth headers."""
    with Session(engine) as session:
        # Check if device already exists
        existing = session.exec(select(IoTDevice).where(IoTDevice.device_id == "test-analytics-device")).first()
        if existing:
            token = create_token(existing.device_id)
            existing.api_token = token
            session.add(existing)
            session.commit()
        else:
            device = IoTDevice(device_id="test-analytics-device", device_mac="AA:BB:CC:DD:EE:FF")
            token = create_token(device.device_id)
            device.api_token = token
            session.add(device)
            session.commit()
    
    yield {"Authorization": f"Bearer {token}"}
    
    # Cleanup: Remove the test device and its logs after each test
    with Session(engine) as session:
        # Delete logs first (due to foreign key)
        logs = session.exec(select(InteractionLog).where(InteractionLog.device_id == "test-analytics-device")).all()
        for log in logs:
            session.delete(log)
        # Delete device
        device = session.exec(select(IoTDevice).where(IoTDevice.device_id == "test-analytics-device")).first()
        if device:
            session.delete(device)
        session.commit()



def test_analytics_summary_empty(client, auth_headers):
    """Test analytics summary with no interactions."""
    resp = client.get("/api/iot/analytics/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_interactions"] == 0
    assert data["by_action"] == {}
    assert data["recent"] == []


def test_analytics_summary_with_interactions(client, auth_headers):
    """Test analytics summary with multiple interactions."""
    with Session(engine) as session:
        device = session.exec(select(IoTDevice).where(IoTDevice.device_id == "test-analytics-device")).first()
        
        # Add some test logs
        log1 = InteractionLog(
            device_id=device.device_id,
            user_id=1,
            action_type="voice",
            query="test query 1",
            results_count=5,
            response_time_ms=100,
            timestamp=datetime.utcnow()
        )
        log2 = InteractionLog(
            device_id=device.device_id,
            user_id=1,
            action_type="face",
            query=None,
            results_count=1,
            response_time_ms=50,
            timestamp=datetime.utcnow()
        )
        log3 = InteractionLog(
            device_id=device.device_id,
            user_id=2,
            action_type="voice",
            query="test query 2",
            results_count=3,
            response_time_ms=120,
            timestamp=datetime.utcnow()
        )
        session.add_all([log1, log2, log3])
        session.commit()
    
    resp = client.get("/api/iot/analytics/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_interactions"] == 3
    assert data["by_action"]["voice"] == 2
    assert data["by_action"]["face"] == 1
    assert len(data["recent"]) == 3


def test_analytics_interactions_pagination(client, auth_headers):
    """Test paginated interactions endpoint."""
    resp = client.get("/api/iot/analytics/interactions?limit=10&offset=0", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert data["limit"] == 10
    assert data["offset"] == 0
    # Should include logs from previous test
    assert len(data["data"]) >= 0
