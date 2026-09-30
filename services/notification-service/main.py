import time
import sys
import pika
import json

import os
import random
from datetime import datetime

DLQ_QUEUE_NAME = 'order_notifications_dlq'

def log_event(level, message, **kwargs):
    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "service": "notification-service",
        "message": message,
        **kwargs
    }
    print(json.dumps(payload), flush=True)

def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        order_id = data.get('id')
        user_id = data.get('user_id')
        log_event("info", f"Notification Received: Processing order #{order_id} for User #{user_id}", order_id=order_id, user_id=user_id)
        
        # Simulate processing notification (email/SMS)
        time.sleep(0.5)
        log_event("info", f"Notification Sent successfully for order #{order_id}", order_id=order_id)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        log_event("error", f"Error processing message: {str(e)}. Forwarding to DLQ.", error=str(e))
        try:
            # Route poison-pill or failed message to Dead Letter Queue
            ch.queue_declare(queue=DLQ_QUEUE_NAME, durable=True)
            dlq_payload = {
                "original_body": body.decode('utf-8') if isinstance(body, bytes) else str(body),
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat()
            }
            ch.basic_publish(
                exchange='',
                routing_key=DLQ_QUEUE_NAME,
                body=json.dumps(dlq_payload),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            log_event("warn", f"Message safely routed to Dead Letter Queue: {DLQ_QUEUE_NAME}")
        except Exception as dlq_err:
            log_event("error", f"Failed routing to DLQ: {dlq_err}")
        
        # Ack original queue so consumer is not blocked
        ch.basic_ack(delivery_tag=method.delivery_tag)

def connect_with_retry(rabbitmq_host, max_attempts=10):
    delay = 2
    for attempt in range(1, max_attempts + 1):
        try:
            log_event("info", f"Attempting to connect to RabbitMQ broker (attempt {attempt}/{max_attempts})...", host=rabbitmq_host)
            connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=rabbitmq_host,
                connection_attempts=3,
                retry_delay=2,
                heartbeat=60
            ))
            return connection
        except (pika.exceptions.AMQPConnectionError, Exception) as err:
            jitter = random.uniform(0.5, 1.5)
            sleep_time = min(delay * (2 ** (attempt - 1)) + jitter, 30)
            log_event("warn", f"RabbitMQ not ready ({err}), retrying in {sleep_time:.1f}s...")
            time.sleep(sleep_time)
    return None

from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import signal

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/health', '/api/notifications/health'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "healthy",
                "service": "notification-service"
            }).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress noisy default http server access logs

def start_health_server(port=8001):
    try:
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        log_event("info", f"Health check server listening on port {port}")
        return server
    except Exception as e:
        log_event("warn", f"Could not start health check server: {e}")
        return None

def main():
    rabbitmq_host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
    queue_name = 'order_notifications'
    health_port = int(os.getenv('HEALTH_PORT', '8001'))
    
    start_health_server(port=health_port)
    log_event("info", "Notification Service starting up...")
    
    connection = connect_with_retry(rabbitmq_host)
            
    if not connection:
        log_event("error", "Failed to connect to RabbitMQ after retries. Exiting.")
        sys.exit(1)
        
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)
    
    # Graceful shutdown handler
    def handle_signal(sig, frame):
        log_event("info", f"Received signal {sig}. Initiating graceful worker shutdown...")
        try:
            channel.stop_consuming()
            connection.close()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    log_event("info", " [*] Waiting for notification messages. To exit press CTRL+C")
    try:
        channel.start_consuming()
    except Exception as e:
        log_event("error", f"Consumer terminated: {e}")
        if connection and connection.is_open:
            connection.close()

if __name__ == '__main__':
    # Simple boilerplate check
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        print("Notification Service boilerplate syntax check: OK", flush=True)
        sys.exit(0)
    main()
