import os
import sys

# Ensure order-service directory is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["TESTING"] = "1"

import pytest
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from main import app, Base, engine, SessionLocal, Order, catalog_client

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

def test_create_order_insufficient_stock():
    with patch.object(catalog_client, 'reserve_stock', side_effect=HTTPException(status_code=409, detail="Insufficient inventory")):
        payload = {
            "user_id": 1,
            "items": [{"product_id": "p1", "quantity": 999, "price": 100.0}]
        }
        response = client.post("/api/orders", json=payload)
        assert response.status_code == 409
        assert "Insufficient inventory" in response.json()["detail"]
