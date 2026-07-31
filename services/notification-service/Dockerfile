# Build stage
FROM python:3.11-slim AS build

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app
COPY --from=build /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH

# Security Hardening: Run as non-root user
RUN useradd -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "main.py"]
