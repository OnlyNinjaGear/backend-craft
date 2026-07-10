# forward-test 101: start-mode (round 2)

> Round 2 (2026-07-10): run on disposable fixture copies with grading
> markers and READMEs stripped (closes the round-1 marker-leak validity hole
> and the shared-fixture mutation incident). Judges verified explicit
> ROUND-2 FOCUS items for every round-1 miss. Original fixtures verified
> untouched via git status.

Date: 2026-07-10
Fixture copy: none (design task)
Ground truth: -
Score: 4/4 (round 1: 4/4)
Round-1 miss closed: True
Generic advice: False
Verifier quality (judge): Strong. Every non-trivial dependency has a named verifier; the test matrix specifies concrete adversarial cases (org-B token against org-A resources -> 404, duplicate Idempotency-Key -> one invoice, 10 concurrent finalizes -> unique sequential numbers, two dispatcher claimers -> one send, txn rollback -> no delivery row, metadata-IP webhook URL rejected, sentinel-secret redaction); CI sequence includes migration upgrade/downgrade round-trip and oasdiff breaking-change gate. No commands were executed, but the skill's proof contract explicitly permits this for a design-only environment and the answer invokes that clause honestly without over-claiming.

## Prompt

```text

```

## Round-2 focus verdict

No items were explicitly marked ROUND-2 FOCUS in this test. Per-behavior verdicts: (1) stack with tradeoffs PASS; (2) tenant model early PASS; (3) API contract/migrations/auth/idempotent webhooks/tests/observability PASS on all six; (4) avoids microservice overbuild PASS; (5) library gate (fit -> failure removed -> integration boundary -> verifier -> escape hatch) PASS, with only the docs-checked statement from the Review output format omitted. Nothing regressed.

## References loaded

- SKILL.md
- stack-recipes.md
- library-decisions.md
- api-contracts.md
- auth-tenancy-security.md
- persistence-migrations.md
- reliability-async.md
- observability-ops.md
- testing-verification.md
- language-adapters.md

## Judge summary

Near-model Start-mode execution: Impact Read first, all 9 Start-mode references loaded and visibly applied, stack chosen with real tradeoffs and rejected alternatives, tenant model defined as the top P0 risk before any code, transactional-outbox webhooks with at-least-once semantics and SSRF defense, per-dependency verifiers per the library gate, no microservice overbuild, and an honest proof-contract statement using the skill's untestable-environment clause rather than fake verification claims. Non-obvious failure modes (crash-mid-send self-heal, concurrent idempotency duplicates, gapless-numbering legality, send-time SSRF re-check) push it to a 4. Only residual issues are a missing per-library docs-checked statement and an unaddressed stuck-in-progress idempotency key scenario, the latter being a gap in the reference itself.

## Misses

- Minor: library-decisions.md Review output requires 'docs/source checked, or the reason current verification is unavailable' per recommended library; the answer never states docs verification status for any dependency
- Minor design gap inherited from the reference: idempotency guard commits the key before executing the operation, so a crash between key insert and response store leaves retries stuck on 409 request_in_progress with no expiry/recovery path specified

## Changes needed

- references/api-contracts.md, 'Mutating retries require idempotency' safe pattern: add a recovery rule for in-progress idempotency records — a stored key with no response must expire or be reclaimable (e.g., lease timestamp + takeover after N seconds), otherwise a crash between key insert and response store bricks the key forever; add matching verifier 'crashed first attempt -> retry after lease expiry succeeds'

## Tested agent answer (verbatim)

````text
All Start-mode references loaded. Producing the design directly as the deliverable (no repo to modify; per instructions I am not scaffolding files).

# Backend foundation design: small B2B SaaS (users, orgs, projects, invoices, webhooks)

## 0. Impact Read

- **Public contracts:** entirely new API surface (v1). Everything decided here becomes a consumer contract on day one.
- **Data:** new Postgres schema; invoices are money-adjacent records; webhook secrets are credentials at rest.
- **Principals/tenants:** users belong to organizations via memberships; every domain row except `users`/`organizations` is tenant-owned. Tenant isolation is the #1 P0 risk class.
- **Side effects that outlive requests:** webhook delivery (retries, duplicates), invoice number assignment, outbound HTTP to customer-controlled URLs (SSRF risk).
- **Existing verifiers:** none (greenfield). CI and tests are part of the foundation, not an afterthought.

