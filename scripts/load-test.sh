#!/bin/bash
# Microservices Load Testing Script
# This script generates HTTP traffic using ApacheBench (ab) or curl to simulate user load,
# which allows validation of Prometheus metrics and HPA auto-scaling rules.

set -e

HOST=${1:-"localhost"}
CONCURRENCY=10
REQUESTS=500

echo "=========================================================="
echo "Starting DevOps Microservices Load Test Benchmark..."
echo "Target Host: $HOST"
echo "Concurrency level: $CONCURRENCY"
echo "Total Requests: $REQUESTS"
echo "=========================================================="

# Check if ApacheBench is installed, fallback to curl loop if not
if command -v ab >/dev/null 2>&1; then
  echo "✔ ApacheBench detected. Simulating catalog queries..."
  ab -n "$REQUESTS" -c "$CONCURRENCY" "http://$HOST/api/products"
  
  echo ""
  echo "✔ Simulating user registrations..."
  # Temporary post data file
  echo '{"name": "Performance Test", "email": "perf@example.com"}' > /tmp/post_user.json
  ab -n 100 -c 5 -p /tmp/post_user.json -T "application/json" "http://$HOST/api/users"
  rm -f /tmp/post_user.json
  
  echo ""
  echo "✔ Simulating order traffic..."
  echo '{"user_id": 1, "items": [{"product_id": "p1", "quantity": 1, "price": 1299.99}]}' > /tmp/post_order.json
  ab -n 100 -c 5 -p /tmp/post_order.json -T "application/json" "http://$HOST/api/orders"
  rm -f /tmp/post_order.json
else
  echo "⚠ ApacheBench (ab) not found. Falling back to multi-threaded curl simulation..."
  for i in {1..200}; do
    curl -s -o /dev/null -w "%{http_code} " "http://$HOST/api/products" &
    if [ $((i % 20)) -eq 0 ]; then
      wait # throttle execution
    fi
  done
  wait
  echo "✔ Curl loop load simulation completed."
fi

echo "=========================================================="
echo "Load Test Completed successfully!"
echo "Check Grafana Dashboard (http://localhost:3000) for metrics spikes."
echo "=========================================================="
