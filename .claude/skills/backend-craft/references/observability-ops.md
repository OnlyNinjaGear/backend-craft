# Observability and operations

Read this when adding or changing logs, metrics, traces, health checks, alerts,
background jobs, external calls, error handling, or operational runbooks.

## Observability read

Identify:

- request/job/correlation id
- business operation name
- dependency calls
- error code taxonomy
- metrics labels and cardinality
- security/audit events: rejected, unauthenticated, or invalid
  deliveries/requests must emit an explicitly tagged security event (distinct
  event type or audit field), not just a generic warning log
- owner/runbook for alerts

## Non-negotiables

### Every boundary needs correlation

HTTP requests, queue messages, cron jobs, and webhooks need a stable id that can
be found in logs/traces. Propagate it to outbound calls where possible.

### Metrics labels must be bounded

Do not use user id, email, UUID, raw path, request id, raw error message, SQL,
or tenant name as metric labels.

Safe labels:

- route template
- status class/code
- operation name
- dependency name
- bounded error code
- region/shard only if bounded and intentional

### Logs are for diagnosis, not data export

Log stable identifiers and decisions. Do not dump payloads. Use redaction and
structured fields.

### Alerts need action

Do not add alerts without owner, symptom, threshold rationale, and first
response. Prefer user-facing symptoms over internal noise.

## Common failure cards

- `observability-no-correlation-id`
- `metrics-high-cardinality`
- `pii-logged`
- `api-error-contract-drift`

## Verifiers

- smoke request shows correlation id in response/log/trace
- metric label review proves bounded cardinality
- log redaction test: send a payload containing a sentinel secret/PII value and
  assert the sentinel never appears in captured log output — redaction by
  design comment does not count
- alert/runbook link in config or docs
- OpenTelemetry instrumentation test when the project supports it
