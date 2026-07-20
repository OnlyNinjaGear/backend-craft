# backend-craft failure cards

Failure cards are the unit of knowledge for this package. They are not generic
best practices. Each card names a situation where an agent commonly writes code
that looks plausible and fails under production conditions.

Status values:

- `draft`: plausible and source-backed, not yet observed in this project
- `observed`: seen once in a real project/task
- `production-tested`: repeated or forward-tested; suitable for hard rule
- `retired`: no longer useful or too noisy

## Card template

```md
## card-id

Status:
Triggered by:
Model failure:
Blast radius:
Detect:
Safe pattern:
Verifier:
Escape hatch:
Sources:
```

---

## api-bola-id-swap

Status: production-tested (forward-test 003, 2026-07-10)
Triggered by: adding `GET /resources/{id}`, `PATCH /resources/{id}`, admin/user scoped endpoints.
Model failure: checks authentication but fetches by raw id without verifying that the caller may access that object.
Blast radius: cross-tenant data exposure or mutation.
Detect: route has path id plus DB lookup by id, but no tenant/user/role predicate or ownership authorization call.
Safe pattern: authorize at object boundary: query by `(id, tenant_id)` or call policy with loaded resource before returning/mutating.
Verifier: test user A cannot read/update/delete user B's resource, including guessed ids.
Escape hatch: public resources with explicit public-read policy.
Sources: OWASP API1:2023 Broken Object Level Authorization, OWASP Authorization Cheat Sheet.

## api-bopla-property-leak

Status: production-tested (forward-test 011, 2026-07-10)
Triggered by: serializing ORM/document objects directly in API responses.
Model failure: returns every field from DB model, including internal or unauthorized properties.
Blast radius: PII leakage, privilege escalation through writable fields, contract drift.
Detect: response uses `model.__dict__`, ORM entity, spread object, `SELECT *`, or schema inferred from persistence model.
Safe pattern: explicit response DTO/schema per endpoint; sensitive fields opt-in only.
Verifier: response contract test asserts forbidden fields are absent.
Escape hatch: internal admin endpoint with explicit role gate and documented response schema.
Sources: OWASP API3:2023 Broken Object Property Level Authorization, OpenAPI 3.1.

## api-mass-assignment

Status: production-tested (forward-test 002, 2026-07-10)
Triggered by: create/update handlers mapping request body directly into model update.
Model failure: `update(data)`, `Object.assign(entity, body)`, Pydantic/DTO accepted fields reused as persistence update.
Blast radius: user sets `role`, `tenant_id`, `is_admin`, balance/status fields.
Detect: request body is passed wholesale to DB/ORM update without allowlist.
Safe pattern: command DTO with explicit allowed fields; server-owned fields assigned server-side only.
Verifier: test forbidden writable fields are ignored or rejected.
Escape hatch: trusted internal migration/admin scripts outside HTTP boundary.
Sources: OWASP API3:2023, ASVS access control requirements.

## api-pagination-late

Status: draft
Triggered by: list endpoint returning a collection.
Model failure: returns unbounded arrays and plans to add pagination later.
Blast radius: compatibility break when pagination is added; memory/latency/resource exhaustion.
Detect: `GET /items` returns list without `limit/page_size/cursor` and no max cap.
Safe pattern: pagination from first release; cursor preferred for mutable large collections.
Verifier: contract includes pagination parameters and response tokens; tests cap max page size.
Escape hatch: tiny static enumerations with explicit bounded cardinality.
Sources: AIP-158 Pagination, OWASP API4:2023 Unrestricted Resource Consumption.

## api-error-contract-drift

Status: draft
Triggered by: adding or changing error handling.
Model failure: returns ad hoc errors per handler (`{"error": "..."} vs {"message": ...}`), leaks stack traces, or changes status semantics.
Blast radius: clients break; sensitive internals leak; monitoring loses signal.
Detect: handlers construct error bodies directly instead of shared error mapper.
Safe pattern: one error schema with code, message, request id, optional details; no stack traces to clients.
Verifier: contract tests for representative 4xx/5xx paths.
Escape hatch: intentionally different upstream compatibility layer, documented in OpenAPI.
Sources: OpenAPI 3.1, OWASP REST Security Cheat Sheet.

## api-idempotency-missing-on-mutation-retry

Status: production-tested (forward-test 004, 2026-07-10)
Triggered by: POST/PATCH/DELETE with payment/order/email/webhook side effects or client retry guidance.
Model failure: adds retry or timeout handling without idempotency key/deduplication.
Blast radius: duplicate charge/order/email/job.
Detect: mutating endpoint performs side effect but has no idempotency key, unique operation id, or dedupe table.
Safe pattern: persist idempotency key with request fingerprint and final response; replay same result for duplicate key. When the mutation also writes local state, state the transaction boundary explicitly and use outbox/state machine — even when the current store has no transactions, say so.
Verifier: duplicate request with same key produces one side effect and same response.
Escape hatch: naturally idempotent PUT to a complete resource state with no external side effects.
Sources: Stripe idempotent requests, Stripe idempotency article, AWS Reliability Pillar.

## authz-handler-only

Status: draft
Triggered by: adding service/repository methods used by multiple routes.
Model failure: authorization checked only in one handler while shared service method remains unsafe for other callers.
Blast radius: future endpoint bypasses policy accidentally.
Detect: service accepts user id/resource id but does not encode policy or require authorized principal/context.
Safe pattern: policy at use-case boundary; repository receives scoped predicates; unsafe lower-level methods named/internal.
Verifier: tests call all public use cases with forbidden principal.
Escape hatch: private pure data access function not reachable from request/job boundary.
Sources: OWASP Authorization Cheat Sheet, ASVS access control.

## auth-cross-layer-prefix-exemption-gap

