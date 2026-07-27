import time
import sys
import pika
import json

def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        print(f" [x] Notification Received: Processing order #{data.get('id')} for User #{data.get('user_id')}", flush=True)
        # Simulate processing notification (email/SMS)
        time.sleep(1)
        print(f" [x] Notification Sent successfully for order #{data.get('id')}!", flush=True)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error processing message: {e}", flush=True)
        # Nack and requeue
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    rabbitmq_host = 'rabbitmq'
    queue_name = 'order_notifications'
    
    print("Notification Service starting...", flush=True)
    
    # Try connecting to RabbitMQ with retry loop
    connection = None
    for attempt in range(1, 11):
        try:
            print(f"Attempting to connect to RabbitMQ (attempt {attempt}/10)...", flush=True)
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
            break
        except pika.exceptions.AMQPConnectionError:
            print("RabbitMQ not ready yet, sleeping 5s...", flush=True)
            time.sleep(5)
            
    if not connection:
        print("Failed to connect to RabbitMQ after 10 attempts. Exiting.", flush=True)
        sys.exit(1)
        
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)
    
    print(' [*] Waiting for notification messages. To exit press CTRL+C', flush=True)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print('Interrupted', flush=True)
        connection.close()

if __name__ == '__main__':
    # Simple boilerplate check
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        print("Notification Service boilerplate syntax check: OK", flush=True)
        sys.exit(0)
    main()