All answers non-empty, so the full Start-mode reference set was loaded (listed at the end).

## 1. Architecture record

**Chosen recipe: Python — FastAPI + Pydantic v2 + SQLAlchemy 2.x + Alembic + Postgres**, with a **synchronous** DB layer (psycopg 3) and a **Postgres-backed outbox worker** for webhook delivery. Single deployable repo, two processes: `api` and `dispatcher`.

Why this fits a team of 2:

- API-first product; FastAPI gives OpenAPI generation, DTO validation, and dependency injection for auth/tenant context with almost no framework ceremony.
- Sync SQLAlchemy sessions remove the async-session-sharing and cancellation footguns; this workload is DB-bound CRUD plus one IO-bound worker. Async is not a quality badge; it can be introduced later per-module (dispatcher first) without a rewrite.
- **One piece of infrastructure: Postgres.** Queue, outbox, idempotency store, and data all live in the same transactional database. No Redis/Celery/RabbitMQ to operate at 2-person scale.

Rejected alternatives:

- **Django + DRF:** strongest competitor — free admin is real leverage for support work. Rejected because the highest-risk surfaces here (webhook outbox/dispatcher, idempotency keys, invoice state machine) are custom either way, and the API-first contract + typed-DTO story is cleaner in FastAPI. If you expect heavy back-office CRUD and staff tooling, flip this decision now, not later.
- **Celery + Redis for webhooks:** correct at higher volume; unjustified infra for launch. The outbox table with `FOR UPDATE SKIP LOCKED` survives restarts, is transactional with domain writes, and is trivially replaceable by Celery later because enqueue is just an insert.
- **SQLModel:** rejected for a domain with money, state machines, and schema evolution; SQLAlchemy + Alembic directly.
- **Go / TypeScript:** no constraint here that beats Python + this team's stated preference.

## 2. Stack and dependencies (each with its verifier)

| Dependency | Why | Verifier before relying on it |
|---|---|---|
| FastAPI | routing, DTO validation, OpenAPI | endpoint tests: success / 422 / 401 / 403 |
| Pydantic v2 + pydantic-settings | boundary validation, typed config | invalid-input test; app fails fast on missing env |
| SQLAlchemy 2.x (sync) + psycopg 3 | explicit persistence, visible transactions | DB integration test against real Postgres |
| Alembic | migrations as code | `alembic upgrade head` + `downgrade -1` on throwaway DB in CI |
| httpx | outbound HTTP with explicit timeouts | delivery test asserting timeout raised at budget |
| argon2-cffi | password hashing (argon2id) | hash/verify round-trip test |
| structlog | JSON logs with bound request_id/org_id | log-capture test: sentinel secret never appears |
| pytest + testcontainers[postgres] | real-engine DB semantics | cross-tenant and idempotency tests run against Postgres |
| Ruff + mypy (strict on `app/`) | lint + types | CI gate |
| oasdiff (CI binary) | breaking-change detection on OpenAPI | diff vs `main` snapshot in CI |

Deliberately **not** added: Celery/Redis (outbox instead), any auth SaaS SDK (delayed decision), ORM soft-delete plugins, generic repository layers that hide transactions.

## 3. Domain and data model

Conventions: UUIDv7 primary keys (time-ordered, index-friendly), `timestamptz` everywhere, money as **integer minor units + ISO 4217 currency code**, every tenant-owned table carries `org_id` with a composite FK-and-filter discipline.