Status: draft
Triggered by: a global auth middleware/gateway that exempts a URL prefix (e.g. `/api/*`) on the assumption that a framework mounted there (DRF, a sub-app, a router) authenticates every request itself, combined with a plain non-framework handler (a raw Django view, a small utility/health endpoint, a mounted sub-app) registered under that same prefix.
Model failure: treats "this prefix is owned by an authenticating framework" as true for every handler under it. It is only true for handlers that actually go through that framework's per-view auth. A raw view registered on the same URLconf, under the same prefix, is not a framework view — it inherits neither the middleware check (the middleware exempted the whole prefix) nor the framework's per-view auth (it never runs through the framework's dispatch). It ships fully unauthenticated, and nothing errors: the middleware sees an exempted path and steps aside; the raw view has no auth code of its own and just returns data.
Blast radius: any raw/utility/health/sub-app handler added under the exempted prefix is public the moment it ships, including sensitive utility endpoints (internal file listings, debug/dump endpoints, sub-app admin) that nobody thought needed their own auth because "the middleware/API framework handles auth here."
Detect: a middleware/gateway auth check with an early-return/skip branch keyed on a URL prefix, paired with any handler registered on that prefix that is not an instance of the trusted framework's view base class (not an `APIView`/`ViewSet`, not going through the framework's router) — a plain function/handler, a raw included sub-app, a static/utility endpoint.
Safe pattern: never trust a prefix; trust only the specific dispatch mechanism proven to authenticate. Either (a) authenticate at the true shared ancestor — the middleware itself, with no prefix exemption, letting framework views additionally self-authenticate/self-authorize as needed — or (b) if the prefix truly must be exempted, enumerate and audit every handler under it and require each to explicitly opt into an authenticated base class/decorator; never assume "it's under /api/, so DRF/the router covers it."
Verifier: an unauthenticated route-table sweep over the *whole* URLconf (not just the trusted framework's router) — for every route under the exempted prefix, assert 401/403 with no credentials unless the route is on an explicit public allowlist; separately assert the middleware still protects routes outside the exempted prefix, and that a genuine framework view under the exempted prefix stays protected by its own permission check (proving the gap is specific to non-framework handlers, not the whole prefix). Reducer at `tests/cards/auth_cross_layer_prefix_exemption_gap.py` isolates the mechanism: one middleware, one dispatcher, a plain view, a real DRF view, and a plain view outside the prefix.
Escape hatch: a route intentionally public (health check, signed webhook, public docs), named explicitly in the sweep's allowlist — not exempted implicitly by living under a trusted prefix.
Sources: OWASP Authorization Cheat Sheet (deny by default; authorization must be enforced per route/resource, not inferred from URL structure or a sibling layer's configuration); Django docs — Middleware (each middleware runs for every request that reaches it in `MIDDLEWARE` order regardless of which view ultimately handles it, so an early return inside middleware is the only thing that can create this gap), https://docs.djangoproject.com/en/stable/topics/http/middleware/. Distinct from `auth-middleware-scope-miss`, which is about encapsulation among sibling routers within one framework layer (a hook/dependency registered on a sub-scope not covering a sibling scope in the same layer); this card is about a seam *between* two auth layers — a middleware layer that exempts a prefix and a framework layer it trusts to cover that prefix.

## auth-middleware-scope-miss

Status: draft
Triggered by: adding auth via framework middleware/hooks/router dependencies (Fastify `addHook`, FastAPI `APIRouter(dependencies=...)`, Go mux middleware wrapping), then adding a new route module.
Model failure: registers the auth guard on a sub-scope and assumes it is global. New or sibling route modules land outside the guarded scope and ship unauthenticated: Fastify hooks are encapsulated to their plugin context and its children (siblings unaffected); FastAPI router-level dependencies "only affect that APIRouter"; Go stdlib auth wrapping covers only the handlers or sub-mux it explicitly wraps.
Blast radius: whole route modules silently public — every request succeeds, nothing errors, data exposure or mutation until someone notices.
Detect: auth hook/dependency registered inside one registered plugin/router while routes exist in sibling scopes; a new route file whose registration path does not pass through the guarded scope; a route registered directly on the root mux/app next to an auth-wrapped sub-router.
Safe pattern: attach the auth guard at the shared ancestor context (root or an explicit "authenticated" scope) and put public routes in a separate scope; in Fastify use preParsing/preValidation at the ancestor (the docs' recommended auth hooks) and export hooks upward only via `fastify-plugin`, explicitly; in FastAPI attach dependencies at `include_router` (or app level) for every protected router.
Verifier: route-table sweep test — enumerate all registered routes (Fastify `printRoutes()`, FastAPI `app.routes`, the Go mux table) and assert every route not in the public allowlist returns 401/403 without credentials.
Escape hatch: intentionally public routes (health, signed webhooks, docs) named in a public-route allowlist that the sweep test reads.
Sources: Fastify Hooks + Encapsulation references (hooks encapsulated per plugin context; sibling isolation; fastify-plugin breaks encapsulation explicitly), FastAPI Bigger Applications tutorial (router-level dependencies scoped to that router only), OWASP Authorization Cheat Sheet (deny by default). Verified against fastify.dev and fastapi.tiangolo.com, 2026-07-10.

## drf-default-permission-unset

Status: draft
Triggered by: a Django REST Framework project that sets `DEFAULT_AUTHENTICATION_CLASSES` in `REST_FRAMEWORK` (so requests do get a resolved `request.user`) but never sets `DEFAULT_PERMISSION_CLASSES`, plus any view/viewset that forgets its own `permission_classes`.
Model failure: treats "authentication is configured" as "authorization is configured." DRF's actual built-in default for `DEFAULT_PERMISSION_CLASSES` is `AllowAny`, not deny-by-default. A view that forgets `permission_classes` is not merely unauthenticated-and-500 — it is silently public to anyone, authenticated or not, and nothing errors.
Blast radius: any view added or copy-pasted without an explicit `permission_classes` line is world-readable/writable the moment it ships; the gap is invisible in code review because the view looks identical to a properly-guarded one minus one line.
Detect: `REST_FRAMEWORK` config defines `DEFAULT_AUTHENTICATION_CLASSES` without also defining `DEFAULT_PERMISSION_CLASSES`; any `APIView`/`ViewSet` subclass with no `permission_classes` attribute and no `get_permissions` override.
Safe pattern: set `DEFAULT_PERMISSION_CLASSES` to a non-`AllowAny` value (typically `IsAuthenticated`) project-wide, so a forgotten per-view line fails closed instead of open; treat any explicit `AllowAny` view as an exception that must be named and reviewed.
Verifier: instantiate the DRF settings actually used by the project; assert `DEFAULT_PERMISSION_CLASSES` is set and does not resolve to `AllowAny`. Fixture-level: a view with no `permission_classes` hit via `APIRequestFactory`/test client with zero credentials must return 401/403, not 200.
Escape hatch: a route intentionally public (health check, signed webhook receiver, public docs) with `permission_classes = [AllowAny]` stated explicitly on the view, not inherited from an unset default.
Sources: DRF permissions docs, https://www.django-rest-framework.org/api-guide/permissions/ (documents `DEFAULT_PERMISSION_CLASSES` as a global `REST_FRAMEWORK` setting and `AllowAny` as its shipped default when unset — confirmed directly against the installed `djangorestframework` 3.17.1 source in this repo's environment, see reducer); OWASP Authorization Cheat Sheet (deny by default).

## drf-authn-expansion-widens-authz

Status: draft
Triggered by: a Django REST Framework project where authorization on many endpoints is just "is the caller authenticated" (`permission_classes = [IsAuthenticated]`), then a new authentication class is added to `DEFAULT_AUTHENTICATION_CLASSES` project-wide (commonly an API-key class for a machine/service integrator).
Model failure: treats `IsAuthenticated` as scoped authorization when it is only a coarse "some principal resolved" check. The check was written when the only principal that could authenticate was a staff user; adding a second authentication class does not touch any view's `permission_classes`, but it changes who can satisfy that check. Every endpoint guarded only by `IsAuthenticated` — including admin/reference CRUD never meant for the new principal — silently accepts it too.
Blast radius: whole classes of endpoints (anything relying on bare `IsAuthenticated`) become reachable by a principal added for one narrow purpose, without a single line of those endpoints changing; nothing errors, and code review of the new authenticator does not surface the affected views because they live elsewhere.
Detect: a `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]` change (an addition) alongside views/viewsets whose only authorization is `permission_classes = [IsAuthenticated]` (or an equivalent coarse "authenticated" check) with no principal/scope/role distinction.
Safe pattern: authorization must be principal-aware, not just authentication-aware — key on role/scope/claim (`IsAdminUser`, a custom permission checking `request.auth`'s scope, or a DRF `Permission` per principal class) so a new authentication method does not implicitly re-scope every endpoint that used to trust "authenticated == staff."
Verifier: principal-matrix test, run whenever a new authentication class is added — construct a request authenticated only via the new class, hit every route guarded by bare `IsAuthenticated`, and assert 403 on everything outside that principal's explicit allowlist. Reducer at `tests/cards/drf_authn_expansion_widens_authz.py` isolates the mechanism: same view, same `permission_classes`, only the authenticator list changes, and a request that got 403 before now gets 200.
Escape hatch: an endpoint intentionally meant for every authenticated principal class (e.g. a shared `/whoami/` health-style endpoint) — state that explicitly in review, not by omission.
Sources: DRF permissions docs, https://www.django-rest-framework.org/api-guide/permissions/ (permission classes run against whatever `request.user`/`request.auth` the configured authenticators resolve, independent of which authenticator resolved them); OWASP Authorization Cheat Sheet (authorization must be enforced per resource/principal, not inferred from authentication alone).

## drf-authenticator-raises-instead-of-none

Status: draft
Triggered by: writing a custom Django REST Framework `BaseAuthentication.authenticate()` for a secondary scheme (commonly an API key for a machine/service integrator) that is registered alongside session/JWT authentication in `DEFAULT_AUTHENTICATION_CLASSES`.
Model failure: two bugs bundled in one authenticator. (1) It raises `AuthenticationFailed` when it cannot find its own credentials, instead of returning `None`. DRF's authenticator chain (`Request._authenticate()`) stops on the first raised `APIException` and does not try the remaining authenticators — a legitimate session/JWT request that simply has no API key never reaches session auth and gets 401. (2) It infers credentials by scanning `request.headers` against a deny-list of "known" header names and treating the first unrecognized header as username:secret, instead of reading one explicit header for its own scheme. Any unrelated header the client happens to send (a new proxy/tracing header) is parsed as a bogus credential, rejected, and again short-circuits the fallback — plus the auth surface is now every header name and order-dependent.
Blast radius: legitimate session/JWT-authenticated users get spurious 401s the moment they send any header the authenticator does not recognize, or simply omit the API key; the failure is intermittent and looks like a session/JWT bug even though session/JWT auth is never reached. A secret compared with `==` instead of a constant-time function additionally leaks timing information.
Detect: custom `authenticate()` raises `AuthenticationFailed` for "my credentials are absent" rather than returning `None`; iterates `request.headers`/`request.META` against a deny-list instead of reading one named header; compares a secret with `==`/`!=` instead of `hmac.compare_digest`.
Safe pattern: return `None` when this authenticator's own explicit header (e.g. `X-Api-Key`) is absent, so DRF continues to the next authenticator; only this scheme's named header is ever read as credentials; raise only once that header is present and invalid; compare secrets with `hmac.compare_digest`.
Verifier: same protected view, same `permission_classes`, three request shapes against each authenticator variant — (a) valid session cookie, no API key, (b) valid session cookie plus one unrelated header, (c) a valid API key alone. The buggy authenticator 401s (a) and (b) despite a valid session and still accepts (c); the fixed authenticator returns 200 for all three. Reducer at `tests/cards/drf_authenticator_raises_instead_of_none.py`, run standalone or via `python -m pytest tests/cards/test_drf_authenticator_raises_instead_of_none.py -q`.
Escape hatch: an authenticator that is the *only* configured authentication class (no fallback scheme exists to break) may raise on missing credentials — state that explicitly, since adding a second authentication class later reintroduces this failure mode.
Sources: DRF authentication docs, https://www.django-rest-framework.org/api-guide/authentication/ (custom authentication: "If authentication is successful, `.authenticate()` should return a two-tuple... If authentication is not attempted, `.authenticate()` should return `None`... Any authentication errors should raise an `AuthenticationFailed` exception" — returning `None` vs raising are documented as distinct outcomes with distinct chain behavior); confirmed against `Request._authenticate()` in installed `djangorestframework` 3.17.1 source (raised `exceptions.APIException` stops the authenticator loop, does not continue to the next authenticator); Python `hmac` docs on `compare_digest` for timing-safe comparison.

## drf-permission-flag-nulled-for-post-read

Status: draft
Triggered by: a Django REST Framework mixin that decides required authorization by HTTP method — safe methods get a light or no check, everything else requires a permission flag (`permission_flag`) evaluated by a shared permission class — combined with an action that is semantically a read but is exposed over `POST` (search-by-key, bulk-get, "preview", and similar).
Model failure: instead of mapping the misclassified action to the permission it actually needs, the mixin sets `self.permission_flag = None` for that action list, calls `super().check_permissions()` under no flag, then restores the flag afterward. The permission class treats a falsy flag as "nothing to check," so setting it to `None` does not scope the check down to something lighter — it removes the check. Any authenticated principal, including one holding none of the view's permissions, can now call the action. Authorization was disabled, not corrected.
Blast radius: every endpoint added to the "misclassified read" list is reachable by every authenticated principal regardless of role; the diff reads as an intentional, narrow read-classification fix (a comment like "these are reads"), so it passes review without anyone noticing the guard is gone.
Detect: a `check_permissions`/`get_permissions` override that branches on `self.action` and sets a guard attribute (`permission_flag` or similar) to `None`/falsy inside the branch, then restores it, instead of resolving the action to its own required permission via an explicit map.
Safe pattern: an explicit `action -> required_permission` map consulted for every action, including a genuinely lighter "read" permission for the misclassified actions; never null a shared guard attribute as a way to skip a check.
Verifier: a principal holding none of the view's permissions must get 403 on `POST .../by-key/` and `POST .../bulk-get/`, same as on the write actions; a principal holding only the mapped read permission gets 200 on the read actions and 403 on write actions. Reducer at `tests/cards/drf_permission_flag_nulled_for_post_read.py` isolates the mechanism: same permission class, same principals, only the `check_permissions` override differs between the nulling-flag variant and the explicit-map variant.
Escape hatch: an action that is genuinely public, stated explicitly as `permission_classes = [AllowAny]` on that action — not achieved by nulling a guard attribute shared with privileged actions.
Sources: DRF permissions docs, https://www.django-rest-framework.org/api-guide/permissions/ (permission classes are evaluated per request against whatever attributes the view exposes at call time; the framework does not protect an application from an attribute it chooses to clear); OWASP Authorization Cheat Sheet (authorization must be enforced per action/resource, not inferred from HTTP method, and never disabled as a shortcut around misclassification).

## drf-default-throttle-unset

Status: draft
Triggered by: a Django REST Framework project that configures `DEFAULT_AUTHENTICATION_CLASSES`/`DEFAULT_PERMISSION_CLASSES` but never sets `DEFAULT_THROTTLE_CLASSES`, or that sets only a generic project-wide anonymous/user rate, including on the credential-issuing endpoint (`TokenObtainPairView`, a custom login view, or any endpoint whose per-request cost is high).
Model failure: treats "authentication and authorization are configured" as "the endpoint is safe." DRF's own built-in default for `DEFAULT_THROTTLE_CLASSES` is `[]` -- no throttling runs at all unless a view opts in, so a forgotten throttle is not a slower endpoint, it is an unmetered one. Even a project that does add a project-wide `AnonRateThrottle`/`UserRateThrottle` shares one scope and one budget across every anonymous route; the login endpoint inherits the same generic "browse a few pages" rate as any other read, instead of its own scope. That single shared bucket cuts both ways: unrelated anonymous traffic can burn down the budget that was supposed to cap login attempts (a legitimate user gets locked out of login by other traffic), and login-guessing traffic can burn down the budget legitimate anonymous reads need, with neither getting a rate tuned to what it actually is.
Blast radius: unrestricted credential brute force against the token/login endpoint; on any endpoint whose handler does per-request DB/auth work (a custom authenticator with a DB user lookup, for example), unrestricted requests also amplify into DB load -- OWASP API4:2023 Unrestricted Resource Consumption.
Detect: `REST_FRAMEWORK` has no `DEFAULT_THROTTLE_CLASSES`/`DEFAULT_THROTTLE_RATES` at all; or it has them, but the login/token view (and any other high-cost view) has no `throttle_classes`/`throttle_scope` of its own distinct from the generic anon/user scope shared with unrelated routes.
Safe pattern: give the credential-issuing endpoint (and any other high-cost endpoint) its own `ScopedRateThrottle` scope (e.g. `"login"`) with a rate sized to what that endpoint actually is, separate from -- and in addition to -- any project-wide default throttle scope used for ordinary reads; verify the 429 response actually appears under repeated hits and that unrelated traffic on other scopes does not move the login scope's counter.
Verifier: from a single caller identity, N+1 rapid requests to the token/login endpoint must return 429 starting at request N+1, with N sized to the endpoint's own configured rate, not the project-wide default. Separately, prove independence: exhausting a sibling endpoint's throttle scope must not affect the login endpoint's remaining budget, and vice versa. Reducer at `tests/cards/drf_default_throttle_unset.py` isolates three variants: no throttling at all, a shared generic anon scope, and a dedicated scope.
Escape hatch: an endpoint that issues no credential and does no expensive per-request work (a static public docs page) does not need a dedicated throttle scope -- state that explicitly in review rather than by omission, and keep it on the project's shared default scope.
Sources: DRF throttling docs, https://www.django-rest-framework.org/api-guide/throttling/ (documents `DEFAULT_THROTTLE_CLASSES` defaulting to `[]`; `ScopedRateThrottle` computing its cache key from the view's own `throttle_scope`, independent of any other scope) -- confirmed against the installed `djangorestframework` 3.17.1 source in this repo's environment, see reducer; OWASP API4:2023 Unrestricted Resource Consumption; OWASP Authentication Cheat Sheet (rate-limit authentication attempts).

## tenant-filter-forgotten

Status: production-tested (forward-test 003, 2026-07-10)
Triggered by: multi-tenant project, list/search/report/export endpoints.
Model failure: one query lacks `tenant_id` predicate or uses tenant from request body instead of authenticated context.
Blast radius: cross-tenant reads/writes, regulatory incident.
Detect: DB query on tenant-owned table without tenant predicate; tenant id accepted from client.
Safe pattern: tenant scope comes from auth/session; repository helpers require tenant scope.
Verifier: seeded two-tenant integration test proves no leakage on list, get, update, export.
Escape hatch: platform-level global admin endpoint with explicit role and audit log.
Sources: OWASP API1:2023, OWASP Authorization Cheat Sheet.

## pii-logged

Status: draft
Triggered by: adding request/response logging, exception logging, webhook debugging.
Model failure: logs full body, tokens, passwords, emails, payment details, auth headers.
Blast radius: privacy incident; secrets copied into log storage and support tooling.
Detect: logger receives raw request body, headers, exception context with secret-bearing fields.
Safe pattern: structured allowlist logs; redact sensitive keys; include correlation id, not payload dump.
Verifier: test logger/redactor removes known sensitive fields.
Escape hatch: temporary local-only debugging with no committed code and no shared log sink.
Sources: OWASP Logging Cheat Sheet, OWASP API Security.

## ssrf-url-fetch

Status: draft
Triggered by: webhook fetcher, image importer, URL preview, callback validation.
Model failure: fetches user-controlled URL without scheme/host/IP restrictions and redirect policy.
Blast radius: internal metadata/service access, data exfiltration.
Detect: HTTP client consumes URL from request/db/user config.
Safe pattern: allowlist schemes and hosts, block private/link-local ranges after DNS resolution, limit redirects, timeout and size cap.
Verifier: tests reject localhost, private IPs, link-local metadata IPs, DNS rebinding fixture if possible.
Escape hatch: internal admin-only tool running in isolated network with explicit allowlist.
Sources: OWASP API7:2023 SSRF, OWASP SSRF Prevention Cheat Sheet.

## secret-in-config-or-log

Status: draft
Triggered by: adding config examples, logs, errors, seed data.
Model failure: commits real-looking secrets or logs environment variable values.
Blast radius: credential leakage and false confidence in secret hygiene.
Detect: API keys/tokens/passwords in source, fixtures, `.env`, logs, docs.
Safe pattern: placeholders only; load secrets from env/secret manager; never log secret values.
Verifier: secret scan plus review of config output.
Escape hatch: deterministic fake test keys clearly marked and rejected by production providers.
Sources: OWASP ASVS, Node security best practices.

## sql-string-concat

Status: production-tested (forward-test 002, 2026-07-10)
Triggered by: building filters/search/order clauses.
Model failure: concatenates request values into SQL string or f-string/template literal.
Blast radius: SQL injection or broken query semantics.
Detect: SQL string contains interpolated user/request values.
Safe pattern: parameterized values; allowlisted identifiers for dynamic sort/filter fields.
Verifier: injection payload test and linter/Semgrep rule.
Escape hatch: static SQL fragments selected from constant allowlist.
Sources: CWE-89, OWASP ASVS, PostgreSQL docs.

## db-transaction-around-network-call

Status: production-tested (forward-test 104, 2026-07-10)
Triggered by: endpoint creates DB row and calls payment/email/external API.
Model failure: opens DB transaction, then performs network call inside it.
Blast radius: long-held locks, deadlocks, duplicate side effects on retry, poor throughput.
Detect: transaction scope includes HTTP/email/payment/queue publish call.
Safe pattern: keep DB transaction short; use outbox/inbox or state machine for external side effects.
Verifier: integration test proves transaction commits quickly and outbox worker handles external call idempotently.
Escape hatch: rare local RPC guaranteed bounded and necessary for serializable invariant; document timeout and lock impact.
Sources: PostgreSQL explicit locking, AWS Reliability Pillar.

## migration-non-online-ddl

Status: production-tested (forward-test 005, 2026-07-10)
Triggered by: altering large/hot table.
Model failure: writes direct blocking DDL or backfills all rows in one transaction.
Blast radius: table lock, outage, replication lag.
Detect: migration contains `ALTER TABLE` on hot table, full-table update, index creation without online/concurrent strategy.
Safe pattern: expand/contract migration, concurrent index where supported, batched backfill, app compatibility window.
Verifier: migration dry run on production-like data or explicit lock analysis.
Escape hatch: tiny table with measured row count and maintenance window.
Sources: PostgreSQL ALTER TABLE, PostgreSQL explicit locking.

## migration-no-rollback-plan

Status: draft
Triggered by: schema/data migration in production path.
Model failure: only writes `up`; no rollback, no forward-fix note, no backup/restore assumptions.
Blast radius: failed deploy leaves app and DB incompatible.
Detect: migration lacks `down` or irreversible annotation.
Safe pattern: reversible migration, or explicit irreversible-with-forward-fix note and deployment sequence.
Verifier: run up/down on throwaway DB or document irreversible proof.
Escape hatch: destructive legal/data-retention migration with signoff.
Sources: deployment safety practice, PostgreSQL DDL docs.

## orm-n-plus-one

Status: draft
Triggered by: list endpoint returns nested data.
Model failure: loops over rows and performs per-row query or lazy relation access.
Blast radius: latency and DB load grow with result count.
Detect: query in loop; lazy relation access in serialization; Mongo `.find()` inside loop.
Safe pattern: join/prefetch/batch lookup; cap page size; validate query count.
Verifier: test query count for list endpoint and representative page size.
Escape hatch: bounded list of very small fixed size, documented.
Sources: PostgreSQL performance tips, MongoDB indexing strategies.

## select-star-public-response

Status: draft
Triggered by: endpoint query or repository powering public response.
Model failure: `SELECT *` or full document fetch is returned/mapped wholesale.
Blast radius: field leak and accidental contract expansion.
Detect: `SELECT *`, ORM entity returned directly, Mongo projection missing on public path.
Safe pattern: explicit column/projection list matched to response schema.
Verifier: contract test forbids internal fields.
Escape hatch: internal migration/admin script.
Sources: OWASP API3:2023, OpenAPI 3.1.

## db-timeout-missing

Status: draft
Triggered by: DB query in request path or worker.
Model failure: uses default unlimited statement/query timeout.
Blast radius: hung requests, worker starvation, pool exhaustion.
Detect: DB client/query has no context/deadline/statement timeout.
Safe pattern: request deadline propagated to DB; statement/lock timeout configured per role/session/path.
Verifier: slow query test aborts within configured budget.
Escape hatch: offline maintenance job with explicit long timeout and isolation.
Sources: PostgreSQL runtime client config, Go database cancel operations.

## mongo-index-without-query-shape

Status: draft
Triggered by: adding Mongo query or index.
Model failure: creates index on a field "just in case" or wrong compound order.
Blast radius: write amplification, unused indexes, slow sort/range queries.
Detect: index does not match equality/sort/range query shape.
Safe pattern: derive compound index from query pattern using ESR guideline.
Verifier: `explain()` confirms index use for target query.
Escape hatch: low-volume collection with explicit growth cap.
Sources: MongoDB indexing strategies, MongoDB ESR guideline.

## mongo-weak-critical-write-concern

Status: draft
Triggered by: critical writes: payments, account state, order state, audit.
Model failure: relies on default write concern without deciding durability semantics.
Blast radius: acknowledged state may be weaker than product invariant expects.
Detect: critical write path has no documented write concern/read concern policy.
Safe pattern: choose write concern/read concern based on consistency requirement; document tradeoff.
Verifier: integration/config test asserts client/session settings.
Escape hatch: cache/analytics/non-critical ephemeral data.
Sources: MongoDB write concern, MongoDB transactions.

## retry-without-jitter-or-cap

Status: production-tested (forward-test 007, 2026-07-10)
Triggered by: transient failure handling for HTTP/DB/queue calls.
Model failure: unbounded retry, fixed sleep, no jitter, no max elapsed time, retries non-idempotent operation.
Blast radius: retry storm, duplicate side effects, overload amplification.
Detect: retry loop lacks cap/jitter/idempotency check or ignores `Retry-After`.
Safe pattern: bounded exponential backoff with jitter; retry only idempotent or idempotency-protected operations.
Verifier: test retry count/timing and non-retry on non-idempotent path.
Escape hatch: single local in-memory retry with no external side effect.
Sources: AWS Reliability Pillar, Azure Retry pattern, Azure Retry Storm antipattern.

## circuit-breaker-missing-on-fragile-dependency

Status: draft
Triggered by: hot path calls unreliable/slow downstream.
Model failure: every request calls downstream until downstream failure consumes threads/pool/timeouts.
Blast radius: cascading failure.
Detect: high-volume call has timeout and retry but no fail-fast/degraded behavior.
Safe pattern: timeout + circuit breaker or budgeted fallback/degraded response.
Verifier: downstream-failure test proves bounded latency and no retry storm.
Escape hatch: low-volume admin path with manual operator use.
Sources: Azure Circuit Breaker pattern, Google SRE Cascading Failures.

## queue-consumer-not-idempotent

Status: production-tested (forward-test 006, 2026-07-10)
Triggered by: background worker, webhook handler, message queue consumer.
Model failure: assumes exactly-once delivery and writes side effects directly.
Blast radius: duplicate side effects, inconsistent state after redelivery.
Detect: consumer lacks dedupe key, idempotent state transition, or processed-message table.
Safe pattern: at-least-once assumption; idempotency key/dedupe; transactional inbox/outbox where needed.
Verifier: process same message twice; assert single side effect and stable state.
Escape hatch: read-only analytics consumer where duplicates are intentionally aggregated downstream.
Sources: AWS Reliability Pillar, Stripe idempotency.

## worker-unbounded-concurrency

Status: draft
Triggered by: batch job, queue worker, goroutines/tasks/promises over collection.
Model failure: spawns one concurrent task per item without limit or backpressure.
Blast radius: DB/API pool exhaustion, memory blowup, rate-limit bans.
Detect: `Promise.all(items.map(...))`, unbounded goroutines, `asyncio.gather` over unbounded input.
Safe pattern: bounded worker pool; respect downstream capacity; propagate cancellation.
Verifier: test max concurrency; load test or fake downstream asserts cap.
Escape hatch: collection size proven tiny and bounded.
Sources: Google SRE Handling Overload, Node event loop guidance, Go context docs, Python asyncio docs.

## timeout-without-cancellation-propagation

Status: draft
Triggered by: request deadline, cancellation, user disconnect, job shutdown.
Model failure: sets timeout at outer layer but inner DB/HTTP/tasks continue running.
Blast radius: wasted work, resource leak, inconsistent side effects.
Detect: timeout wrapper around call without context/signal passed into dependency.
Safe pattern: propagate context/AbortSignal/cancellation token to every blocking operation.
Verifier: cancellation test observes downstream operation stops.
Escape hatch: non-cancellable legacy dependency isolated in worker with hard process/job timeout.
Sources: Go context docs, Python asyncio docs, Node AbortController docs.

## event-loop-blocking

Status: production-tested (forward-test 108, 2026-07-10)
Triggered by: Node request path with crypto, compression, JSON, file IO, loops, sync DB/client calls.
Model failure: uses sync or CPU-heavy work inside request handler.
Blast radius: all clients stall because event loop is blocked.
Detect: `fs.*Sync`, large JSON operations, CPU loop, sync crypto in handler.
Safe pattern: async APIs, worker thread/process, streaming, input size cap.
Verifier: concrete proof of bounded work — row-cap test, streamed-response assertion, or event-loop delay benchmark. A comment claiming the dataset is small does not count.
Escape hatch: CLI script or one-shot startup work.
Sources: Node "Don't Block the Event Loop", Express performance practices.

## go-http-server-no-timeouts

Status: draft
Triggered by: creating or reviewing a Go HTTP server entrypoint.
Model failure: serves with `http.ListenAndServe(addr, handler)` or a bare `&http.Server{Addr, Handler}` — all server timeouts are zero.
Blast radius: per Go docs, zero means no timeout at all: slow/stalled clients (slowloris) hold connections and goroutines indefinitely; file descriptor and memory exhaustion; outage under trivial attack or bad client.
Detect: package-level `http.ListenAndServe(...)` call; `http.Server` literal with neither `ReadTimeout` nor `ReadHeaderTimeout` set.
Safe pattern: construct `http.Server` with `ReadHeaderTimeout` (preferred per docs — lets handlers own body deadlines), plus `ReadTimeout`/`WriteTimeout`/`IdleTimeout` chosen for the workload; pair with `Server.Shutdown` for graceful stop.
Verifier: startup code review or test asserting server config fields are non-zero; slow-client test where feasible.
Escape hatch: localhost-only dev/test servers, pprof/debug listeners on private interfaces, and tests using `httptest.Server`.
Sources: pkg.go.dev/net/http `Server` field docs (zero or negative value means no timeout; `ReadHeaderTimeout` falls back to `ReadTimeout`), verified 2026-07-10 against installed Go 1.26 `go doc net/http.Server`.

## go-goroutine-without-lifecycle

Status: production-tested (forward-test 009, 2026-07-10)
Triggered by: `go func()` in request/job/server path.
Model failure: launches goroutine without context, errgroup, wait, panic recovery, or bounded lifetime.
Blast radius: leaked work, ignored errors, process crash, data race.
Detect: `go` statement not tied to `errgroup`, context, worker pool, or lifecycle manager.
Safe pattern: `errgroup.WithContext`, bounded worker pool, explicit error propagation; goroutines that may panic need their own `defer`/`recover` converting panic to error — errgroup does NOT propagate panics to `Wait` (rejected by design in x/sync source, verified v0.22.0).
Verifier: cancellation test; goroutine count does not grow after request/job cancellation.
Escape hatch: process-lifetime background goroutine registered in server lifecycle.
Sources: Effective Go, Go context docs, golangci-lint linters, x/sync errgroup source.

## go-ignored-error

Status: draft
Triggered by: any Go call returning `error`.
Model failure: `_ =`, missing check, or log-and-continue where invariant requires stop.
Blast radius: silent data loss and corrupted state.
Detect: unchecked error or ignored close/commit/rollback errors.
Safe pattern: handle, wrap with context, or explicitly document safe ignore.
Verifier: `errcheck` clean or suppressions have reason.
Escape hatch: documented best-effort cleanup where ignoring is harmless.
Sources: Go Code Review Comments, golangci-lint `errcheck`.

## python-swallowed-exception

Status: draft
Triggered by: broad exception handling.
Model failure: `except Exception: pass`, logs without traceback, or returns default success.
Blast radius: silent data loss and false success.
Detect: broad except with no re-raise, no typed recovery, no `logging.exception`.
Safe pattern: catch specific exceptions; recover explicitly; log with traceback and fail closed when invariant unknown.
Verifier: test error path returns failure and logs exception.
Escape hatch: best-effort cleanup with comment and metric.
Sources: Python exceptions docs, Python logging docs, Ruff rules.

## python-async-cancel-swallowed

Status: production-tested (forward-test 010, 2026-07-10)
Triggered by: `asyncio` worker, request handler, background task.
Model failure: catches `BaseException`/broad exception and swallows cancellation, or creates task without awaiting/cancelling.
Blast radius: shutdown hangs, leaked task, partial side effect.
Detect: `create_task` with no lifecycle; broad except in async function; missing `finally` cleanup.
Safe pattern: `TaskGroup` or owned task registry; re-raise cancellation; use `asyncio.timeout`.
Verifier: cancellation test terminates promptly and cleanup runs.
Escape hatch: fire-and-forget telemetry with bounded queue and shutdown drain.
Sources: Python asyncio tasks docs.

## ts-floating-promise

Status: draft
Triggered by: async function call in request/worker path.
Model failure: starts promise without await/return/catch/void marker.
Blast radius: unhandled rejection, lost sequencing, side effect after response.
Detect: `no-floating-promises` lint hit or promise-valued statement.
Safe pattern: await, return, catch with explicit error handling, or `void` only for intentional detached work with lifecycle.
Verifier: `@typescript-eslint/no-floating-promises` enabled and clean.
Escape hatch: intentional background fire-and-forget registered in job supervisor.
Sources: typescript-eslint no-floating-promises, Node security docs.

## ts-any-at-boundary

Status: draft
Triggered by: request parsing, external API response, DB document, message payload.
Model failure: uses `any` and trusts shape without runtime validation.
Blast radius: runtime crash, bad writes, security bypass through malformed input.
Detect: `any`, `as unknown as`, unchecked JSON parse on boundary.
Safe pattern: runtime validation schema at boundary; `unknown` before validation; typed domain object after validation.
Verifier: malformed payload tests fail safely.
Escape hatch: generated trusted client with contract tests.
Sources: TypeScript Handbook, typescript-eslint no-explicit-any, JSON Schema 2020-12.

## observability-no-correlation-id

Status: draft
Triggered by: new service, endpoint, worker, outbound call.
Model failure: logs events without request/job/correlation id.
Blast radius: production incident cannot be traced across services.
Detect: log statements lack trace/request/job id or context propagation.
Safe pattern: correlation id generated/accepted at boundary and propagated through logs/traces/outbound calls.
Verifier: integration test or smoke request shows id in response header/log/trace.
Escape hatch: one-shot local script.
Sources: OpenTelemetry docs, Google SRE monitoring.

## metrics-high-cardinality

Status: draft
Triggered by: adding metrics labels.
Model failure: uses user id, email, raw path, request id, UUID, or error message as label.
Blast radius: monitoring cardinality explosion and cost/perf incident.
Detect: metric labels include unbounded values.
Safe pattern: bounded labels: route template, status class, dependency name, operation, error code.
Verifier: code review plus metric cardinality check in tests where possible.
Escape hatch: tracing attributes or logs where high-cardinality values are appropriate and sampled/retained safely.
Sources: OpenTelemetry docs, Google SRE monitoring.

## test-only-happy-path

Status: draft
Triggered by: any backend feature touching contracts, auth, DB, side effects, queues.
Model failure: adds only success test or no tests.
Blast radius: regressions in error path, authorization, rollback, retry, compatibility.
Detect: changed surface has no tests for failure/permission/boundary/idempotency path.
Safe pattern: proof matrix based on changed blast radius.
Verifier: cite exact test names for success, error, permission, boundary, recovery.
Escape hatch: pure refactor with unchanged behavior and existing covering tests.
Sources: pytest docs, Pact docs, Testcontainers docs.

## dependency-cargo-cult

Status: production-tested (forward-test 013, 2026-07-10)
Triggered by: stack choice, dependency recommendation, replacing custom code with a library.
Model failure: recommends a popular library without mapping it to project fit, failure removed, integration boundary, verifier, or escape hatch.
Blast radius: new abstraction hides transaction/auth/retry/migration semantics; project gains maintenance load without reducing production risk.
Detect: dependency added or recommended with no lockfile/version check, no official docs check, no test/check command, and no stated failure mode.
Safe pattern: run the dependency gate: current project fit, failure removed, integration boundary, verifier, escape hatch, removal path.
Verifier: recommendation cites official docs or installed version and adds the first proof command/test before relying on the library.
Escape hatch: exploratory prototype explicitly marked disposable.
Sources: official docs for the chosen library, project lockfile, `library-decisions.md`.

## framework-rewrite-as-cleanup

Status: production-tested (forward-test 014, 2026-07-10)
Triggered by: messy existing backend, retrofit/hardening request, framework comparison.
Model failure: recommends migrating Express to Fastify/NestJS, Flask/FastAPI to Django, or similar rewrites before mapping current P0/P1 risks.
Blast radius: rewrite delays fixes for auth, tenancy, migrations, tests, timeouts, and observability; may ship new regressions with old risks preserved.
Detect: answer starts with new framework choice before inventory of current framework, DB, migrations, tests, CI, queues, and public contracts.
Safe pattern: inventory first, harden current boundaries, introduce new library/framework only at one boundary with verifier; full migration needs explicit product/ops reason.
Verifier: staged plan lists current-stack checks and proves at least one risk reduction before any migration work.
Escape hatch: current framework is unsupported, blocks required security fixes, or the user explicitly asks for a migration project.
Sources: `stack-recipes.md`, `codebase-fit.md`, official docs for old and new frameworks.

## python-gather-partial-failure-leak

Status: draft
Triggered by: running several side-effecting async operations concurrently (`asyncio.gather`, fan-out over a collection) where one may fail.
Model failure: treats `asyncio.gather(*coros)` as if it were an all-or-nothing transaction. Two wrong assumptions get bundled together: (a) that when one awaitable raises, `gather` cancels the siblings, and (b) that a failed batch leaves no partial side effects. Both are false, and they are different problems that need different fixes.
Blast radius: after the first error, sibling coroutines keep running and commit half of a logical operation — a charge without its record, a row written without its outbox event, an email sent for an order that never persisted.
Detect: `asyncio.gather(...)` (without `return_exceptions=True`) over coroutines that each perform a write/external call, and the code path assumes "if it raised, nothing happened".
Safe pattern: separate the four concerns instead of hoping one call covers them.
  1. Ownership / cancellation: prefer `asyncio.TaskGroup` — structured concurrency cancels the remaining tasks on the first error and does not leak background work. If you must stay on `gather`, do it manually: create tasks, and on the first exception cancel the unfinished ones, then `await asyncio.gather(*tasks, return_exceptions=True)` to drain them, then re-raise.
  2. Atomicity: neither `gather` nor `TaskGroup` gives it. Cancellation is not rollback — a side effect committed before the cancel point stays committed.
  3. Side-effect safety: make each side effect idempotent, or add compensation/saga, a state machine, an outbox, or a single DB transaction boundary — or run the side effects sequentially after all inputs are validated, so a mid-batch failure cannot half-commit.
  4. Read-only fan-out has none of this risk; only error aggregation and ordering matter there.
Verifier: `tests/cards/gather_partial_failure.py` + `tests/cards/test_gather_partial_failure.py` prove BOTH facts without a timing race: `gather` lets a sibling commit its side effect AFTER the error already propagated (not cancelled), and `TaskGroup` cancels the sibling but the side effect it committed before cancellation is NOT rolled back. Run: `python3 tests/cards/gather_partial_failure.py` and `cd tests/cards && python3 -m pytest test_gather_partial_failure.py -q`.
Escape hatch: fan-out with no side effects (pure reads/computation), where a partial failure cannot leave inconsistent state.
Sources: Python asyncio docs — `asyncio.gather` and `asyncio.TaskGroup` (https://docs.python.org/3/library/asyncio-task.html).

## pg-non-atomic-poll-queue-claim

Status: draft
Triggered by: using a Postgres table as a job/outbox queue and writing the "grab the next job" step by hand.
Model failure: claims a job with a `SELECT ... WHERE status='pending'` in one statement and a separate `UPDATE ... SET status='running'` in another, with no row lock and no status guard. Two workers polling at the same time both read the same row before either writes it back, so the job is claimed — and processed — twice. The real defect is a non-atomic claim, not "missing SKIP LOCKED".
Blast radius: duplicate processing of each job under concurrency — double charges, double emails, double side effects — silently, only when more than one worker runs.
Detect: a poll loop that reads candidate rows and marks them claimed in a separate statement/transaction, with no `FOR UPDATE`, no `SKIP LOCKED`, and no conditional guard (`status='pending'`) inside the UPDATE/DELETE itself.
Safe pattern: make the claim atomic. Any of these is correct:
  - `SELECT ... FOR UPDATE SKIP LOCKED` then update — the standard high-throughput option; locked rows are skipped so workers do not block each other.
  - a single conditional `UPDATE ... SET status='running' WHERE id=$1 AND status='pending' RETURNING ...` (or `DELETE ... RETURNING` for delete-on-claim) — the claim succeeds only if the row was still pending; check that a row came back.
  - plain `SELECT ... FOR UPDATE` — correct, but workers contend on the lock; fine when the claim transaction is short.
  SKIP LOCKED is one good option, not the only correct one.
  None of these give exactly-once: after a claim a worker can crash mid-processing and a reaper/visibility-timeout will redeliver, so the consumer must still be idempotent / dedupe / compensate.
Verifier: `tests/cards/pg_non_atomic_claim.py` + `tests/cards/test_pg_non_atomic_claim.py` (needs a reachable PostgreSQL) prove four facts: non-atomic SELECT-then-UPDATE hands the same row to two workers; `FOR UPDATE SKIP LOCKED` gives each row to exactly one worker without blocking; conditional `UPDATE ... RETURNING` claims exactly once under concurrent writers; and an atomically-claimed job is still delivered twice after a crash + requeue. Run: `PGHOST=... PGDATABASE=... uv run --with psycopg2-binary python tests/cards/pg_non_atomic_claim.py` and the same env with `--with pytest python -m pytest tests/cards/test_pg_non_atomic_claim.py -q`.
Escape hatch: a single-worker consumer, or a real broker (SQS/RabbitMQ/Redis Streams) that already provides the claim — the card is about hand-rolled SQL-table queues.
Sources: PostgreSQL SELECT reference — `FOR UPDATE ... SKIP LOCKED` (https://www.postgresql.org/docs/current/sql-select.html); PostgreSQL explicit locking (https://www.postgresql.org/docs/current/explicit-locking.html).

## pg-bytea-key-without-length-check

Status: production-tested (live DB check 2026-07-19: hex-text insert rejected by the CHECK, 32-byte insert accepted)
Triggered by: BYTEA column used as a dedupe/unique key (sha256 or another fixed-length digest), written from Go/pgx or any driver that encodes both strings and byte slices.
Model failure: passes the hex STRING instead of the raw `[]byte` digest. The driver happily encodes the 64 ASCII hex characters as a 64-byte value; `UNIQUE(sha256)` still "works" but 64-byte values never collide with 32-byte ones, so deduplication silently stops. Nothing errors.
Blast radius: duplicates accumulate in a table whose whole point is dedupe; every consumer downstream sees repeated items; the defect is invisible until someone measures.
Detect: `SELECT octet_length(<key>), count(*) FROM <table> GROUP BY 1` shows mixed lengths (32 and 64); dedupe hit-rate drops to ~0 after a code change on the write path.
Safe pattern: `CHECK (octet_length(sha256) = 32)` on the column. It converts the silent type confusion into a loud insert error at the first wrong write. Keep passing raw bytes from the app, but do not rely on that alone.
Verifier: `INSERT` with a hex string cast through text must fail the CHECK; `INSERT` with a real 32-byte value must pass. Both directions live-verified 2026-07-19.
Escape hatch: columns that legitimately store variable-length blobs — the CHECK is for fixed-length digest keys only.
Sources: PostgreSQL docs — Binary Data Types (bytea); PostgreSQL docs — Constraints (CHECK constraints).

## inference-gpu-arch-wheel-mismatch

Status: observed (Pascal-class GPU node, 2026-07-19)
Triggered by: choosing a serving stack for a GPU node; installing default PyPI `torch` on an older NVIDIA card.
Model failure: assumes "GPU node" means the default torch wheel will use the GPU. Modern default wheels (e.g. `torch 2.x +cu13x`) are built for sm_75+ and need a CUDA runtime newer than the node's driver supports. On a Pascal card (Tesla P100 = sm_60, CUDA-12.8-era driver) `torch.cuda.is_available()` returns False and the service silently runs on CPU. AWQ/int4 kernels also require sm_75+.
Blast radius: capacity plan built around a GPU that is effectively a CPU node; latency budgets miss; time burned on quantization stacks that can never run on this hardware.
Detect: `torch.cuda.is_available()` is False on a node where `nvidia-smi` works; the card's compute capability is absent from `torch.cuda.get_arch_list()`.
Safe pattern: inventory before stack choice — `nvidia-smi` for arch and driver version. Install a wheel built for that arch AND compatible with the driver's CUDA, or explicitly configure the service for CPU and size capacity accordingly. A GPU node that can only run CPU is a CPU node.
Verifier: pre-deploy on the target node: `python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_arch_list())"`.
Escape hatch: intentional CPU fallback, stated in the service config and the capacity plan.
Sources: NVIDIA CUDA GPUs compute capability table; PyTorch release notes (supported architectures and CUDA per wheel); CUDA Toolkit release notes (driver compatibility).

## inference-hf-implicit-token-401

Status: observed (shared inference node, 2026-07-19; the same env fix pre-applied on two more nodes)
Triggered by: downloading model weights on a shared node via huggingface_hub (`snapshot_download`, `from_pretrained`, first service start).
Model failure: debugs a 401 `RepositoryNotFoundError` on a PUBLIC model as "wrong repo id" or "model gated". Real cause: a stale `~/.cache/huggingface/token` left by another project; huggingface_hub sends it implicitly, and the Hub returns 401 even for public repos. `curl` without a token fetches the same file with 200.
Blast radius: deploys blocked on any shared node with a leftover token; hours lost chasing a nonexistent repo problem; deleting the token file breaks the other project.
Detect: hub client 401s a repo that `curl -sI <hub file URL>` answers with 200; `~/.cache/huggingface/token` exists and does not belong to this service.
Safe pattern: set `HF_HUB_DISABLE_IMPLICIT_TOKEN=1` in the service environment and pass `token=False` to explicit downloads. Do not delete the token file — it is another project's credential.
Verifier: `curl -sI` on a hub file URL returns 200 while the Python client 401s ⇒ implicit token is the cause; after the env fix the same multi-GB download completes anonymously.
Escape hatch: services that need gated/private models get their own explicit token via env, never the shared cache file.
Sources: huggingface_hub docs — Environment variables reference (`HF_HUB_DISABLE_IMPLICIT_TOKEN`); huggingface_hub docs — Authentication guide.

## infra-node-python-too-new-for-wheels

Status: observed (venv build failed on the node's default python3, 2026-07-19)
Triggered by: building a service venv on a node whose default `python3` is very new (e.g. 3.14), then pip-installing ML packages.
Model failure: uses whatever `python3` resolves to. The newest interpreter has no cpXX wheels yet for torch/ML stacks, so pip fails or tries to compile from source. Second trap on macOS: non-login SSH sessions do not have `/opt/homebrew/bin` on PATH, so `which python3.12` reports "not found" while the binary exists.
Blast radius: deploy fails late, or the agent concludes the interpreter "is not installed" and installs a duplicate toolchain.
Detect: pip "no matching distribution" errors for packages that ship wheels; `which` disagrees with `ls /opt/homebrew/bin`.
Safe pattern: create venvs with an explicitly versioned interpreter by ABSOLUTE path (`/opt/homebrew/bin/python3.12 -m venv ...`); make the interpreter path a deploy-script parameter, not an assumption.
Verifier: before deploy: `ssh node '<abs-python> -c "import sys; print(sys.version)"'` plus a pip dry-run of the requirement set on the node.
Escape hatch: pure-stdlib services.
Sources: PyTorch Get Started install matrix (supported Python versions); Python Packaging User Guide (binary wheels are built per interpreter tag).

## infra-one-way-overlay-inline-media

Status: observed (node-to-core fetch: curl exit 000, empty access log, 2026-07-19)
Triggered by: inference service that accepts media only as an `http(s)` URL or a node-local path, with media hosted on the app host and nodes reached over an overlay network.
Model failure: assumes reachability is symmetric because app-host-to-node calls work. Overlay networks are often one-directional (no reverse route or identity for node-to-core), so the node cannot fetch anything from the app host. The service deploys green, passes node-local tests, and fails on the first real request.
Blast radius: the whole media pipeline is dead in production while every deploy check is green.
Detect: node-side `curl <app-host URL>` fails (exit 000 / timeout) and the app host's access log stays empty, while app-host-to-node requests work; the service input loader handles only URL/path.
Safe pattern: every inference service accepts `data:` URIs (base64) in the same field as URLs; the client inlines media. Probe the reverse direction before choosing URL transport.
Verifier: live call from the app host with a data-URI payload returns 200; a node-to-app-host `curl` probe is part of pre-deploy checks.
Escape hatch: fleets with verified bidirectional routing — keep URL transport, keep the reverse probe in deploy checks.
Sources: RFC 2397 (the "data" URL scheme); the one-way route itself is observed overlay behavior, not documented.

## inference-encoder-in-prompt-loop

Status: production-tested (before/after latency measured on a live moderation service, 2026-07-19)
Triggered by: zero-shot classification or scoring with several prompt/label sets over one input (CLIP/SigLIP-style), especially on CPU.
Model failure: runs the input encoder once per prompt set and re-encodes constant prompt texts on every request. The loop "for each prompt ladder: encode and compare" reads naturally and errors never fire — it is only 5-10x slower. Measured: 4 image-encoder passes + per-request text encoding = 11.4 s/image on CPU; after the fix 1.3-1.8 s warm.
Blast radius: latency blows the client timeout of every caller; on a queue-fed service this feeds a retry storm (see `infra-colocated-cpu-services-retry-storm`).
Detect: encoder forward called inside a loop over prompt/label sets; text embeddings of constant prompts computed per request instead of per process.
Safe pattern: encode the input once per request and reuse the features across all prompt ladders; cache constant text embeddings at process scope (`functools.lru_cache` or init-time precompute).
Verifier: latency measured before/after on the same input (curl timing); grep for encoder calls inside per-prompt-set loops.
Escape hatch: prompts that genuinely change per request (user queries) — cache only what is constant.
Sources: measured behavior on a live service; Python functools docs (`lru_cache`).

## infra-colocated-cpu-services-retry-storm

Status: observed (two-service CPU node during bulk ingest, 2026-07-19)
Triggered by: placing two CPU-bound inference services (e.g. OCR + moderation) on one node, fed by a queue worker with fixed concurrency and a client timeout.
Model failure: sizes worker concurrency to the fastest service and assumes colocation is free. Under ingest the services contend for the same cores, response time crosses the client timeout, the queue retries, and retries add more load. Measured collapse: 2/1500 items in 100 minutes. The best-effort stage was skipped silently: coverage 1/1500 rows with zero errors logged.
Blast radius: throughput collapse under exactly the load the pipeline was built for; silent data-quality loss in every skip-on-error stage — nobody notices without a metric.
Detect: two CPU-heavy services on one node; client timeout + retry with no server-side concurrency cap; best-effort stage with no skip counter.
Safe pattern: spread CPU-bound services across nodes. Give each service its own server-side semaphore (max-concurrency env) so it protects itself regardless of client behavior. Size worker concurrency from the slowest shared resource. Count and log the skip rate of every best-effort stage.
Verifier: load run of N items — throughput does not degrade as worker concurrency rises; per-stage coverage metric is ~100% or the gap is explained.
Escape hatch: colocation with measured headroom AND a server-side cap on each service.
Sources: Google SRE — Addressing Cascading Failures; Azure Retry Storm antipattern.

## infra-enable-now-not-a-restart

Status: observed (redeploy served stale code and stale env, 2026-07-19)
Triggered by: deploy script that rsyncs code/env and then runs `systemctl --user enable --now`, or relies on launchd `RunAtLoad`.
Model failure: assumes `enable --now` (re)starts the unit. For an already-running unit it is a no-op: the old process keeps serving old code and the old environment — here a stale `cuda` device setting survived the fix that removed it. The deploy log says success; the behavior is stale.
Blast radius: fixes never reach production while deploys report success; debugging targets new code that is not actually running.
Detect: deploy script has no `restart`/`try-restart`/`kickstart -k` step; service behavior contradicts the just-synced code.
Safe pattern: `systemctl --user restart <unit>` (or `try-restart`) after every sync; on launchd, `launchctl kickstart -k gui/$UID/<label>`. End the deploy with a version probe, not with the sync.
Verifier: post-deploy, the service reports a version/build marker (e.g. a field in `/health`) matching what was just synced.
Escape hatch: none for code deploys; `enable --now` alone is only sufficient on first install.
Sources: systemctl(1) man page (enable/start semantics: start does nothing to a running unit); launchctl(1) man page (`kickstart -k`); launchd.plist(5) (`RunAtLoad`).

## infra-launchd-bootstrap-io-error

Status: observed (twice, on two different macOS nodes, 2026-07-19)
Triggered by: `launchctl bootstrap gui/$UID <plist>` during redeploy of a LaunchAgent.
Model failure: treats "Bootstrap failed: 5: Input/output error" as a broken plist and starts rewriting a working file. The label is in a transitional state after a previous load/unload; the plist is fine.
Blast radius: deploy loops on a red herring; agents "fix" valid plists and can corrupt a working service definition.
Detect: bootstrap fails with error 5 right after a bootout or a previously failed load, while `plutil -lint` says the plist is valid.
Safe pattern: deterministic sequence: `launchctl bootout gui/$UID/<label>` (ignore "No such process"), `sleep 3`, `launchctl bootstrap gui/$UID <plist>`, `launchctl enable`, `launchctl kickstart -k`. Manage only your own labels; never touch co-tenant processes.
Verifier: after the sequence, `launchctl print gui/$UID/<label>` shows the service running and the health endpoint answers.
Escape hatch: none needed; the sequence is idempotent.
Sources: launchctl(1) man page (bootstrap/bootout/kickstart subcommands); the transitional-state error itself is observed behavior, not documented.

## infra-shared-append-log-merge-conflict

Status: observed (this pipeline's own PR queue, 2026-07-19)
Triggered by: a multi-branch pipeline (agent or human) where every branch appends an entry to the tail of the same tracked file -- a changelog, evidence log, or registry.
Model failure: treats "append to the log" as a safe, additive operation because each individual diff is non-overlapping in intent. Git's default line-based merge driver only sees that two branches both touched the final lines of the same file and calls it a conflict, even though the correct resolution is always "keep both blocks". Auto-merge tooling has no conflict-resolution logic, so it silently declines to merge and gives no actionable signal -- the PR just sits open until a human hand-resolves a "conflict" that was never semantically one.
Blast radius: every PR opened before the previous one merges into the same file is guaranteed `CONFLICTING`; queue depth compounds (PR3 conflicts with PR2 which conflicts with PR1); auto-merge stalls silently with no exit code or alert, so an unattended pipeline looks idle rather than broken.
Detect: two or more open branches append to the tail of the same tracked file; the repo has no merge driver configured for that path; auto-merge is enabled but PRs accumulate with `mergeable: CONFLICTING` / `mergeStateStatus: DIRTY`.
Safe pattern: either (a) mark the append-only file `merge=union` in `.gitattributes` (e.g. `EVIDENCE_LOG.md merge=union`) so concurrent tail-appends merge automatically, keeping both blocks -- git's built-in union low-level driver needs no extra `[merge "union"]` config; or (b) switch to a one-file-per-entry layout (`entries/<date>-<slug>.md`) so concurrent branches touch disjoint paths and never collide. Prefer (b) when entries need independent review or revert; (a) is a fast retrofit for an existing single-file log.
Verifier: reducer branches twice from one commit, appends a distinct block to the tail of the same file on each branch, merges one, then merges the other -- asserts a real conflict with the default driver, then asserts a clean merge with both blocks kept once `.gitattributes` sets `merge=union`, and asserts a clean merge under the per-entry-file layout. `tests/cards/infra_shared_append_log_merge_conflict.py` + `tests/cards/test_infra_shared_append_log_merge_conflict.py`.
Escape hatch: union merge has no semantic check -- it happily keeps two branches that each "resolve" the same underlying case differently, silently accepting a contradiction instead of flagging it. For content where order or mutual exclusivity matters, prefer the per-entry-file layout so an actual duplicate/contradiction still surfaces as a normal path-level review question instead of being merged away.
Sources: gitattributes(5) `merge` attribute and the built-in `union` low-level merge driver (documented behavior, verified directly against the installed git in this repo).

## inference-mlx-not-thread-safe

Status: observed (concurrent smoke test, 3 of 4 requests failed, 2026-07-19)
Triggered by: serving mlx / mlx-vlm generation behind sync FastAPI (or any framework that runs sync handlers in a threadpool).
Model failure: assumes the inference call is thread-safe like most service code. MLX Metal streams are thread-local: under concurrency 2 requests fail with "There is no Stream(gpu, N) in current thread". The service passes every single-request smoke test.
Blast radius: hard failures under any real concurrency, discovered in production traffic instead of deploy checks.
Detect: mlx generate/encode called from framework-managed threads without serialization; errors naming a missing GPU stream in the current thread.
Safe pattern: wrap generation in a `threading.Lock` — one GPU generates one sequence at a time anyway, so the lock only makes the queueing explicit. Alternative: one dedicated inference thread with a queue.
Verifier: parallel smoke test at concurrency >= 2: all responses 200.
Escape hatch: none for threadpool servers; async single-worker designs that never touch mlx from two threads.
Sources: MLX documentation (streams / unified memory execution model); FastAPI docs — sync `def` endpoints run in an external threadpool.
