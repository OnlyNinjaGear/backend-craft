# forward-test 001: start-mode

> **Run-integrity note (2026-07-10):** tested agents in this batch were not
> isolated; implementation-shaped tasks edited the shared fixtures in place
> while sibling tests were reading them. Fixtures were restored from pristine
> snapshots afterwards and re-verified (see ../docs/FORWARD_TESTS.md isolation rules).
> Design-only tests (001, 007) are unaffected.

Date: 2026-07-10
Fixture: none (design task)
Score: 4/4
Generic advice: False
Verifier quality (judge): Strong. Every non-trivial design choice names its verifier: duplicate-POST idempotency test, cross-tenant 404 tests seeded with two orgs, SKIP LOCKED double-worker delivery test, retry/backoff/dead-letter tests against a stub HTTP server, migration up/down/up plus single-head check, log redaction test, oasdiff contract gate. Greenfield untestability is stated explicitly with the exact commands (pytest, alembic upgrade/downgrade, ruff, mypy, oasdiff) required to pass on the first scaffold commit, satisfying the Final proof contract's untestability clause rather than dodging it.

## Prompt

```text
Design the backend foundation for a small B2B SaaS: users, organizations, projects, invoices, and webhooks. Use Python unless there is a strong reason not to. I want something maintainable for a team of 2.
```

## References loaded (from agent's 'Files read')

- SKILL.md
- references/stack-recipes.md
- references/library-decisions.md
- references/api-contracts.md
- references/auth-tenancy-security.md
- references/persistence-migrations.md
- references/reliability-async.md
- references/observability-ops.md
- references/testing-verification.md
- references/language-adapters.md

## Judge summary

Exemplary Start-mode execution. The agent ran the Impact Read before any stack talk, loaded exactly the nine references SKILL.md routes for Start mode, and delivered every Start-mode deliverable: stack with named rejected alternatives and concrete tradeoffs, dependency table where each library states the failure it removes and its first verifier (matching the library-decisions.md gate and its Review-output format, including the 'do not guess docs from memory' rule for argon2), tenant model decided first and enforced through one dependency plus a CI lint, money as integer minor units, versioned webhook envelope/signature named as the least-changeable contract, transactional outbox with SKIP LOCKED instead of premature Celery/Redis, idempotency keys with fingerprint checks, expand/contract migrations with up/down/up CI proof, observability with cardinality and redaction rules, and a proof matrix tying each risk to a named test. It also produced the architecture record the Scaffold warning requires (chosen/rejected recipes, irreversible decisions, first verifiers, risks needing product input). The final proof contract is honored via the explicit-untestability clause with named compensating commands. Non-obvious failure modes (per-send SSRF re-resolution, worker lease recovery, single-head Alembic guard, no network in transactions) push this to a 4. No skill edits needed from this run.

## Misses

- none

## Changes needed in skill/reference/failure card

- none

## Tested agent answer (verbatim)

````text
All Start-mode references are loaded. This is a greenfield task (no repo), so I deliver the architecture record, design, and code sketches directly below.

---

# Backend foundation design: small B2B SaaS (users, orgs, projects, invoices, webhooks)

## 0. Impact Read (blast radius before code)

1. **Public contracts:** every endpoint is new — the v1 API surface, the error envelope, the webhook event envelope, and the webhook signature scheme are all contracts being created now. The webhook envelope and signature are consumed by *customers'* code, so they are the least changeable artifacts in the system.
2. **Data:** all tables are new. Money (invoices) and tenant-owned records are involved — data-model mistakes here (float money, missing `org_id`) are P0-class and expensive to reverse.
3. **Principals/tenant boundaries:** multi-tenant by organization. Users are global identities; every resource row is org-owned. Cross-tenant leakage is the top standing risk.
4. **Side effects that can repeat/outlive requests:** webhook deliveries (retried, at-least-once), invoice creation/state transitions (client-retryable POSTs). Both need idempotency designed before launch, not after.
5. **Existing tests/checkers:** none — the CI baseline below is part of the deliverable.

