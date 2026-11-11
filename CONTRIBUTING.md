# Contributing to Docker Microservices Stack

Thank you for your interest in contributing to the Docker Microservices Stack! This guide explains our development workflow, coding standards, and testing procedures.

---

## 📋 Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free environment for all contributors.

---

## 🛠️ Local Development Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/MelvinjoseC/docker-microservices-stack.git
   cd docker-microservices-stack
   ```

2. **Environment File**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

3. **Start the Stack**:
   ```bash
   make up
   ```

4. **Run Unit Tests**:
   ```bash
   make test-unit
   ```

5. **Run E2E Smoke Tests**:
   ```bash
   make test-e2e
   ```

---

## 📝 Commit Conventions

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat(...)`: A new user-facing feature or architectural capability
- `fix(...)`: A bug fix
- `test(...)`: Adding or refactoring automated tests
- `docs(...)`: Documentation changes
- `ci(...)`: GitHub Actions or CI/CD workflow updates
- `iac(...)`: Terraform or Kubernetes manifest modifications
- `perf(...)`: Performance optimization or indexing

Example commit message:
```
feat(order): implement order idempotency key mechanism and duplicate request guard
```

---

## 🧪 Testing Guidelines

Before opening a pull request, ensure all test suites pass:

- **Node.js (User Service)**: `npm test` with 100% route coverage
- **Go (Catalog Service)**: `go test -v ./...`
- **Python (Order & Notification)**: `pytest` and `flake8`
- **Docker Compose**: `docker compose config -q`
- **Helm**: `helm lint k8s/helm/microservices-stack`
