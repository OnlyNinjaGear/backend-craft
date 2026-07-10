package main

import (
	"expvar"
	"log"
	"net/http"
)

// opsHandler serves liveness and runtime counters for the ops team.
func opsHandler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	})
	mux.Handle("GET /debug/vars", expvar.Handler())
	return mux
}

// startOps exposes the ops endpoints for the life of the process.
func startOps() {
	// PLANTED: go-http-server-no-timeouts — bare &http.Server{Addr, Handler}
	// on all interfaces: every timeout field is zero, which means no timeout
	// at all, so a stalled client holds its connection and goroutine forever.
	opsServer := &http.Server{
		Addr:    ":8081",
		Handler: opsHandler(),
	}
	log.Printf("ops API listening on %s", opsServer.Addr)
	if err := opsServer.ListenAndServe(); err != nil {
		log.Printf("ops server: %v", err)
	}
}

// startDebug serves the default mux (expvar self-registers its handler
// there) so engineers can reach debug endpoints without the ops mux.
func startDebug() {
	// PLANTED: go-http-server-no-timeouts — package-level ListenAndServe on
	// all interfaces (not localhost) uses a default http.Server: zero
	// timeouts, so it inherits the same slowloris exposure.
	if err := http.ListenAndServe(":6060", nil); err != nil {
		log.Printf("debug server: %v", err)
	}
}