Assumptions (stated, not asked): single region, Postgres available, ~10s of orgs at launch, invoices are records the SaaS issues (no card processing in scope — payment-provider integration is deferred), team of 2 owns dev + ops.

---

## 1. Architecture record

**Chosen recipe: Python — FastAPI + Pydantic v2 + SQLAlchemy 2.x + Alembic + Postgres**, deployed as a modular monolith with two processes from one image: the API and a webhook-delivery worker.

Why this fits *this* product and team:

- API-first B2B product: explicit request/response DTOs and generated OpenAPI are direct leverage for customers integrating against you.
- Webhooks demand explicit control over retries, timeouts, signing, and an outbox — visible semantics beat framework magic here.
- Tenancy is enforced in one obvious place (a FastAPI dependency + `(id, org_id)` query discipline).
- SQLAlchemy 2.x + Alembic keep transactions, locks, and migrations reviewable — important for the invoices tables.

**Rejected alternatives and the concrete tradeoff:**

- **Django + DRF** — the serious contender. Its admin, auth, and migrations are real leverage for CRUD-heavy B2B. Rejected because: (a) the integration-facing half of this product (webhooks, idempotent invoice API, typed contracts) is where the risk lives, and DRF generic serializers make property-leak/mass-assignment mistakes easy defaults; (b) the team of 2 gets more value from one explicit stack than from admin UI we can approximate later (e.g. `sqladmin` behind VPN if needed). If the product pivots to heavy back-office CRUD, revisit — do not bolt half a Django into FastAPI.
- **Go (chi + pgx)** — great operationally, rejected only because Python was requested and there is no throughput constraint that overrides team preference.
- **Async SQLAlchemy end-to-end** — rejected for launch. The service is DB-bound CRUD; sync sessions in FastAPI (threadpool) avoid the shared-`AsyncSession` and cancellation-propagation failure classes entirely for a team of 2. Async is not a quality badge. Escape hatch: the worker already uses HTTPX and can go async independently if webhook fan-out grows.
- **Celery/Redis for jobs** — rejected at launch per the dependency gate: a Postgres outbox with `FOR UPDATE SKIP LOCKED` gives durable, restart-surviving, at-least-once delivery with zero new infrastructure. Escape hatch: if job types multiply or throughput demands it, move the *dispatch* to Celery/arq; the outbox tables stay.

**First irreversible decisions (and how each is delayed or contained):**

| Decision | Choice | Why hard to reverse | Containment |
|---|---|---|---|
| Tenancy model | Shared schema, `org_id` column on every tenant-owned table | Row layout touches everything | Centralize scoping in one dependency + repo helpers; Postgres RLS can be layered on later as defense-in-depth without schema change |
| Money representation | `BIGINT` minor units + `CHAR(3)` currency, never float/numeric-as-float | Backfilling money is dangerous | Non-delayable; decided now |
| Primary keys | UUIDv7, exposed publicly | Public IDs leak into customer systems | UUID avoids enumeration; v7 keeps index locality |
| Webhook envelope + signature scheme | Versioned envelope (`{id, type, created_at, data}`), `t=...,v1=HMAC` signature | Customers write code against it | Version fields (`v1=`) in the signature header and `type` versioning (`invoice.paid`) allow additive evolution |
| Invoice numbering | Per-org sequence via counter row | Numbers on issued invoices are legally sticky | Counter table isolates the mechanism |
| API versioning | `/v1` prefix from day one | Retro-adding versioning breaks clients | Trivial now, painful later |

**Deliberately delayed:** payment-provider integration, RLS, Celery, OpenTelemetry backend choice (instrumentation hooks in from day one, exporter behind env flag), multi-region, SSO/OAuth (start with password + org API keys).

---

## 2. Dependency defaults (each with its verifier)

