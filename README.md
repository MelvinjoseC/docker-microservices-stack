# Enterprise Docker Microservices Stack

[![CI Pipeline](https://github.com/MelvinjoseC/docker-microservices-stack/actions/workflows/ci.yml/badge.svg)](https://github.com/MelvinjoseC/docker-microservices-stack/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository implements a production-ready, containerized microservices architecture showcasing a complete DevOps lifecycle. It is designed to run locally using Docker Compose and provisioned in production via Terraform and Kubernetes (EKS).

---

## 🏗️ Architecture Design

```
                     ┌──────────────────┐
                     │  Client Browser  │
                     └────────┬─────────┘
                              │ HTTP / Port 80
                              ▼
                     ┌──────────────────┐
                     │   API Gateway    │ (Nginx)
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
            ▼                  ▼ (orders.exchange)
     ┌───────────┐      ┌─────────────┐
     │PostgreSQL │      │  RabbitMQ   │
     └───────────┘      └──────┬──────┘
                               │ Event Consume
                               ▼ (order_notifications)
                        ┌─────────────┐
                        │Notification │ (Python Worker)
                        │   Service   │
                        └─────────────┘
```

### Stack Components

| Component | Technology | Database | Function | Port |
| :--- | :--- | :--- | :--- | :--- |
| **API Gateway** | Nginx | — | Reverse Proxy, Rate Limiting, Route Aggegation | `80` |
| **Frontend** | React / Vite | — | System Health Dashboard & Interactive Console | `3000` |
| **User Service** | Node.js / Express | PostgreSQL | Auth, Profile Management, Registration | `5000` |
| **Catalog Service** | Go / Gin | MongoDB | Product Catalog CRUD & Seeding | `8080` |
| **Order Service** | Python / FastAPI | PostgreSQL | Transaction Management & Async RabbitMQ events | `8000` |
| **Notification Service** | Python | — | Background Worker consuming RabbitMQ notifications | — |
| **Observability** | Prometheus / Grafana / Loki | — | Metrics scraping and centralized logging | `9090` / `3000` |

---

## 🛠️ Local Development Quickstart

### Prerequisites
- Docker (v20.10+) and Docker Compose (v2.0+)
- Make utility (optional, for automation commands)

### Orchestration Commands
We provide a helper `Makefile` at the root of the project to manage local runs:

```bash
# Spin up the entire stack (builds images if not present)
make up

# Check status of stack services
make status

# Follow logs from all containers
make logs

# Run local integration health checks
make test

# Shutdown services and remove local database volumes
make clean
```

### Local Entrypoints
Once services are running (`make up`), you can access:
- **Frontend Dashboard**: [http://localhost](http://localhost) (routed through Gateway)
- **API Gateway Health**: [http://localhost/health](http://localhost/health)
- **RabbitMQ Dashboard**: [http://localhost:15672](http://localhost:15672) (User: `guest` / Pass: `guest`)
- **Prometheus Console**: [http://localhost:9090](http://localhost:9090)
- **Grafana Server**: [http://localhost:3000](http://localhost:3000) (User: `admin` / Pass: `admin`)

---

## 📈 Observability Stack

### Metrics (Prometheus & Grafana)
Each microservice exposes a `/metrics` endpoint scraped by Prometheus every 15 seconds. 
- Custom counters track API transaction rates: `user_service_http_requests_total`.
- Grafana automatically provisions **Prometheus** as a data source with default dashboards to visualize system performance.

### Centralized Logging (Loki & Promtail)
- **Promtail** runs as a container daemon, listening to `/var/run/docker.sock` to dynamically scrape Docker log streams.
- Logs are shipped to **Loki** and queryable inside Grafana under the "Explore" panel using LogQL (e.g. `{container="user-service"}`).

---

## 🚀 Production Deployment (IaC & Kubernetes)

### Infrastructure as Code (Terraform)
We configure a production AWS environment located in `./terraform`:
- **VPC Network**: Multi-AZ layout with public subnets for external load balancers and private subnets containing EKS worker nodes. Includes active NAT Gateways.
- **EKS Cluster**: Fully managed Elastic Kubernetes Service cluster with auto-scaling node groups.

To provision:
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### Kubernetes Manifests
Standard yaml files are provided under `./k8s`:
- **`namespace.yaml`**: Pre-configures target namespace `microservices-stack`.
- **`databases.yaml`**: Persistent volumes, claims, and container deployments for PostgreSQL, MongoDB, and RabbitMQ.
- **`services.yaml`**: Horizontal Pod Autoscaling (HPA) targets, NodePort, LoadBalancer services, and image path definitions.

Deploy all manifests:
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/databases.yaml
kubectl apply -f k8s/services.yaml
```

### Helm Chart Packaging
A production chart is provided in `./k8s/helm/microservices-stack` to release versioned deployments.
```bash
cd k8s/helm
helm lint microservices-stack/
helm install my-release microservices-stack/ --values microservices-stack/values.yaml
```

---

## 🔄 CI/CD Pipelines

Powered by GitHub Actions, our workflows (`.github/workflows/`):
1. **CI Pipeline (`ci.yml`)**: Triggered on every pull request. Validates docker-compose syntax, lints Dockerfiles (`hadolint`), checks Node dependencies, compiles Go modules, and runs python linting (`flake8`).
2. **CD Pipeline (`cd.yml`)**: Triggered on push to `main` branch. Compiles multi-platform docker images and pushes them to Docker Hub.

---

## 🛡️ Hardening & Security Best Practices
- **Non-Root Execution**: Dockerfiles run using custom unprivileged users (e.g., `USER node`, `USER appuser`) to block container breakout exploits.
- **Multi-Stage Builds**: Docker configurations isolate build tools in initial cache layers, producing slim, dependency-free execution runtime layers.
- **Resource Constraints**: Kubernetes manifests set explicit CPU and Memory requests and limits to prevent noisy-neighbor memory exhaustion.