```sql
-- users are global identities; credentials are separable for future SSO
CREATE TABLE users (
    id            uuid PRIMARY KEY,
    email         text NOT NULL,
    name          text NOT NULL DEFAULT '',
    password_hash text,                          -- null once SSO-only
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX users_email_key ON users (lower(email));

CREATE TABLE organizations (
    id         uuid PRIMARY KEY,
    name       text NOT NULL,
    slug       text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE memberships (
    id         uuid PRIMARY KEY,
    org_id     uuid NOT NULL REFERENCES organizations(id),
    user_id    uuid NOT NULL REFERENCES users(id),
    role       text NOT NULL CHECK (role IN ('owner','admin','member')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (org_id, user_id)
);

CREATE TABLE api_keys (                          -- org-scoped machine auth
    id          uuid PRIMARY KEY,
    org_id      uuid NOT NULL REFERENCES organizations(id),
    name        text NOT NULL,
    token_hash  text NOT NULL UNIQUE,            -- sha256 of opaque token
    created_by  uuid NOT NULL REFERENCES users(id),
    last_used_at timestamptz,
    revoked_at  timestamptz
);

CREATE TABLE projects (
    id         uuid PRIMARY KEY,
    org_id     uuid NOT NULL REFERENCES organizations(id),
    name       text NOT NULL,
    status     text NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (org_id, name)
);

CREATE TABLE invoice_counters (                  -- per-org gapless-enough numbering
    org_id uuid PRIMARY KEY REFERENCES organizations(id),
    next_number bigint NOT NULL DEFAULT 1
);

CREATE TABLE invoices (
    id          uuid PRIMARY KEY,
    org_id      uuid NOT NULL REFERENCES organizations(id),
    project_id  uuid REFERENCES projects(id),
    number      text,                            -- assigned at finalize, e.g. INV-000042
    status      text NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft','open','paid','void')),
    currency    char(3) NOT NULL,
    total_minor bigint NOT NULL DEFAULT 0,
    issued_at   timestamptz,
    due_at      timestamptz,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (org_id, number)
);
CREATE INDEX invoices_org_status_idx ON invoices (org_id, status, created_at);

CREATE TABLE invoice_line_items (
    id                uuid PRIMARY KEY,
    invoice_id        uuid NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    description       text NOT NULL,
    quantity          numeric(12,3) NOT NULL,
    unit_amount_minor bigint NOT NULL,
    amount_minor      bigint NOT NULL
);

CREATE TABLE idempotency_keys (
    org_id        uuid NOT NULL REFERENCES organizations(id),
    key           text NOT NULL,
    fingerprint   text NOT NULL,                 -- sha256(method|path|body)
    response_code int,
    response_body jsonb,
    created_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (org_id, key)
);

CREATE TABLE webhook_endpoints (
    id          uuid PRIMARY KEY,
    org_id      uuid NOT NULL REFERENCES organizations(id),
    url         text NOT NULL,                   -- https only, SSRF-checked
    secret      text NOT NULL,                   -- whsec_..., shown once at creation
    event_types text[] NOT NULL,                 -- e.g. {'invoice.paid','project.created'}
    is_active   boolean NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE webhook_events (                    -- immutable event log
    id         uuid PRIMARY KEY,
    org_id     uuid NOT NULL REFERENCES organizations(id),
    type       text NOT NULL,
    payload    jsonb NOT NULL,                   -- versioned DTO, never raw ORM rows
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE webhook_deliveries (                -- the outbox
    id             uuid PRIMARY KEY,
    endpoint_id    uuid NOT NULL REFERENCES webhook_endpoints(id),
    event_id       uuid NOT NULL REFERENCES webhook_events(id),
    status         text NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending','succeeded','dead')),
    attempt_count  int NOT NULL DEFAULT 0,
    next_attempt_at timestamptz NOT NULL DEFAULT now(),
    last_status_code int,
    last_error     text,
    UNIQUE (endpoint_id, event_id)               -- enqueue is idempotent
);
CREATE INDEX deliveries_due_idx ON webhook_deliveries (next_attempt_at)
    WHERE status = 'pending';
```

## 4. Auth and tenant model

- **Human auth:** email + password (argon2id), opaque bearer session tokens — `secrets.token_urlsafe(32)`, stored as SHA-256 hash with expiry. No JWTs at launch: revocation is a `DELETE`, no key rotation ceremony. 
- **Machine auth:** org-scoped API keys (`sk_live_...`), hashed at rest, shown once.
- **Tenancy:** shared schema with `org_id` column. The tenant id is **always server-derived** from the authenticated principal (membership row or API key), never from the request body or a header. Every repository query filters by `(id, org_id)` — a missing filter is a P0.
- **Roles:** `owner` (billing, member management, org deletion), `admin` (all resources), `member` (projects read/write, invoices read). Deny by default: an endpoint without an explicit role requirement fails closed.
- Server-owned fields (`org_id`, `role`, `status`, `number`, totals) are never mass-assigned; each command DTO allowlists writable fields.

