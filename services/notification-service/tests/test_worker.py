import os
import sys

# Ensure notification-service directory is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from unittest.mock import MagicMock
import pytest
from main import callback, DLQ_QUEUE_NAME, PROCESSED_ORDERS, EMAIL_CHANNEL, WEBHOOK_CHANNEL

class MockMethod:
    delivery_tag = 101

def test_callback_successful_order():
    channel = MagicMock()
    method = MockMethod()
    properties = MagicMock()
    payload = json.dumps({"id": 123, "user_id": 45, "total_amount": 99.99}).encode('utf-8')

    callback(channel, method, properties, payload)

    channel.basic_ack.assert_called_once_with(delivery_tag=101)
    channel.basic_publish.assert_not_called()

def test_callback_deduplication():
    channel = MagicMock()
    method = MockMethod()
    properties = MagicMock()
    payload = json.dumps({"id": 999, "user_id": 1, "total_amount": 10.0}).encode('utf-8')

    # Initial processing
    callback(channel, method, properties, payload)
    assert 999 in PROCESSED_ORDERS
    assert channel.basic_ack.call_count == 1

    # Redelivered duplicate message
    callback(channel, method, properties, payload)
    # Acknowledged without double dispatch
    assert channel.basic_ack.call_count == 2

def test_callback_malformed_json_routes_to_dlq():
    channel = MagicMock()
    method = MockMethod()
    properties = MagicMock()
    bad_payload = b"invalid-non-json-binary-data"

    callback(channel, method, properties, bad_payload)

    # Verifies DLQ queue declaration and routing
    channel.queue_declare.assert_called_with(queue=DLQ_QUEUE_NAME, durable=True)
    channel.basic_publish.assert_called_once()
    args, kwargs = channel.basic_publish.call_args
    assert kwargs.get("routing_key") == DLQ_QUEUE_NAME

    # Original poison message acknowledged so consumer does not hang
    channel.basic_ack.assert_called_once_with(delivery_tag=101)

def test_health_server_handler():
    from main import HealthHandler
    from unittest.mock import patch
    import io

    handler = HealthHandler.__new__(HealthHandler)
    handler.path = '/health'
    handler.wfile = io.BytesIO()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    HealthHandler.do_GET(handler)

    handler.send_response.assert_called_once_with(200)
    data = json.loads(handler.wfile.getvalue().decode('utf-8'))
    assert data["status"] == "healthy"
    assert data["service"] == "notification-service"

def test_metrics_server_handler():
    from main import HealthHandler
    import io

    handler = HealthHandler.__new__(HealthHandler)
    handler.path = '/metrics'
    handler.wfile = io.BytesIO()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    HealthHandler.do_GET(handler)

    handler.send_response.assert_called_once_with(200)
    output = handler.wfile.getvalue().decode('utf-8')
    assert "notifications_processed_total" in output