| Library | Why (per dependency gate) | First verifier |
|---|---|---|
| FastAPI | OpenAPI generation, DI for auth/tenant/session | endpoint tests: success, 422, 401/404-denial |
| Pydantic v2 + pydantic-settings | validated boundaries and config; kills mass-assignment by construction | invalid-input test; app fails fast on missing env |
| SQLAlchemy 2.x (sync) | reviewable transactions/locks | DB integration test against real Postgres |
| Alembic | tracked, reviewable migrations | `alembic upgrade head` + `downgrade -1` on throwaway DB in CI |
| Postgres 16 | transactional outbox, `SKIP LOCKED`, partial indexes | Testcontainers-backed test suite |
| HTTPX | outbound HTTP with explicit timeouts, redirects off | webhook delivery test with stub server + timeout test |
| argon2-cffi | password hashing primitive that is easy to get wrong by hand | hash/verify round-trip test (pin version; check docs at install time — do not guess API from memory) |
| structlog (or stdlib JSON logging) | structured logs with bound request_id | smoke test asserts request_id present, secrets absent |
| pytest + testcontainers[postgres] | real DB semantics (constraints, SKIP LOCKED, uniques) | the suite itself |
| Ruff + mypy (strict on `src/`) | drift control for a 2-person team | CI gate |

Not added (per the gate): Redis, Celery, message broker, ORM-level multitenancy plugins, API gateway. Each hides semantics we must reason about or adds ops burden without removing a current failure mode.

---

## 3. Domain and data model

```
users               id, email (citext unique), password_hash, created_at
organizations       id, name, slug (unique), created_at
memberships         id, org_id FK, user_id FK, role ('owner'|'admin'|'member'),
                    UNIQUE (org_id, user_id)
api_keys            id, org_id FK, name, token_hash (unique), created_by FK users,
                    last_used_at, revoked_at
org_counters        org_id PK/FK, invoice_seq BIGINT NOT NULL DEFAULT 0

projects            id, org_id FK, name, status, created_at, archived_at
                    INDEX (org_id, created_at DESC)

invoices            id, org_id FK, project_id FK NULL, number BIGINT,
                    status ('draft'|'open'|'paid'|'void'),
                    currency CHAR(3), amount_total_minor BIGINT,
                    issued_at, due_at, paid_at, created_at
                    UNIQUE (org_id, number); INDEX (org_id, status, created_at DESC)
invoice_line_items  id, invoice_id FK, description, quantity NUMERIC(12,3),
                    unit_amount_minor BIGINT, amount_minor BIGINT, position INT

idempotency_keys    id, org_id FK, key TEXT, request_fingerprint TEXT,
                    response_status INT NULL, response_body JSONB NULL,
                    created_at, locked_until
                    UNIQUE (org_id, key)

outbox_events       id (uuidv7), org_id FK, event_type TEXT, payload JSONB, created_at
webhook_endpoints   id, org_id FK, url, secret (encrypted at rest or vaulted),
                    is_active BOOL, event_types TEXT[], consecutive_failures INT,
                    created_at, disabled_at
webhook_deliveries  id, event_id FK outbox_events, endpoint_id FK, org_id FK,
                    status ('pending'|'delivering'|'succeeded'|'failed'),
                    attempts INT, next_attempt_at, lease_expires_at,
                    last_status_code INT NULL, last_error TEXT NULL
                    PARTIAL INDEX (next_attempt_at) WHERE status='pending'
```

Rules baked in:

- Every tenant-owned table carries `org_id`; every FK pair that crosses tables inside a tenant (e.g. `invoices.project_id`) is *also* checked to be same-org in the service layer.
- Money: integers in minor units; totals computed server-side; `quantity` is the only NUMERIC.
- Invoice state machine transitions are the only way `status` changes: `draft→open`, `open→paid`, `draft|open→void`. No free-form PATCH of `status`.
- Deletes: projects archive (soft via `archived_at`); invoices are never deleted, only voided; users/orgs deletion is an offboarding procedure, not an endpoint, at launch.

---

## 4. Project layout

