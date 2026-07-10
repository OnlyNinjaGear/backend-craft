package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"example.com/orders-fixture/internal/store"
)

func newTestServer(t *testing.T) (*server, *store.Store) {
	t.Helper()
	st := store.New()
	if err := seedDemoData(st); err != nil {
		t.Fatalf("seed: %v", err)
	}
	inv := NewInventoryClient()
	// Fake downstream: the reservation succeeds on the first attempt so
	// tests never sit in the retry loop.
	inv.callReserve = func(item string) error { return nil }
	return newServer(st, inv), st
}

func doRequest(t *testing.T, h http.Handler, method, target, body string) *httptest.ResponseRecorder {
	t.Helper()
	var req *http.Request
	if body == "" {
		req = httptest.NewRequest(method, target, nil)
	} else {
		req = httptest.NewRequest(method, target, strings.NewReader(body))
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestListOrdersByStatus(t *testing.T) {
	srv, _ := newTestServer(t)
	rec := doRequest(t, srv.handler(), http.MethodGet, "/orders?status=shipped", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body: %s", rec.Code, rec.Body.String())
	}
	var rows []store.Row
	if err := json.Unmarshal(rec.Body.Bytes(), &rows); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(rows) != 2 {
		t.Fatalf("got %d rows, want 2: %v", len(rows), rows)
	}
	for _, row := range rows {
		if row["status"] != "shipped" {
			t.Errorf("row %v has status %q, want shipped", row, row["status"])
		}
	}
}

func TestCreateOrder(t *testing.T) {
	srv, _ := newTestServer(t)
	h := srv.handler()

	rec := doRequest(t, h, http.MethodPost, "/orders", `{"item":"webcam"}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("status = %d, want 201; body: %s", rec.Code, rec.Body.String())
	}
	var created store.Order
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if created.ID == "" || created.Status != "pending" || created.Item != "webcam" {
		t.Fatalf("unexpected order: %+v", created)
	}

	// The created order is retrievable.
	rec = doRequest(t, h, http.MethodGet, "/orders/"+created.ID, "")
	if rec.Code != http.StatusOK {
		t.Fatalf("get created order: status = %d, want 200; body: %s", rec.Code, rec.Body.String())
	}
}

func TestCreateOrderWritesAuditLog(t *testing.T) {
	srv, st := newTestServer(t)
	rec := doRequest(t, srv.handler(), http.MethodPost, "/orders", `{"item":"desk"}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("status = %d, want 201; body: %s", rec.Code, rec.Body.String())
	}
	log := st.ExecLog()
	if len(log) != 1 || !strings.Contains(log[0], "audit_log") {
		t.Fatalf("exec log = %v, want one audit_log insert", log)
	}
}

func TestGetOrderByID(t *testing.T) {
	srv, _ := newTestServer(t)
	rec := doRequest(t, srv.handler(), http.MethodGet, "/orders/ord-1", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body: %s", rec.Code, rec.Body.String())
	}
	var resp map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp["id"] != "ord-1" || resp["item"] != "keyboard" || resp["in_stock"] != true {
		t.Fatalf("unexpected response: %v", resp)
	}
}

func TestSearchOrders(t *testing.T) {
	srv, _ := newTestServer(t)
	rec := doRequest(t, srv.handler(), http.MethodGet, "/orders/search?status=pending", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body: %s", rec.Code, rec.Body.String())
	}
	var rows []store.Row
	if err := json.Unmarshal(rec.Body.Bytes(), &rows); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(rows) != 1 || rows[0]["id"] != "ord-1" {
		t.Fatalf("got rows %v, want exactly ord-1", rows)
	}
}
