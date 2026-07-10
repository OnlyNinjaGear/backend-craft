package tests

import (
	"context"
	"fmt"
)

func probes(ctx context.Context, pool DB, tbl string, id int64) {
	// ruleid: backend-craft.go.sql-sprintf-query-pgx
	pool.Query(ctx, fmt.Sprintf("SELECT * FROM %s", tbl))
	// ruleid: backend-craft.go.sql-sprintf-query-pgx
	pool.QueryRow(ctx, fmt.Sprintf("SELECT * FROM %s WHERE x=1", tbl))
	// ruleid: backend-craft.go.sql-sprintf-query-pgx
	pool.Exec(ctx, fmt.Sprintf("DELETE FROM %s", tbl))
	// ok: backend-craft.go.sql-sprintf-query-pgx
	pool.Query(ctx, "SELECT * FROM t WHERE id=$1", id)
	// ok: backend-craft.go.sql-sprintf-query-pgx
	_ = fmt.Sprintf("log: %d", id)
	q := fmt.Sprintf("SELECT * FROM %s", tbl)
	q = "SELECT 1"
	// ok: backend-craft.go.sql-sprintf-query-pgx
	pool.Query(ctx, q)
	// KNOWN FN (documented in the rule message): a pre-built query string that is
	// genuinely dynamic is NOT matched, because the rule is inline-only. This line
	// is intentionally left un-annotated -- it is neither a clean case nor a
	// caught TP, it is an honest miss. Catching it would require dataflow.
	qq := fmt.Sprintf("SELECT * FROM %s", tbl)
	pool.Query(ctx, qq)
}
