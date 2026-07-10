# API contracts

Read this when a change touches an endpoint, public DTO, status code, webhook,
schema, pagination, error response, generated client, or external API contract.

## Contract read

Identify:

- route/method and consumers
- request schema, response schema, and error schema
- backward compatibility risk
- auth and tenant assumptions
- pagination/filter/sort behavior
- idempotency semantics for mutating operations

## Non-negotiables

### Public responses are explicit DTOs

Do not return persistence models directly. Direct model serialization causes
property leaks and contract drift.

Bad signatures:

- `return user`
- `return rows`
- `return document`
- `SELECT *` backing a public response
- object spread from ORM/document into response

Safe pattern:

- response schema/DTO lists fields explicitly
- server-owned/internal fields are opt-in only
- forbidden fields are asserted absent in tests

### Pagination is a launch decision

Any collection endpoint that can grow needs pagination at the outset. Adding
pagination later can break consumers that already expect an array or complete
result.

Safe pattern:

- request has `page_size`/`limit` with max cap
- response has cursor/token or explicit next link
- tests cover max page size and stable ordering

Escape hatch: tiny static enumerations with documented bounded cardinality.

### Exports are bounded work

Any full-collection export (CSV/report/bulk download) must bound its work: a
hard row cap, cursor pagination, a streamed response, or an async export job
with a download link. "The dataset is small today" is not an accepted waiver —
the endpoint's cost grows with the table. The row cap must be enforced in the
query itself (e.g. `LIMIT cap+1`), not after materializing all rows, so the DB
read is bounded too. Verifier: row-cap test or streamed-response assertion
(see `reliability-async.md` verifiers).

### Mutating retries require idempotency

If a POST/PATCH/DELETE can be retried and creates external or business side
effects, require an idempotency key or equivalent operation id.

Safe pattern:

- persist key + request fingerprint + final response/result
- replay same result for duplicate key
- reject same key with different fingerprint
- in-progress keys must be recoverable: a stored key with no response needs a
  lease timestamp and takeover/expiry after N seconds, otherwise a crash
  between key insert and response store bricks the key forever

Verifier: duplicate request produces one side effect; crashed first attempt ->
retry after lease expiry succeeds.

### Error responses use one contract

Avoid per-handler ad hoc error JSON. Use shared error mapping with stable error
codes and request/correlation id. Do not expose stack traces.

Verifier: contract tests cover representative 400, 401, 403, 404, 409, 422, 429,
and 5xx paths when those apply.

## Common failure cards

- `api-bola-id-swap`
- `api-bopla-property-leak`
- `api-mass-assignment`
- `api-pagination-late`
- `api-error-contract-drift`
- `api-idempotency-missing-on-mutation-retry`

## Useful checkers

- OpenAPI schema validation
- `oasdiff` for breaking changes
- Pact for consumer-driven contracts
- response snapshot/schema tests
- generated client compile test
