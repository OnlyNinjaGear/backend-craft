# Auth, tenancy, and security

Read this when a change touches authentication, authorization, roles,
ownership, tenant scope, PII, secrets, request validation, outbound URL fetches,
file uploads, admin endpoints, or logging of security-relevant events.

## Boundary read

Identify:

- authenticated principal source
- authorization decision point
- tenant/account/org scope
- server-owned fields
- sensitive data handled
- security event that should be logged

## Non-negotiables

### Deny by default

Missing policy means no access. Do not rely on "this route is internal" unless
the transport, auth, and deployment boundary prove it.

### Object authorization is separate from authentication

Authentication answers "who is this?" Object authorization answers "may this
principal access this object?" Route-level login checks do not prove object
access.

Safe patterns:

- query by `(id, tenant_id)` for tenant-owned records
- call policy with principal + object before mutation
- enforce server-derived tenant id, never client-provided tenant id

### Auth guards attach at the shared ancestor scope

Framework auth is scoped, not global: Fastify hooks are encapsulated to their
plugin context, FastAPI router dependencies cover only that router, a wrapped
Go sub-mux covers only what it wraps. A new route module added outside the
guarded scope ships unauthenticated and nothing errors. Attach the guard at
the shared ancestor, keep public routes in an explicit allowlisted scope, and
sweep the route table with an unauthenticated 401/403 test.

### Request bodies cannot set server-owned fields

Never mass-assign request bodies into persistence models. Allowlist writeable
fields per command. Assign `role`, `tenant_id`, `owner_id`, `status`, balance,
and audit fields server-side.

### Logs are allowlists

Do not log raw request bodies, auth headers, cookies, tokens, passwords, payment
data, or full webhook payloads by default. Redact by key and prefer stable
identifiers.

### User-controlled URLs are SSRF risk

Any fetch of a user-controlled URL needs scheme/host allowlist, private IP and
link-local blocking after DNS resolution, redirect limits, size caps, and
timeouts.

## Common failure cards

- `authz-handler-only`
- `auth-middleware-scope-miss`
- `tenant-filter-forgotten`
- `pii-logged`
- `ssrf-url-fetch`
- `secret-in-config-or-log`
- `api-bola-id-swap`
- `api-mass-assignment`

## Verifiers

- forbidden-principal tests
- unauthenticated route-table sweep (all non-allowlisted routes 401/403)
- cross-tenant seed tests
- forbidden field update tests
- secret scan
- log redaction tests
- SSRF blocked-host tests

## Escalate to P0

- cross-tenant data read/write
- role/permission escalation
- credential leak
- PII leak into public response or persistent logs
- SSRF to internal network or metadata service