Tenant context as a FastAPI dependency:

```python
# app/auth/deps.py
@dataclass(frozen=True)
class OrgContext:
    org_id: UUID
    user_id: UUID | None   # None for API-key principals
    role: str

def current_org(
    request: Request,
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> OrgContext:
    principal = resolve_token(db, creds.credentials)   # session token or API key, by prefix
    if principal is None:
        raise ApiError(401, "unauthenticated")
    org_slug = request.path_params["org_slug"]
    ctx = load_membership(db, principal, org_slug)     # joins memberships/api_keys
    if ctx is None:
        raise ApiError(404, "not_found")               # 404, not 403: don't leak org existence
    structlog.contextvars.bind_contextvars(org_id=str(ctx.org_id))
    return ctx

def require_role(*roles: str):
    def check(ctx: OrgContext = Depends(current_org)) -> OrgContext:
        if ctx.role not in roles:
            raise ApiError(403, "forbidden")
        return ctx
    return check
```

Repository discipline (the only pattern that touches tenant-owned rows):

```python
def get_invoice(db: Session, org_id: UUID, invoice_id: UUID) -> Invoice | None:
    return db.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.org_id == org_id)
    ).scalar_one_or_none()
```

Delayed but designed-for: Postgres RLS as defense-in-depth (set `app.org_id` per request; policies on tenant tables). Additive later because all queries already filter.

## 5. API contract strategy

- URL shape: `/v1/orgs/{org_slug}/projects`, `/v1/orgs/{org_slug}/invoices`, `/v1/orgs/{org_slug}/webhook-endpoints`. Version in path; `v1` is a contract, breaking changes mean `v2`.
- **Explicit DTOs only.** ORM models never serialize into responses; every response model lists fields. Tests assert forbidden fields (`password_hash`, `secret`, `token_hash`) are absent.
- **Pagination from day one** on every collection: `?limit=` (default 20, max 100) + opaque cursor (`base64(created_at,id)`), stable `ORDER BY created_at, id`. Response envelope: `{"data": [...], "next_cursor": "..."}`.
- **One error contract** via a single exception handler:

```python
{"error": {"code": "invoice_not_editable", "message": "Only draft invoices can be edited.",
           "request_id": "req_9f2c..."}}
```

Stable machine codes; no stack traces; request id always present. Contract tests cover 400/401/403/404/409/422/429/500.
- **Idempotency:** all mutating endpoints with business side effects accept `Idempotency-Key` (required for invoice creation/finalization via API keys). Implementation: insert into `idempotency_keys` (PK conflict → replay stored response; same key + different fingerprint → `409 idempotency_key_reuse`).

```python
# app/http/idempotency.py (dependency used by mutating routes)
def idempotency_guard(ctx, request, db) -> StoredResponse | IdemTicket:
    key = request.headers.get("Idempotency-Key")
    if not key:
        raise ApiError(422, "idempotency_key_required")
    fp = sha256(f"{request.method}|{request.url.path}|{body_bytes}").hexdigest()
    try:
        db.execute(insert(IdempotencyKey).values(org_id=ctx.org_id, key=key, fingerprint=fp))
        db.commit()
        return IdemTicket(key=key)                    # first time: proceed, store response after
    except IntegrityError:
        db.rollback()
        row = db.get(IdempotencyKey, (ctx.org_id, key))
        if row.fingerprint != fp:
            raise ApiError(409, "idempotency_key_reuse")
        if row.response_code is None:
            raise ApiError(409, "request_in_progress")  # concurrent duplicate
        return StoredResponse(row.response_code, row.response_body)
```

- OpenAPI exported to `openapi.json` in CI; `oasdiff breaking` against `main` fails the build on breaking changes.

## 6. Invoices: state machine and numbering

States: `draft → open → paid | void` (and `draft → void`). Transitions are explicit endpoints (`POST .../invoices/{id}/finalize`, `/pay`, `/void`), not `PATCH status`. Illegal transitions return `409 invoice_invalid_transition`.

