import os
os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient
from main import app, Base, engine, SessionLocal, Order

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200

def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "order-service"

def test_health_check_alias_endpoint():
    response = client.get("/api/orders/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_correlation_id_propagation():
    test_id = "test-order-trace-789"
    response = client.get("/metrics", headers={"X-Correlation-ID": test_id})
    assert response.headers.get("X-Correlation-ID") == test_id

def test_create_order_validation_empty_items():
    response = client.post("/api/orders", json={"user_id": 1, "items": []})
    assert response.status_code == 422

def test_create_order_validation_negative_price():
    response = client.post("/api/orders", json={
        "user_id": 1,
        "items": [{"product_id": "p1", "quantity": 1, "price": -50.0}]
    })
    assert response.status_code == 422

def test_create_order_success():
    payload = {
        "user_id": 42,
        "items": [
            {"product_id": "p1", "quantity": 2, "price": 100.0}
        ]
    }
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == 42
    assert data["total_amount"] == 200.0
    assert data["status"] == "PENDING"
