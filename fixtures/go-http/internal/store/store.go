// Package store is a tiny in-memory stand-in for a SQL database. It exposes
// a Query/Exec API shaped like database/sql but parses nothing: statements
// are matched on substrings, which is enough for this demo fixture.
//
// Pretend schema:
//
//	CREATE TABLE orders (
//	    id     TEXT PRIMARY KEY,
//	    status TEXT NOT NULL,
//	    item   TEXT NOT NULL
//	);
//
//	CREATE TABLE audit_log (
//	    event    TEXT NOT NULL,
//	    order_id TEXT
//	);
//
// NOTE: the orders table is assumed large in production (10M+ rows).
package store

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"sync"
)

// Row is one generic result row.
type Row map[string]string

// Order is one row of the orders table.
type Order struct {
	ID     string `json:"id"`
	Status string `json:"status"`
	Item   string `json:"item"`
}

// Store is the in-memory fake database.
type Store struct {
	mu      sync.RWMutex
	ids     []string // insertion order, for deterministic results
	orders  map[string]Order
	execLog []string
}

// New returns an empty Store.
func New() *Store {
	return &Store{orders: make(map[string]Order)}
}

// Add inserts an order, failing on duplicate ids.
func (s *Store) Add(o Order) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.orders[o.ID]; exists {
		return fmt.Errorf("order %q already exists", o.ID)
	}
	s.ids = append(s.ids, o.ID)
	s.orders[o.ID] = o
	return nil
}

// Query pretends to run a SQL query with values already inlined in q.
func (s *Store) Query(q string) ([]Row, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.match(q, nil), nil
}

// QueryContext is the context-aware, parameterized variant of Query.
// Placeholder args are matched positionally, like database/sql.
func (s *Store) QueryContext(ctx context.Context, q string, args ...any) ([]Row, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.match(q, args), nil
}

// Exec pretends to run a write statement; it only records it.
func (s *Store) Exec(q string) error {
	if strings.TrimSpace(q) == "" {
		return errors.New("empty statement")
	}
	if !strings.Contains(q, "orders") && !strings.Contains(q, "audit_log") {
		return fmt.Errorf("unknown table in statement %q", q)
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	s.execLog = append(s.execLog, q)
	return nil
}

// ExecLog returns a copy of every statement passed to Exec.
func (s *Store) ExecLog() []string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return append([]string(nil), s.execLog...)
}

// match implements the fake "SQL engine": no parsing, substring checks only.
func (s *Store) match(q string, args []any) []Row {
	want := ""
	if len(args) > 0 {
		want = fmt.Sprint(args[0])
	}
	var rows []Row
	for _, id := range s.ids {
		o := s.orders[id]
		var ok bool
		switch {
		case !strings.Contains(q, "WHERE"):
			ok = true
		case strings.Contains(q, "WHERE status"):
			if want != "" {
				ok = o.Status == want
			} else {
				ok = strings.Contains(q, "'"+o.Status+"'")
			}
		case strings.Contains(q, "WHERE id"):
			if want != "" {
				ok = o.ID == want
			} else {
				ok = strings.Contains(q, "'"+o.ID+"'")
			}
		}
		if ok {
			rows = append(rows, Row{"id": o.ID, "status": o.Status, "item": o.Item})
		}
	}
	return rows
}