```
saas-backend/
  pyproject.toml            # uv or pip-tools; pinned lockfile committed
  alembic.ini
  migrations/versions/
  docker-compose.yml        # postgres:16 for dev
  Dockerfile                # one image, two entrypoints
  src/app/
    main.py                 # app factory, routers, error handlers, middleware
    core/
      config.py             # pydantic-settings
      db.py                 # engine, session-per-request dependency
      security.py           # password hashing, token hashing, current_user
      tenancy.py            # org membership dependency, TenantContext
      errors.py             # error envelope + exception handlers
      idempotency.py
      pagination.py
      logging.py            # structlog config, request-id middleware
    accounts/  models.py schemas.py router.py service.py
    projects/  models.py schemas.py router.py service.py
    invoicing/ models.py schemas.py router.py service.py
    webhooks/  models.py schemas.py router.py outbox.py signing.py ssrf.py worker.py
  tests/
    conftest.py             # testcontainers postgres, app+client fixtures, org/user seeds
    test_tenancy.py test_projects.py test_invoices.py
    test_idempotency.py test_webhooks_worker.py test_migrations.py
```

Module boundaries follow product domains, not tables. Cross-domain writes (e.g. invoicing emits webhook events) go through `webhooks/outbox.py`'s one function, inside the caller's transaction.

---

## 5. Code sketches

### 5.1 Config and DB session (core/config.py, core/db.py)

```python
# core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")
    database_url: str                      # no default: fail fast
    env: str = "dev"
    webhook_timeout_seconds: float = 5.0
    webhook_max_attempts: int = 8
    statement_timeout_ms: int = 5_000

settings = Settings()
```

```python
# core/db.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=10)

@event.listens_for(engine, "connect")
def _set_timeouts(dbapi_conn, _):
    with dbapi_conn.cursor() as cur:   # every session gets a statement budget
        cur.execute(f"SET statement_timeout = {settings.statement_timeout_ms}")
        cur.execute("SET lock_timeout = '2s'")

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def get_db() -> Iterator[Session]:     # one session per request, always closed
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 5.2 Auth + tenancy dependency (core/security.py, core/tenancy.py)

Tokens are opaque, stored hashed (`sha256`), never logged. Tenant id is **always server-derived** from the path + membership row — client bodies can never carry `org_id`.

```python
# core/tenancy.py
from dataclasses import dataclass

ROLE_RANK = {"member": 0, "admin": 1, "owner": 2}

@dataclass(frozen=True)
class TenantContext:
    org_id: UUID
    user_id: UUID
    role: str

def org_context(
    org_id: UUID,                                  # from path /v1/orgs/{org_id}/...
    user: User = Depends(current_user),            # 401 if token invalid
    db: Session = Depends(get_db),
) -> TenantContext:
    m = db.execute(
        select(Membership.role)
        .where(Membership.org_id == org_id, Membership.user_id == user.id)
    ).scalar_one_or_none()
    if m is None:
        # 404, not 403: do not confirm the org exists to non-members
        raise ApiError(404, "not_found", "Resource not found")
    return TenantContext(org_id=org_id, user_id=user.id, role=m)

def require_role(minimum: str):
    def dep(ctx: TenantContext = Depends(org_context)) -> TenantContext:
        if ROLE_RANK[ctx.role] < ROLE_RANK[minimum]:
            raise ApiError(403, "forbidden", "Insufficient role")
        return ctx
    return dep
```

Query discipline (the tenant filter that must never be forgotten): **every** fetch of a tenant-owned row goes through a helper that takes the context:

```python
def get_owned(db: Session, model, ctx: TenantContext, obj_id: UUID):
    row = db.execute(
        select(model).where(model.id == obj_id, model.org_id == ctx.org_id)
    ).scalar_one_or_none()
    if row is None:
        raise ApiError(404, "not_found", "Resource not found")
    return row
```

A Semgrep/ast-grep rule in CI flags any `select(<TenantModel>)` in `src/app` that lacks an `org_id ==` comparison — cheap guardrail for a 2-person team.

### 5.3 Error contract (core/errors.py)

One envelope for every non-2xx response; no stack traces; request id always present.

```python
class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message