- Line items editable only in `draft`; totals recomputed server-side (`amount_minor = round(quantity * unit_amount_minor)`), never accepted from the client.
- Invoice number assigned at finalize inside one short transaction, using the per-org counter with a row lock — no gaps from drafts, no cross-org contention:

```python
def finalize_invoice(db: Session, org_id: UUID, invoice_id: UUID) -> Invoice:
    with db.begin():
        inv = db.execute(
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.org_id == org_id)
            .with_for_update()
        ).scalar_one_or_none()
        if inv is None:
            raise ApiError(404, "not_found")
        if inv.status != "draft":
            raise ApiError(409, "invoice_invalid_transition")
        n = db.execute(
            update(InvoiceCounter)
            .where(InvoiceCounter.org_id == org_id)
            .values(next_number=InvoiceCounter.next_number + 1)
            .returning(InvoiceCounter.next_number - 1)
        ).scalar_one()
        inv.number, inv.status, inv.issued_at = f"INV-{n:06d}", "open", func.now()
        emit_event(db, org_id, "invoice.finalized", InvoiceDTO.from_model(inv))  # same txn
    return inv
```

Assumption stated: no payment-provider integration in scope. `paid` is recorded manually or via a future Stripe integration, which would arrive through the same outbox/state-machine path (never a DB transaction around a Stripe call).

## 7. Webhooks: transactional outbox + dispatcher

**Emit** (inside the same transaction as the domain write — this is the whole point):

```python
def emit_event(db: Session, org_id: UUID, type_: str, payload: BaseModel) -> None:
    event = WebhookEvent(id=uuid7(), org_id=org_id, type=type_,
                         payload=payload.model_dump(mode="json"))
    db.add(event)
    for ep in active_endpoints_for(db, org_id, type_):
        db.add(WebhookDelivery(id=uuid7(), endpoint_id=ep.id, event_id=event.id))
```

If the transaction rolls back, no event and no deliveries exist. No lost or phantom webhooks.

**Dispatcher** (separate process, same codebase):

```python
BACKOFF = [30, 120, 600, 3600, 7200, 14400, 43200, 86400]  # seconds; then dead
CONCURRENCY = 8                                             # bounded thread pool

def claim_due(db: Session, limit: int = 20) -> list[WebhookDelivery]:
    with db.begin():
        rows = db.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.status == "pending",
                   WebhookDelivery.next_attempt_at <= func.now())
            .order_by(WebhookDelivery.next_attempt_at)
            .limit(limit)
            .with_for_update(skip_locked=True)          # safe with N dispatcher replicas
        ).scalars().all()
        for d in rows:                                   # push out so a crash mid-send
            d.next_attempt_at = func.now() + timedelta(minutes=5)  # just retries later
        return rows

def attempt(db_factory, delivery_id: UUID) -> None:
    # 1) load delivery+event+endpoint; 2) send OUTSIDE any transaction; 3) record result
    body = canonical_json(event.payload_envelope())      # {"id","type","created_at","data"}
    ts = int(time.time())
    sig = hmac.new(endpoint.secret.encode(), f"{ts}.{body}".encode(), "sha256").hexdigest()
    try:
        resp = httpx.post(
            endpoint.url, content=body,
            headers={"Content-Type": "application/json",
                     "Webhook-Id": str(delivery.id),          # receiver dedupe key
                     "Webhook-Signature": f"t={ts},v1={sig}"},
            timeout=httpx.Timeout(connect=3, read=7, write=7, pool=3),
            follow_redirects=False,
        )
        ok = 200 <= resp.status_code < 300
    except httpx.HTTPError as exc:
        ok, resp = False, None
    with db_factory() as db, db.begin():
        d = db.get(WebhookDelivery, delivery_id, with_for_update=True)
        d.attempt_count += 1
        d.last_status_code = resp.status_code if resp else None
        if ok:
            d.status = "succeeded"
        elif d.attempt_count >= len(BACKOFF):
            d.status = "dead"                            # visible in UI; manual redeliver endpoint
        else:
            base = BACKOFF[d.attempt_count - 1]
            d.next_attempt_at = func.now() + timedelta(
                seconds=base + random.uniform(0, base * 0.25))   # jitter
```

