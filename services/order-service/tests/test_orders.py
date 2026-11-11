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

def test_create_order_idempotency():
    idem_key = "idemp-key-xyz-987"
    payload = {
        "user_id": 99,
        "items": [{"product_id": "p1", "quantity": 1, "price": 50.0}]
    }
    # First submission
    resp1 = client.post("/api/orders", json=payload, headers={"X-Idempotency-Key": idem_key})
    assert resp1.status_code == 201
    order1 = resp1.json()

    # Second submission with same idempotency key
    resp2 = client.post("/api/orders", json=payload, headers={"X-Idempotency-Key": idem_key})
    assert resp2.status_code == 200 or resp2.status_code == 201
    order2 = resp2.json()

    assert order1["id"] == order2["id"]
    assert order1["total_amount"] == order2["total_amount"]

def test_order_state_machine_valid_transition():
    # Create order in PENDING
    payload = {"user_id": 1, "items": [{"product_id": "p1", "quantity": 1, "price": 10.0}]}
    create_resp = client.post("/api/orders", json=payload)
    order_id = create_resp.json()["id"]

    # Transition to CONFIRMED
    patch_resp = client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "CONFIRMED"

def test_order_state_machine_invalid_transition():
    # Create order in PENDING
    payload = {"user_id": 1, "items": [{"product_id": "p1", "quantity": 1, "price": 10.0}]}
    create_resp = client.post("/api/orders", json=payload)
    order_id = create_resp.json()["id"]

    # Attempt illegal jump directly from PENDING to DELIVERED
    patch_resp = client.patch(f"/api/orders/{order_id}/status", json={"status": "DELIVERED"})
    assert patch_resp.status_code == 400
    assert "Invalid order status transition" in patch_resp.json()["detail"]