# handler registered on the app:
def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message,
                           "request_id": request.state.request_id}},
    )
# plus handlers mapping RequestValidationError -> 422 {"code": "validation_error", ...}
# and Exception -> 500 {"code": "internal_error"} (details only in logs)
```

### 5.4 DTOs and a tenant-scoped router (projects)

Explicit DTOs; ORM models never returned; create/update/read schemas are separate; server-owned fields absent from input schemas by construction.

```python
# projects/schemas.py
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)     # note: no org_id, no status

class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    status: str
    created_at: datetime                                 # explicit allowlist of fields

# projects/router.py
router = APIRouter(prefix="/v1/orgs/{org_id}/projects", tags=["projects"])

@router.post("", status_code=201, response_model=ProjectOut)
def create_project(
    body: ProjectCreate,
    ctx: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    project = Project(org_id=ctx.org_id, name=body.name, status="active")
    db.add(project); db.commit()
    return project

@router.get("", response_model=Page[ProjectOut])
def list_projects(
    ctx: TenantContext = Depends(org_context),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, le=100),              # cap at launch
    cursor: UUID | None = None,                          # uuidv7 => time-ordered cursor
):
    q = (select(Project)
         .where(Project.org_id == ctx.org_id, Project.archived_at.is_(None))
         .order_by(Project.id.desc()).limit(limit + 1))
    if cursor:
        q = q.where(Project.id < cursor)
    rows = db.execute(q).scalars().all()
    return Page.build(rows, limit)   # {"items": [...], "next_cursor": id-or-null}
```

Pagination is on every collection endpoint from day one (`Page` envelope with `next_cursor`), so adding it never becomes a breaking change.

### 5.5 Idempotency for mutating endpoints (core/idempotency.py)

`Idempotency-Key` header is **required** on `POST /invoices` and on invoice state transitions (the endpoints clients retry). Persist key + fingerprint + final response; replay duplicates; reject key reuse with a different body.

```python
def begin_idempotent(db: Session, ctx: TenantContext, key: str, request: Request,
                     body_bytes: bytes) -> JSONResponse | None:
    fp = hashlib.sha256(
        f"{request.method}:{request.url.path}:".encode() + body_bytes
    ).hexdigest()
    try:
        db.execute(insert(IdempotencyKey).values(
            org_id=ctx.org_id, key=key, request_fingerprint=fp,
            locked_until=now() + timedelta(seconds=30)))
        db.commit()
        return None                                   # first time: proceed
    except IntegrityError:
        db.rollback()
        row = db.execute(select(IdempotencyKey).where(
            IdempotencyKey.org_id == ctx.org_id, IdempotencyKey.key == key)
        ).scalar_one()
        if row.request_fingerprint != fp:
            raise ApiError(422, "idempotency_key_reuse",
                           "Key was used with a different request")
        if row.response_status is None:               # concurrent in-flight call
            raise ApiError(409, "request_in_progress", "Retry shortly")
        return JSONResponse(status_code=row.response_status,
                            content=row.response_body)   # replay stored result

def finish_idempotent(db, ctx, key, status: int, body: dict) -> None:
    db.execute(update(IdempotencyKey)
               .where(IdempotencyKey.org_id == ctx.org_id, IdempotencyKey.key == key)
               .values(response_status=status, response_body=body))
