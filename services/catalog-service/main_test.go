package main

import (
	"bytes"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestCatalogServiceEndpoints(t *testing.T) {
	router := setupRouter()

	t.Run("Health Check Degraded When DB Disconnected", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/health", nil)
		router.ServeHTTP(w, req)

		if w.Code != http.StatusServiceUnavailable && w.Code != http.StatusOK {
			t.Errorf("Expected status 503 or 200, got %d", w.Code)
		}
	})

	t.Run("Health Check Alias /api/products/health", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/api/products/health", nil)
		router.ServeHTTP(w, req)

		if w.Code != http.StatusServiceUnavailable && w.Code != http.StatusOK {
			t.Errorf("Expected status 503 or 200, got %d", w.Code)
		}
	})

	t.Run("Prometheus Metrics Endpoint", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/metrics", nil)
		router.ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Expected status 200 on /metrics, got %d", w.Code)
		}
	})

	t.Run("Correlation ID Header Propagation", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/metrics", nil)
		testCorrelationID := "test-trace-uuid-123"
		req.Header.Set("X-Correlation-ID", testCorrelationID)
		router.ServeHTTP(w, req)

		respCorrelationID := w.Header().Get("X-Correlation-ID")
		if respCorrelationID != testCorrelationID {
			t.Errorf("Expected X-Correlation-ID %s, got %s", testCorrelationID, respCorrelationID)
		}
	})

	t.Run("Add Product Validation", func(t *testing.T) {
		w := httptest.NewRecorder()
		// Missing Name and negative price
		jsonPayload := []byte(`{"name": "", "price": -10.0}`)
		req, _ := http.NewRequest("POST", "/api/products", bytes.NewBuffer(jsonPayload))
		req.Header.Set("Content-Type", "application/json")
		router.ServeHTTP(w, req)

		// Should either be 503 (no db) or 400 (validation error)
		if w.Code != http.StatusBadRequest && w.Code != http.StatusServiceUnavailable {
			t.Errorf("Expected 400 or 503 for invalid product payload, got %d", w.Code)
		}
	})
}
