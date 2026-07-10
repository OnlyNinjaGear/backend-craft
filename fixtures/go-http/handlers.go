package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"example.com/orders-fixture/internal/store"
)

// handleListOrders serves GET /orders?status=<status>.
func (s *server) handleListOrders(w http.ResponseWriter, r *http.Request) {
	status := r.URL.Query().Get("status")
	if status == "" {
		http.Error(w, "status query parameter is required", http.StatusBadRequest)
		return
	}

	// PLANTED: sql-string-concat
	q := fmt.Sprintf("SELECT * FROM orders WHERE status = '%s'", status)
	rows, err := s.store.Query(q)
	if err != nil {
		http.Error(w, "query failed", http.StatusInternalServerError)
		return
	}
	writeJSON(w, http.StatusOK, rows)
}

// handleCreateOrder serves POST /orders.
func (s *server) handleCreateOrder(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Item string `json:"item"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid JSON body", http.StatusBadRequest)
		return
	}
	if req.Item == "" {
		http.Error(w, "item is required", http.StatusBadRequest)
		return
	}

	order := store.Order{ID: s.nextID(), Status: "pending", Item: req.Item}

	// Reserve stock before accepting the order.
	if err := s.inventory.Reserve(order.Item); err != nil {
		http.Error(w, "inventory unavailable", http.StatusBadGateway)
		return
	}

	if err := s.store.Add(order); err != nil {
		http.Error(w, "could not save order", http.StatusInternalServerError)
		return
	}

	// PLANTED: go-ignored-error
	_ = s.store.Exec("INSERT INTO audit_log (event) VALUES ('order_created')")

	// PLANTED: go-goroutine-without-lifecycle
	go func() {
		sendConfirmationEmail(order)
	}()

	writeJSON(w, http.StatusCreated, order)
}

// handleGetOrder serves GET /orders/{id}.
func (s *server) handleGetOrder(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")

	rows, err := s.store.QueryContext(r.Context(),
		"SELECT id, status, item FROM orders WHERE id = ?", id)
	if err != nil {
		http.Error(w, "query failed", http.StatusInternalServerError)
		return
	}
	if len(rows) == 0 {
		http.Error(w, "order not found", http.StatusNotFound)
		return
	}
	row := rows[0]

	// PLANTED: timeout-without-cancellation-propagation
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	inStock, err := s.inventory.Check(ctx, row["item"])
	if err != nil {
		http.Error(w, "inventory check failed", http.StatusBadGateway)
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"id":       row["id"],
		"status":   row["status"],
		"item":     row["item"],
		"in_stock": inStock,
	})
}

// handleSearchOrders serves GET /orders/search?status=<status>. It is the
// safe counterpart of handleListOrders: constant parameterized query, the
// request context propagated downstream, and every error handled.
func (s *server) handleSearchOrders(w http.ResponseWriter, r *http.Request) {
	status := r.URL.Query().Get("status")
	if status == "" {
		http.Error(w, "status query parameter is required", http.StatusBadRequest)
		return
	}

	const q = "SELECT id, status, item FROM orders WHERE status = ?"
	rows, err := s.store.QueryContext(r.Context(), q, status)
	if err != nil {
		http.Error(w, "query failed", http.StatusInternalServerError)
		return
	}
	writeJSON(w, http.StatusOK, rows)
}

// writeJSON writes v as a JSON response and handles encoding errors.
func writeJSON(w http.ResponseWriter, statusCode int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("write response: %v", err)
	}
}

// sendConfirmationEmail pretends to deliver an order confirmation email.
func sendConfirmationEmail(o store.Order) error {
	time.Sleep(10 * time.Millisecond) // pretend SMTP round trip
	log.Printf("email: confirmation sent for order %s", o.ID)
	return nil
}