```

Verifier: test fires the same POST twice → exactly one invoice row, identical responses; same key + different body → 422.

### 5.6 Invoices: numbering, state machine, and event emission in one transaction

```python
# invoicing/service.py
def create_invoice(db: Session, ctx: TenantContext, data: InvoiceCreate) -> Invoice:
    if data.project_id is not None:
        get_owned(db, Project, ctx, data.project_id)   # same-org check on cross-FK

    number = db.execute(text(
        "UPDATE org_counters SET invoice_seq = invoice_seq + 1 "
        "WHERE org_id = :org RETURNING invoice_seq"), {"org": ctx.org_id}
    ).scalar_one()                                     # row lock scoped to this org only

    items = [InvoiceLineItem(
        description=i.description, quantity=i.quantity, position=n,
        unit_amount_minor=i.unit_amount_minor,
        amount_minor=round(i.unit_amount_minor * i.quantity),
    ) for n, i in enumerate(data.line_items)]

    invoice = Invoice(
        org_id=ctx.org_id, project_id=data.project_id, number=number,
        status="draft", currency=data.currency,
        amount_total_minor=sum(i.amount_minor for i in items),  # server-computed
        line_items=items,
    )
    db.add(invoice)
    emit_event(db, ctx.org_id, "invoice.created", invoice_payload(invoice))
    db.commit()                                        # invoice + counter + outbox: atomic
    return invoice

TRANSITIONS = {("draft", "open"), ("open", "paid"), ("draft", "void"), ("open", "void")}

def transition_invoice(db, ctx, invoice_id: UUID, target: str) -> Invoice:
    invoice = db.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.org_id == ctx.org_id)
        .with_for_update()                             # serialize concurrent transitions
    ).scalar_one_or_none()
    if invoice is None:
        raise ApiError(404, "not_found", "Resource not found")
    if (invoice.status, target) not in TRANSITIONS:
        raise ApiError(409, "invalid_transition",
                       f"Cannot move invoice from {invoice.status} to {target}")
    invoice.status = target
    if target == "open": invoice.issued_at = now()
    if target == "paid": invoice.paid_at = now()
    emit_event(db, ctx.org_id, f"invoice.{target}", invoice_payload(invoice))
    db.commit()
    return invoice
```

Note the transaction shape: DB writes + outbox insert commit together; **no network call is inside the transaction** — delivery happens in the worker.

### 5.7 Webhooks: outbox, fan-out, signing, SSRF guard, worker

```python
# webhooks/outbox.py — called inside the caller's transaction
def emit_event(db: Session, org_id: UUID, event_type: str, data: dict) -> None:
    event = OutboxEvent(id=uuid7(), org_id=org_id, event_type=event_type,
                        payload={"id": None, "type": event_type,
                                 "created_at": now().isoformat(), "data": data})
    event.payload["id"] = str(event.id)
    db.add(event)
    endpoints = db.execute(select(WebhookEndpoint.id).where(
        WebhookEndpoint.org_id == org_id,
        WebhookEndpoint.is_active.is_(True),
        WebhookEndpoint.event_types.contains([event_type]))).scalars().all()
    for ep_id in endpoints:
        db.add(WebhookDelivery(event_id=event.id, endpoint_id=ep_id, org_id=org_id,
                               status="pending", attempts=0, next_attempt_at=now()))
```

```python
# webhooks/signing.py — the customer-facing contract; versioned from day one
def sign(secret: str, body: bytes, ts: int) -> str:
    mac = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256)
    return f"t={ts},v1={mac.hexdigest()}"
# Headers sent: X-Webhook-Signature, X-Webhook-Event-Id (consumer dedupe key),
# X-Webhook-Event-Type. Docs tell consumers: verify HMAC, reject |now-t| > 5min,
# dedupe on event id (delivery is at-least-once).
```

```python
# webhooks/ssrf.py — endpoint URLs are user-controlled: validate at registration AND per send
PRIVATE_NETS = [ip_network(n) for n in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8",
    "169.254.0.0/16", "::1/128", "fc00::/7", "fe80::/10", "100.64.0.0/10")]

def assert_url_safe(url: str) -> None:
    p = urlparse(url)
    if p.scheme != "https" or not p.hostname:
        raise WebhookUrlError("Webhook URLs must be https")
    for _, _, _, _, sockaddr in socket.getaddrinfo(p.hostname, p.port or 443):
        if any(ip_address(sockaddr[0]) in net for net in PRIVATE_NETS):
            raise WebhookUrlError("Webhook URL resolves to a private address")
