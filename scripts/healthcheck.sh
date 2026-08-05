#!/bin/bash
# Microservices stack local health check script

set -e

# Target host (default to localhost)
HOST=${1:-"localhost"}

echo "--------------------------------------------------------"
echo "Starting Health Check for Docker Microservices Stack..."
echo "Host: $HOST"
echo "--------------------------------------------------------"

check_endpoint() {
  local name=$1
  local url=$2
  local expected_status=$3
  
  echo -n "Checking $name ($url)... "
  
  # Perform request
  local response
  response=$(curl -s -w "%{http_code}" "$url" || echo "failed 000")
  
  local body
  body=$(echo "$response" | sed 's/...$//')
  local status
  status=${response: -3}
  
  if [ "$status" -eq "$expected_status" ]; then
    echo -e "\e[32m[OK] (Status: $status)\e[0m"
    return 0
  else
    echo -e "\e[31m[FAILED] (Status: $status, Response: $body)\e[0m"
    return 1
  fi
}

failed=0

# Check API Gateway
check_endpoint "API Gateway" "http://$HOST/health" 200 || failed=1

# Check User Service (Direct)
check_endpoint "User Service (Direct)" "http://$HOST:5000/health" 200 || failed=1

# Check Catalog Service (Direct)
check_endpoint "Catalog Service (Direct)" "http://$HOST:8080/health" 200 || failed=1

# Check Order Service (Direct)
check_endpoint "Order Service (Direct)" "http://$HOST:8000/health" 200 || failed=1

# Check services through the API Gateway
echo "------------------------------"
echo "Testing routing via API Gateway"
echo "------------------------------"
check_endpoint "Gateway -> User Route" "http://$HOST/api/users" 200 || failed=1
check_endpoint "Gateway -> Catalog Route" "http://$HOST/api/products" 200 || failed=1
check_endpoint "Gateway -> Order Route" "http://$HOST/api/orders" 200 || failed=1

echo "--------------------------------------------------------"
if [ $failed -eq 0 ]; then
  echo -e "\e[32m✔ SUCCESS: All services are healthy and API routing is correct!\e[0m"
  exit 0
else
  echo -e "\e[31m✖ FAILURE: Some services are unhealthy or routing is broken.\e[0m"
  exit 1
fi
