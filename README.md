# Enterprise Docker Microservices Stack

[![CI Pipeline](https://github.com/MelvinjoseC/docker-microservices-stack/actions/workflows/ci.yml/badge.svg)](https://github.com/MelvinjoseC/docker-microservices-stack/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository implements a production-grade, containerized microservices platform showcasing the full DevOps lifecycle. It supports multi-tier container orchestration via Docker Compose, production-hardened AWS infrastructure via Terraform (CIS-compliant EKS & VPC Flow Logs), Kubernetes deployment manifests with automated health probes and Secret decoupling, and an end-to-end Helm 3 chart.

---

## 🏗️ Architecture Design

```
                     ┌──────────────────┐
                     │  Client Browser  │
                     └────────┬─────────┘
                              │ HTTP / Port 80
                              ▼
                     ┌──────────────────┐
                     │   API Gateway    │ (Nginx Reverse Proxy / X-Request-ID)
                     └─┬───┬───┬───┬───┬┘
                       │   │   │   │   │
        ┌──────────────┘   │   │   │   └────────────────┐
        │ /                │   │   │ /api/orders    │ /api/products
        ▼                  │   │   ▼                ▼
┌──────────────┐           │   │ ┌──────────────┐ ┌──────────────┐
│   Frontend   │           │   │ │Order Service │ │Catalog Service│
│ (React/Vite) │           │   │ │ (Python/FA)  │ │   (Go/Gin)   │
└──────────────┘           │   │ └──────┬───────┘ └──────┬───────┘
                           │   │        │                │
            ┌──────────────┘   │        │                │
            │ /api/users       │        │                │
            ▼                  │        ▼                ▼
     ┌──────────────┐          │  ┌───────────┐    ┌───────────┐
     │ User Service │          │  │PostgreSQL │    │  MongoDB  │
     │ (Node/Expr)  │          │  └───────────┘    └───────────┘
     └──────┬───────┘          │
            │                  │ Event Publish
            ▼                  ▼ (order_notifications)
     ┌───────────┐      ┌─────────────┐
     │PostgreSQL │      │  RabbitMQ   │
     └───────────┘      └──────┬──────┘
                               │ Event Consume
                               ▼ (order_notifications + DLQ)
                        ┌─────────────┐
                        │Notification │ (Python Worker + HTTP Health Server)
                        │   Service   │
                        └─────────────┘
```

### Stack Components

| Component | Technology | Database | Function | Exposed Port | Network Tier |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **API Gateway** | Nginx 1.25 Alpine | — | Reverse Proxy, Rate Limiting, Upstream Keepalive, Trace ID Injection | `80` | `frontend-tier`, `backend-tier` |
| **Frontend** | React / Vite | — | System Health Dashboard & Interactive Console | `80` (Internal) | `frontend-tier` |
| **User Service** | Node.js 20 / Express | PostgreSQL | RESTful User CRUD, Validation, Trace ID Propagation | `5000` | `backend-tier`, `data-tier` |
| **Catalog Service** | Go 1.21 / Gin | MongoDB | Product Catalog CRUD, Full-text Search, Stock Adjustments | `8080` | `backend-tier`, `data-tier` |
| **Order Service** | Python 3.11 / FastAPI | PostgreSQL | Order Lifecycle Management, Resilient AMQP Publisher | `8000` | `backend-tier`, `data-tier` |
| **Notification Service** | Python 3.11 / Pika | — | Async AMQP Consumer, Dead Letter Queue (DLQ), Health Server | `8001` | `backend-tier`, `data-tier` |
| **Databases** | Postgres 15, Mongo 6.0 | — | ACID Persistent Storage with Automated Snapshot/Restore | `5432`, `27017` | `data-tier` |
| **Broker** | RabbitMQ 3.12 | — | Message Queue with DLQ exchange routing | `5672`, `15672` | `data-tier` |
| **Observability** | Prometheus, Grafana, Loki | — | Metrics scraping, Alert rules, Log aggregation | `9090`, `3000`, `3100`| `backend-tier` |

---

## 🔌 REST API Specification

### User Service (`/api/users`)
- `GET /health` & `GET /api/users/health`: Health status probe.
- `GET /api/users?limit=50&offset=0`: List all users with pagination.
- `GET /api/users/:id`: Retrieve single user by ID.
- `POST /api/users`: Create user (`name`, `email`, optional `role`). Validates email format.
- `PUT /api/users/:id`: Update user profile and role.
- `DELETE /api/users/:id`: Delete user record.

### Catalog Service (`/api/products`)
- `GET /health` & `GET /api/products/health`: Health status probe.
- `GET /api/products?search={term}`: Retrieve products with regex filtering.
- `GET /api/products/:id`: Retrieve single product by ID.
- `POST /api/products`: Create new product catalog item (`name`, `price`, `stock`).
- `PUT /api/products/:id`: Update product attributes.
- `DELETE /api/products/:id`: Delete product item.

### Order Service (`/api/orders`)
- `GET /health` & `GET /api/orders/health`: Health status probe.
- `GET /api/orders`: List all orders.
- `GET /api/orders/{order_id}`: Retrieve single order by ID.
- `POST /api/orders`: Create new order (`user_id`, `items: [{product_id, quantity, price}]`). Dispatches event to RabbitMQ.
- `PATCH /api/orders/{order_id}/status`: Update order status (`status: "COMPLETED"`).
- `DELETE /api/orders/{order_id}`: Cancel/remove order.

---

## 🛠️ Local Development Quickstart

### Prerequisites
- Docker (v20.10+) and Docker Compose (v2.0+)
- Make utility (optional)

### Orchestration Commands
We provide a helper `Makefile` at the root of the project to manage local runs:

```bash
# Spin up the entire stack with isolated network tiers
make up

# Check container health and status
make status

# Follow logs from all containers
make logs

# Run unit and integration test suites
make test-unit

# Run local integration health checks
make test

# Execute database backup snapshot
make backup

# Restore database from backup snapshot
make restore

# Run load test benchmark
make benchmark

# Shutdown services and remove local database volumes
make clean
```

### Local Entrypoints
Once services are running (`make up`), access:
- **Frontend Dashboard**: [http://localhost](http://localhost) (routed through Gateway)
- **API Gateway Health**: [http://localhost/health](http://localhost/health)
- **RabbitMQ Dashboard**: [http://localhost:15672](http://localhost:15672) (User: `guest` / Pass: `guest`)
- **Prometheus Console**: [http://localhost:9090](http://localhost:9090)
- **Grafana Server**: [http://localhost:3000](http://localhost:3000) (User: `admin` / Pass: `admin`)

---

## 📈 Observability & Alerting Stack

### Metrics & Alerts (Prometheus & Grafana)
- Each microservice exposes a `/metrics` endpoint scraped every 15 seconds.
- Alert rules in `monitoring/prometheus/alert.rules.yml` evaluate:
  - `ServiceDown`: Triggers critical alert when an instance is unreachable for > 1m.
  - `HighHttpErrorRate`: Triggers warning when 5xx HTTP responses exceed 5% of traffic.
  - `SlowHttpRequests`: Detects throughput anomalies.
- Provisioned Grafana dashboard includes:
  - User Service request rates by method, route, and status code.
  - Catalog and Order service performance.
  - Instant cluster availability status indicators.
  - 5xx error rate time series.

### Centralized Logging (Loki & Promtail)
- **Promtail** daemon scrapes `/var/run/docker.sock` and `/var/log` for container output.
- All backend services format logs as JSON containing `correlation_id`, `timestamp`, `level`, `service`, and `duration_ms`.
- Query logs in Grafana Explore using LogQL:
  ```logql
  {container="dev-order-service"} |= "error"
  ```

---

## 🚀 Production Deployment (IaC & Kubernetes)

### Infrastructure as Code (Terraform)
Located in `./terraform`:
- **CIS Benchmark Compliance**:
  - EKS cluster enabled with KMS envelope encryption (`aws_kms_key`) for Kubernetes secrets.
  - Full control plane audit logging (`api`, `audit`, `authenticator`, `controllerManager`, `scheduler`).
  - Worker node group launch templates enforcing IMDSv2 (`http_tokens = "required"`) and encrypted gp3 EBS root storage.
  - Multi-AZ VPC network with VPC Flow Logs streamed to CloudWatch for network auditing.

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### Kubernetes Manifests
Standard yaml manifests are provided under `./k8s`:
- **`namespace.yaml`**: Target namespace `microservices-stack`.
- **`configmap.yaml` & `secrets.yaml`**: Decoupled non-sensitive configuration and secure credentials.
- **`databases.yaml`**: PVCs, Stateful/Persistent deployments for PostgreSQL, MongoDB, RabbitMQ.
- **`services.yaml`**: Pod deployments configured with `livenessProbe` and `readinessProbe` on all services.
- **`network-policies.yaml`**: Strict pod-to-pod network isolation restricting database access only to authorized microservices.
- **`hpa.yaml`**: Horizontal Pod Autoscalers based on CPU and memory thresholds.
- **`ingress.yaml`**: Ingress routing preserving API paths.

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/databases.yaml
kubectl apply -f k8s/network-policies.yaml
kubectl apply -f k8s/services.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
```

### Helm 3 Chart Packaging
A complete Helm chart is packaged in `./k8s/helm/microservices-stack` containing templates for all microservices, ConfigMaps, Secrets, Ingress, and standard `_helpers.tpl` labels:

```bash
cd k8s/helm
helm lint microservices-stack/
helm install microservices-stack microservices-stack/ --values microservices-stack/values.yaml
```

---

## 🔄 CI/CD Pipelines

Automated via GitHub Actions (`.github/workflows/`):
1. **CI Pipeline (`ci.yml`)**:
   - Validates `docker-compose.yml` specification.
   - Lints Dockerfiles using `hadolint`.
   - Executes Jest test suite for User Service.
   - Builds and runs Go tests for Catalog Service.
   - Runs `flake8` and `pytest` for Order and Notification services.
2. **Security Scans**:
   - `gitleaks.yml`: Scans git history for leaked credentials.
   - `trivy.yml`: Scans repository configuration for known CVEs.
   - `terraform-scan.yml`: Executes `checkov` static analysis against Terraform templates.
3. **CD Pipeline (`cd.yml`)**:
   - Triggered on push to `main` branch. Builds and publishes multi-platform Docker images to Docker Hub with `latest` and commit SHA tags.

---

## 🛡️ Security Hardening Summary
- **Zero Plaintext Secrets in Manifests**: All database passwords and connection strings externalized to Kubernetes Secrets.
- **IMDSv2 Enforced**: AWS metadata service v1 disabled on worker nodes to prevent SSRF credential theft.
- **Non-Root Execution**: Every service runs as an unprivileged user (`USER node`, `USER appuser`).
- **Network Segmentation**: Docker bridge networks and Kubernetes NetworkPolicies block direct external traffic to databases.
- **Dead Letter Queue (DLQ)**: Poison-pill messages in RabbitMQ automatically diverted without data loss.
