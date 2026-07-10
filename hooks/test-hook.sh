#!/bin/bash
# Acceptance tests for backend-craft-check.py. Run from anywhere.
set -u
HOOK="$(cd "$(dirname "$0")" && pwd)/backend-craft-check.py"
SID="hook-test-$$"
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "  ok: $1"; }
bad()  { FAIL=$((FAIL+1)); echo "  FAIL: $1"; }

event() { # $1=file_path $2=session
  printf '{"session_id":"%s","hook_event_name":"PostToolUse","tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$2" "$1"
}

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# --- fixture-like flawed python project (no uv.lock -> no project-local) ---
mkdir -p "$TMP/pyproj/app"
cat > "$TMP/pyproj/pyproject.toml" <<'EOF'
[project]
name = "t"
version = "0"
EOF
cat > "$TMP/pyproj/app/main.py" <<'EOF'
def search(cur, q):
    cur.execute(f"SELECT * FROM p WHERE name LIKE '%{q}%'")
    try:
        cur.fetchall()
    except Exception:
        pass
EOF

echo "1. python file, no local checker -> semgrep findings + one-time warning, exit 0"
OUT1=$(event "$TMP/pyproj/app/main.py" "$SID" | python3 "$HOOK"); RC=$?
[ $RC -eq 0 ] && ok "exit 0" || bad "exit $RC"
echo "$OUT1" | grep -q "sql-fstring-execute" && ok "sql finding" || bad "sql finding missing: $OUT1"
echo "$OUT1" | grep -q "swallowed-exception" && ok "except finding" || bad "except finding missing"
echo "$OUT1" | grep -q "no project-local python checker" && ok "one-time warning" || bad "warning missing"
echo "$OUT1" | grep -q "NOT evidence the backend is safe" && ok "no-safety disclaimer" || bad "disclaimer missing"

echo "2. same event again -> dedup: silence"
OUT2=$(event "$TMP/pyproj/app/main.py" "$SID" | python3 "$HOOK"); RC=$?
[ $RC -eq 0 ] && ok "exit 0" || bad "exit $RC"
[ -z "$OUT2" ] && ok "silent on repeat" || bad "repeated output: $OUT2"

echo "3. cap at 5 findings"
cat > "$TMP/pyproj/app/many.py" <<'EOF'
def f(cur, a, b, c):
    cur.execute(f"SELECT {a}")
    cur.execute(f"SELECT {b}")
    cur.execute(f"SELECT {c}")
    cur.execute("SELECT %s" % a)
    cur.execute("SELECT {}".format(b))
    cur.execute("SELECT " + c)
    try:
        pass
    except Exception:
        pass
EOF
OUT3=$(event "$TMP/pyproj/app/many.py" "$SID" | python3 "$HOOK")
N=$(echo "$OUT3" | python3 -c "import json,sys; d=json.load(sys.stdin); ctx=d['hookSpecificOutput']['additionalContext']; print(sum(1 for l in ctx.splitlines() if l.startswith('[')))" 2>/dev/null)
[ "$N" = "5" ] && ok "exactly 5 shown" || bad "shown=$N"
echo "$OUT3" | grep -q "more findings suppressed" && ok "suppression notice" || bad "no suppression notice"

echo "4. non-backend file -> silence"
OUT4=$(event "$TMP/pyproj/README.md" "$SID" | python3 "$HOOK"); RC=$?
[ $RC -eq 0 ] && [ -z "$OUT4" ] && ok "silent" || bad "rc=$RC out=$OUT4"

echo "5. garbage stdin -> exit 0, silence"
OUT5=$(echo "not json" | python3 "$HOOK"); RC=$?
[ $RC -eq 0 ] && [ -z "$OUT5" ] && ok "robust" || bad "rc=$RC out=$OUT5"

echo "6. fixtures/ path excluded"
OUT6=$(event "/Users/oleg/Desktop/backend-skills/fixtures/python-fastapi/app/main.py" "$SID" | python3 "$HOOK"); RC=$?
[ $RC -eq 0 ] && [ -z "$OUT6" ] && ok "fixture skipped" || bad "rc=$RC out=$OUT6"

echo "7. go project with local checker (go vet runs, clean file -> silence or semgrep only)"
mkdir -p "$TMP/goproj"
cat > "$TMP/goproj/go.mod" <<'EOF'
module example.com/t

go 1.26
EOF
cat > "$TMP/goproj/main.go" <<'EOF'
package main

func main() {}
EOF
OUT7=$(event "$TMP/goproj/main.go" "$SID" | python3 "$HOOK"); RC=$?
[ $RC -eq 0 ] && ok "exit 0" || bad "exit $RC"
echo "$OUT7" | grep -q "no project-local go checker" && bad "false no-checker warning" || ok "go vet counted as local"

echo; echo "PASS=$PASS FAIL=$FAIL"
[ $FAIL -eq 0 ]