```

```python
# webhooks/worker.py — separate process: `python -m app.webhooks.worker`
BACKOFF_BASE, BACKOFF_CAP = 30, 6 * 3600  # seconds

def claim_batch(db: Session, batch: int = 20) -> list[WebhookDelivery]:
    rows = db.execute(
        select(WebhookDelivery)
        .where(or_(
            and_(WebhookDelivery.status == "pending",
                 WebhookDelivery.next_attempt_at <= now()),
            and_(WebhookDelivery.status == "delivering",       # crashed-worker recovery
                 WebhookDelivery.lease_expires_at <= now())))
        .order_by(WebhookDelivery.next_attempt_at)
        .limit(batch)
        .with_for_update(skip_locked=True)                     # safe multi-worker
    ).scalars().all()
    for d in rows:
        d.status, d.lease_expires_at = "delivering", now() + timedelta(minutes=2)
    db.commit()                                                # short claim tx
    return rows

def deliver(client: httpx.Client, db: Session, d: WebhookDelivery) -> None:
    endpoint, event = d.endpoint, d.event                      # loaded with the claim
    body = json.dumps(event.payload).encode()
    try:
        assert_url_safe(endpoint.url)
        resp = client.post(                                    # HTTP outside any DB tx
            endpoint.url, content=body,
            headers={"Content-Type": "application/json",
                     "X-Webhook-Event-Id": str(event.id),
                     "X-Webhook-Event-Type": event.event_type,
                     "X-Webhook-Signature": sign(endpoint.secret, body, int(time.time()))})
        ok, code = 200 <= resp.status_code < 300, resp.status_code
    except (httpx.HTTPError, WebhookUrlError) as exc:
        ok, code, d.last_error = False, None, str(exc)[:500]

    d.attempts += 1
    d.last_status_code = code
    if ok:
        d.status = "succeeded"
        endpoint.consecutive_failures = 0
    elif d.attempts >= settings.webhook_max_attempts:
        d.status = "failed"                                    # dead-letter: kept, listable, redeliverable
        endpoint.consecutive_failures += 1
        if endpoint.consecutive_failures >= 20:
            endpoint.is_active, endpoint.disabled_at = False, now()   # audit-logged
    else:
        delay = min(BACKOFF_CAP, BACKOFF_BASE * 2 ** d.attempts)
        d.status = "pending"
        d.next_attempt_at = now() + timedelta(seconds=delay * random.uniform(0.5, 1.5))
    db.commit()                                                # short result tx

def main() -> None:
    client = httpx.Client(timeout=httpx.Timeout(settings.webhook_timeout_seconds,
                                                connect=3.0),
                          follow_redirects=False, max_redirects=0)
    while not shutdown_requested():                            # SIGTERM sets the flag
        with SessionLocal() as db:
            batch = claim_batch(db)
            for d in batch:
                deliver(client, db, d)
        if not batch:
            time.sleep(1.0)