Delivery semantics documented to customers: **at-least-once**, ordered-best-effort; dedupe on `Webhook-Id`; signature verification with 5-minute timestamp tolerance (replay protection); 2xx within 10 s counts as received.

**SSRF protection** (endpoint URLs are customer-controlled): at registration and again at send time — `https` scheme only, resolve DNS and reject loopback/private/link-local/metadata ranges (`ipaddress.ip_address(a).is_private/is_loopback/is_link_local`), no redirect following, response body read capped (we only need the status code). Verifier: test registering `https://169.254.169.254/` and `https://internal.local/` is rejected.

## 8. Reliability defaults (server baseline included)

- **Inbound:** uvicorn behind a reverse proxy; proxy enforces request read timeout (30 s) and max body size (1 MiB); `--timeout-keep-alive 5`; `--limit-concurrency` sized to DB pool.
- **DB:** pool `size=10, max_overflow=5, pool_pre_ping, pool_recycle=1800`; per-role `statement_timeout=10s`, `lock_timeout=3s`, `idle_in_transaction_session_timeout=30s`. Dispatcher role gets its own budget.
- **Outbound HTTP:** httpx with explicit connect/read/write/pool timeouts everywhere; no default-timeout client is ever constructed.
- **Retries:** only on idempotent-or-keyed operations; bounded attempts, exponential backoff with jitter, `Retry-After` respected. Webhook schedule above is the reference implementation.
- **No in-process fire-and-forget:** critical side effects go through the outbox; `BackgroundTasks`/`asyncio.create_task` are banned for anything that must happen.
- **Graceful shutdown:** dispatcher traps SIGTERM, stops claiming, drains in-flight sends (claimed rows self-heal via the pushed-out `next_attempt_at` if it dies hard).

## 9. Observability baseline

- structlog JSON logs; middleware generates `request_id` (`req_` + uuid7, echoed in every response and error body) and binds `request_id`, `org_id`, route template, status, duration.
- **Log allowlist:** never log request bodies, tokens, secrets, webhook payloads, or emails; log ids and decisions. Redaction test with a sentinel secret is in the suite.
- Security events are explicitly tagged (`event="auth.denied"`, `event="webhook.signature_invalid"`, `event="tenant.denied"`), not generic warnings.
- `/healthz` (process up) and `/readyz` (DB `SELECT 1`); dispatcher heartbeats a `dispatcher_last_tick` row — first alert: "webhook deliveries pending > 15 min" with a runbook note (owner: whoever is on call of the 2; action: check dispatcher process, then dead-letter counts).
- Metrics via OpenTelemetry later; labels restricted to route template / status class / event type (bounded). Not blocking launch.

## 10. Database and migration strategy

- Alembic owns 100% of schema; `alembic check` in CI fails if models drift from migrations.
- Migration template sets `lock_timeout = '3s'` and `statement_timeout = '60s'`.
- Rules from day one (cheap now, vital at first real traffic): expand/contract for renames; `CREATE INDEX CONCURRENTLY` for indexes on non-empty tables (non-transactional migration); every migration has a real `downgrade()` or an explicit forward-fix note in the docstring.
- CI proves `upgrade head` then `downgrade -1` + `upgrade head` on a throwaway Postgres.

## 11. Testing and CI baseline

Test pyramid (pytest, real Postgres via testcontainers):

| Surface | Required test |
|---|---|
| every public endpoint | success + validation error + unauthenticated + wrong-role |
| tenant boundary | seeded org A/org B; org B token reading/mutating A's project, invoice, endpoint → 404 |
| idempotency | duplicate `Idempotency-Key` → one invoice, same response; reused key + different body → 409 |
| invoice state machine | each illegal transition → 409; finalize assigns unique sequential numbers under 10 concurrent finalizes |
| webhook outbox | domain txn rollback → no delivery row; duplicate dispatcher claim (two claimers) → one send |
| webhook retry/dead-letter | failing receiver (local test server) → backoff schedule honored, `dead` after max attempts |
| SSRF | private/loopback/metadata endpoint URLs rejected at registration and send |
| DTO leaks | responses asserted to not contain `password_hash`, `secret`, `token_hash` |
| logs | sentinel secret in request never appears in captured log output |

