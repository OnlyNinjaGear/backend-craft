// Command orders-fixture is a tiny in-memory orders API used as a
// code-review / checker-rule test fixture.
package main

import (
	"errors"
	"fmt"
	"log"
	"net/http"
	"sync/atomic"
	"time"

	"example.com/orders-fixture/internal/store"
)

type server struct {
	store     *store.Store
	inventory *InventoryClient
	idSeq     atomic.Int64
}

func newServer(st *store.Store, inv *InventoryClient) *server {
	s := &server{store: st, inventory: inv}
	s.idSeq.Store(100)
	return s
}

func (s *server) nextID() string {
	return fmt.Sprintf("ord-%d", s.idSeq.Add(1))
}

func (s *server) handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /orders", s.handleListOrders)
	mux.HandleFunc("POST /orders", s.handleCreateOrder)
	mux.HandleFunc("GET /orders/search", s.handleSearchOrders)
	mux.HandleFunc("GET /orders/{id}", s.handleGetOrder)
	return mux
}

func seedDemoData(st *store.Store) error {
	for _, o := range []store.Order{
		{ID: "ord-1", Status: "pending", Item: "keyboard"},
		{ID: "ord-2", Status: "shipped", Item: "mouse"},
		{ID: "ord-3", Status: "shipped", Item: "monitor"},
	} {
		if err := st.Add(o); err != nil {
			return err
		}
	}
	return nil
}

func main() {
	st := store.New()
	if err := seedDemoData(st); err != nil {
		log.Fatalf("seed: %v", err)
	}
	srv := newServer(st, NewInventoryClient())

	// Process-lifetime ops/debug listeners (see ops.go). The `go` statements
	// here are the goroutine card's escape hatch: registered in server
	// lifecycle, alive for the whole process.
	go startOps()
	go startDebug()

	httpServer := &http.Server{
		Addr:              ":8080",
		Handler:           srv.handler(),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      10 * time.Second,
	}
	log.Printf("orders API listening on %s", httpServer.Addr)
	if err := httpServer.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatalf("server: %v", err)
	}
}