```

Properties worth naming: at-least-once (documented; consumers dedupe on event id), bounded retries with exponential backoff + full jitter, no transaction across network calls, crashed-worker recovery via lease expiry, bounded concurrency (batch size; add worker replicas to scale), SSRF checked per send (DNS can change after registration), endpoint auto-disable as poison-endpoint dead-lettering. API additions: `GET .../webhook-endpoints/{id}/deliveries` and `POST .../deliveries/{id}/redeliver` (admin role) so customers can self-serve debugging.

### 5.8 Observability baseline (core/logging.py)

- Middleware assigns/propagates `X-Request-ID`; structlog binds `request_id`, `org_id`, `user_id`, route template, status, duration to every log line. The worker binds `delivery_id`, `event_id`, `endpoint_id`.
- Logs are allowlists: never request bodies, tokens, `Authorization` headers, webhook secrets, or full payloads. Redaction test in CI.
- Metrics (when added) label only route template / status class / event_type — never org id, URL, or user id (cardinality).
- `/healthz` (process up) and `/readyz` (DB `SELECT 1`) endpoints; worker exposes a heartbeat row (`worker_heartbeats`) so "webhook backlog age" and "worker alive" are queryable — those two are the first alerts, each with a symptom and first-response note in `docs/runbook.md`.
- OpenTelemetry FastAPI/SQLAlchemy/HTTPX instrumentation wired behind `APP_OTEL_ENABLED` so adding a backend later is config, not code.

### 5.9 Migration strategy

- All schema changes via Alembic; autogenerate is a draft, always hand-reviewed (esp. server defaults, index method, constraint names via a fixed naming convention in `MetaData`).
- Policy from day one, even pre-launch (habit for a 2-person team): expand/contract for live changes; `CREATE INDEX CONCURRENTLY` on hot tables (out of transaction); no destructive DDL in the same release that stops writing the old shape.
- CI proves every migration: fresh Postgres → `alembic upgrade head` → `alembic downgrade -1` → `upgrade head`, plus a check that `alembic heads` reports exactly one head (guards branch merges from a 2-person parallel workflow).

---

## 6. Test and CI baseline

`tests/conftest.py` starts one Postgres testcontainer per session; each test runs in a rolled-back transaction or truncated schema. Seed fixture creates **two orgs and two users** so cross-tenant tests are one line to write.

Minimum suite mapped to the proof matrix:

| Surface | Test |
|---|---|
| Every public endpoint | success, 422 validation, 401 no-token |
| Tenancy | user from org B GETs org A's project/invoice/webhook-endpoint by real id → 404; list endpoints never contain other org's rows |
| Mass assignment | POST/PATCH bodies with `org_id`, `status`, `number`, `amount_total_minor` → ignored-by-schema or 422; forbidden fields asserted absent from responses |
| Invoice idempotency | duplicate `Idempotency-Key` → one row, replayed response; key reuse with new body → 422 |
| Invoice state machine | `paid → open` → 409; concurrent transitions serialize |
| Webhook worker | stub HTTP server: success marks succeeded; 500s → retries with growing `next_attempt_at`, then `failed` at cap; two workers claiming concurrently deliver each row once (SKIP LOCKED test); private-IP URL rejected |
| Signature | consumer-side verification snippet in docs verified by a test against `sign()` |
| Migrations | up/down/up on fresh DB |
| Logging | smoke request: response and log line share request_id; `Authorization` value absent from captured logs |

CI (GitHub Actions, single workflow): `ruff check` + `ruff format --check` → `mypy src` → migration up/down job → `pytest` (testcontainers) → OpenAPI export artifact + `oasdiff breaking` against `main`'s spec so contract breaks block merge instead of surprising customers.

---

## 7. Rollout order for the team of 2

1. Scaffold + CI skeleton + Postgres compose + Alembic baseline (empty). CI green on day one.
2. Core: config, db, errors, logging/request-id, auth (password + tokens), orgs/memberships + tenancy dependency, with the tenancy tests.
3. Projects CRUD (the template domain: DTOs, pagination, role checks).
4. Invoices: schema, numbering, state machine, idempotency.
5. Webhooks: outbox, endpoints CRUD, worker, signing docs page.
6. Ops pass: readiness probes, heartbeat, two alerts, runbook, `oasdiff` gate.

Risks needing product/ops input before build: invoice numbering legal requirements per jurisdiction (gapless vs merely unique), data retention/offboarding policy for org deletion, whether webhook secrets need KMS-grade storage at launch or encrypted-column is acceptable.

## Final proof contract statement

No code was executed: this is a greenfield design task with no repository or runtime in the environment, so no test, migration, or contract check can run yet — that is the explicit untestability reason. The compensating control is that Section 6 defines the exact verifier commands (`pytest`, `alembic upgrade head && alembic downgrade -1`, `ruff check`, `mypy src`, `oasdiff breaking`) that must pass on the first scaffold commit, and every non-trivial design choice above names the test that proves it.

---

## Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md (delivered via Skill invocation)
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