CI (GitHub Actions), every PR: `ruff check` → `mypy app` → `pytest` (Postgres service container) → `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` on throwaway DB → export `openapi.json` and `oasdiff breaking origin/main`. Merge blocked on any failure. Total wall time target < 5 min so a 2-person team actually keeps it green.

## 12. Project layout

```
app/
  main.py            # app factory, middleware, error handler, routers
  config.py          # pydantic-settings; fails fast
  db.py              # engine, Session factory, get_db dependency
  errors.py          # ApiError + single exception handler
  auth/              # tokens, password hashing, deps (current_org, require_role)
  http/              # pagination, idempotency guard, request-id middleware
  orgs/  projects/  invoices/  webhooks/
      models.py routes.py schemas.py service.py   # per-domain vertical slices
  dispatcher/
      main.py        # claim loop, bounded pool, shutdown handling
migrations/          # alembic
tests/
  conftest.py        # testcontainers Postgres, app+client fixtures, org/user factories
  test_tenancy.py test_idempotency.py test_invoices.py test_webhooks.py ...
pyproject.toml       # uv-managed; ruff+mypy config
.github/workflows/ci.yml
```

Vertical slices (models+routes+service per domain) over layer-first folders: with 5 domains and 2 people, locality beats abstraction. No generic repository base class; queries stay visible.

## 13. First irreversible decisions — and what we deliberately delay

Locked now (expensive to change later):
1. **Shared-schema tenancy with `org_id`** — migrating to schema-per-tenant later is a project; this is the right call below ~thousands of orgs.
2. **UUIDv7 ids, money as integer minor units, `timestamptz`** — data-shape decisions that poison everything if wrong.
3. **Webhook contract** (envelope shape, `Webhook-Id`/`Webhook-Signature` scheme, at-least-once semantics, event type naming `resource.verb`) — customers write code against this.
4. **`/v1` path versioning and the error envelope** — consumer-visible forever.
5. **Users separate from credentials/memberships** — keeps SSO and multi-org membership additive.

Deliberately delayed, with the seam that keeps them cheap:
- **SSO/OIDC** — delayed; seam: nullable `password_hash`, auth resolution isolated in `auth/`.
- **Celery/Redis** — delayed; seam: enqueue is an outbox insert; swap the dispatcher, not the emitters.
- **Postgres RLS** — delayed; seam: every query already filters by `org_id`, policies are additive.
- **Async SQLAlchemy** — delayed; seam: sync sessions confined to `get_db` + services.
- **Payment provider** — delayed; seam: invoice state machine + outbox already model external settlement.
- **Rate limiting** — proxy-level counter at launch; per-org token bucket in Postgres/Redis when needed.

## 14. Implementation plan (team of 2, ~4 weeks to usable)

1. **Week 1 — skeleton with proof:** repo, config, db, error contract, request-id logging, Alembic baseline, CI fully green including migration round-trip. Users/orgs/memberships + auth deps + cross-tenant denial tests.
2. **Week 2 — projects + pagination + idempotency guard**; DTO-leak and pagination-cap tests; `oasdiff` gate wired.
3. **Week 3 — invoices:** state machine, counters, line items, concurrent-finalize test.
4. **Week 4 — webhooks:** endpoints CRUD (SSRF checks), outbox emit in invoice/project services, dispatcher with retry/dead-letter, signature docs for customers, duplicate-claim and rollback tests. Manual redelivery endpoint.

## Proof contract statement

Design-only engagement: there is no repository or runtime in this environment, so **no verifier commands were executed**. Nothing here is claimed as tested. The verifiers that gate each milestone are enumerated in sections 2, 10, and 11 (per-dependency verifiers, migration round-trip in CI, and the test matrix); the Week-1 exit criterion is the first executed proof (CI green including `alembic upgrade/downgrade` and cross-tenant denial tests against real Postgres).

Residual risks to raise with product before build: whether invoices need tax/discount lines (schema impact), whether gapless invoice numbering is a legal requirement in target jurisdictions (current design is gapless per-org but requires the counter lock — confirm acceptable), and expected webhook volume (drives the Celery decision point).

## Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md (content delivered by skill invocation)
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/stack-recipes.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/library-decisions.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/api-contracts.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/auth-tenancy-security.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/observability-ops.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/testing-verification.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
````
