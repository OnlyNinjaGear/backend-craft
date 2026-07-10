# forward-test 007: retry-wrapper

> **Run-integrity note (2026-07-10):** tested agents in this batch were not
> isolated; implementation-shaped tasks edited the shared fixtures in place
> while sibling tests were reading them. Fixtures were restored from pristine
> snapshots afterwards and re-verified (see FORWARD_TESTS.md isolation rules).
> Design-only tests (001, 007) are unaffected.

Date: 2026-07-10
Fixture: none (design task)
Score: 4/4
Generic advice: False
Verifier quality (judge): Strong. Real executed verifier: bounded retry, jitter cap, Retry-After timing, 400-not-retried, non-idempotent-not-retried (timeout and 503), caller abort, and total-budget tests run against a real local HTTP server with programmable failures; output inspected and independently reproduced by the grader (ALL CHECKS PASSED), plus strict typecheck. Verifiers match the changed behavior exactly and mirror reliability-async.md's verifier list.

## Prompt

```text
Our external CRM API sometimes times out. Add retries around the call.
```

## References loaded (from agent's 'Files read')

- SKILL.md
- references/reliability-async.md
- references/library-decisions.md
- references/language-adapters.md

## Judge summary

Exemplary answer. Impact Read performed first and correctly identified the P0 duplicate-side-effect risk (timed-out write may have executed) before any code. Routing matched the SKILL.md table (reliability-async, library-decisions, language-adapters), failure cards cited by exact name, dependency gate run against p-retry/axios-retry/cockatiel with a removal path. All five expected behaviors present and enforced in code. Proof is real: I independently re-ran the self-test (11 assertions against a real local HTTP server) and got ALL CHECKS PASSED; verifiers directly cover the changed behavior including the non-idempotent-not-retried guard, caller-abort propagation, and total-budget cap. Non-obvious failure modes surfaced: retry amplification across queue layers, idempotency key per logical operation not per attempt, 429-safe-for-non-idempotent nuance, budget-below-caller-deadline. Only nit: testing-verification.md not loaded despite the routing table's tests signal, but the produced verifiers already satisfy that reference, so no material gap.

## Misses

- none

## Changes needed in skill/reference/failure card

- none

## Tested agent answer (verbatim)

````text
# Add retries around the external CRM API call — design, code, and proof

## Impact Read (backend-craft)

1. **Public contracts:** none change; internal error surface gains typed `CrmHttpError` / `CrmUnavailableError`.
2. **Data:** whatever the CRM call writes (contacts/deals). **This is the real risk:** a timeout does not mean the request didn't execute — a blind retry of a create/update can duplicate CRM records (P0 duplicate-side-effect).
3. **Auth/tenant:** unchanged; CRM credentials stay where they are.
4. **Side effects that can repeat:** the CRM write itself, plus retry amplification if the call already sits inside a queue/job that retries.
5. **Existing tests:** none (greenfield); verifiers below were built and run.

Non-empty answers on 2 and 4 → loaded `reliability-async.md`, `library-decisions.md`, `language-adapters.md`.

## Assumptions

- TypeScript/Node service (matching the ts-fastify stack), Node ≥ 20 (`AbortSignal.any`/`AbortSignal.timeout`), outbound HTTP via built-in `fetch` (undici).
- "Times out" means both connect/read timeouts and slow 5xx from the CRM.
- The CRM is a typical SaaS API: returns `Retry-After` on 429, may or may not support an `Idempotency-Key` header (both paths covered below).

## Design decisions

| Decision | Choice | Why |
|---|---|---|
| Attempts | 3 total (1 + 2 retries), configurable | Bounded; more attempts mostly adds latency and load on a struggling CRM |
| Backoff | Exponential, **full jitter**: `U(0, min(cap, base·2ⁿ))`, base 200ms, cap 2s | Avoids `retry-without-jitter-or-cap` (synchronized retry storms) |
| Per-attempt timeout | 3s via `AbortSignal.timeout`, actually **cancels** the in-flight request | Avoids `timeout-without-cancellation-propagation` — an outer timer alone leaves sockets running |
| Total budget | 10s hard wall-clock across attempts + waits; must be < the caller's own deadline | "Bounded attempts" alone is not a deadline |
| Retryable | network errors (ECONNRESET/ECONNREFUSED/UND_ERR_*), timeouts, HTTP 408/429/500/502/503/504 | Transient by nature |
| Never retried | 400/401/403/404/409/422 (permanent for this payload); caller-initiated aborts | Retrying validation/auth errors wastes budget and masks bugs |
| **Idempotency gate** | Retries allowed only when the call is declared idempotent. GET/PUT/DELETE: yes. POST: only with a stable `Idempotency-Key`. Exception: 429 is safe to retry even non-idempotent (request was rejected, not executed) | The core safety rule: a timed-out POST may have executed; retrying without dedupe duplicates CRM records |
| `Retry-After` | Honored (seconds or HTTP-date), capped, counted against the budget | Downstream knows its capacity better than we do |
| Cancellation | Caller `AbortSignal` composed with the per-attempt timeout; abort stops retries immediately | Don't keep hammering the CRM for a client that already hung up |
| Observability | `onRetry` hook → log `{attempt, delayMs, reason}` + counter `crm_client_retries_total{reason}`; alert on retry-exhaustion rate | Retries hide degradation; make them visible |

**Retry amplification warning:** if this call runs inside a queue worker/cron that has its own retries, keep client attempts at 2–3 and make the outer layer the durable retry (attempts multiply: N_outer × N_client).

**Idempotency-key rule:** generate the key once per *logical operation* (e.g., derived from your order/contact id), not per attempt and not per HTTP call — otherwise retries of your own inbound request still duplicate. If the CRM has no idempotency support, do not retry its writes on timeout; instead move the write behind a durable queue with a dedupe/inbox check (`queue-consumer-not-idempotent` card), or use the CRM's upsert-by-external-id endpoint if one exists.

**Circuit breaker (follow-up, not this change):** the skill flags `circuit-breaker-missing-on-fragile-dependency`. If the CRM degrades for minutes at a time, add a breaker (e.g., cockatiel's `circuitBreaker` composed with this retry) so you fail fast instead of burning 10s budgets per request.

## Library decision (dependency gate)

- **Chosen:** small in-repo helper (~180 lines, zero dependencies) over built-in `fetch`/undici + `AbortSignal`.
- **Rejected:** `p-retry` (no Retry-After/idempotency semantics — you'd still write the risky parts yourself); `axios-retry` (would add axios only for retries); `cockatiel` (good fit *if/when* you also want circuit breaker/bulkhead — the helper's call shape makes later replacement mechanical).
- **Failure cards addressed:** `retry-without-jitter-or-cap`, `timeout-without-cancellation-propagation`, duplicate side effect on non-idempotent retry.
- **First verifier:** bounded retry test (run below, passing).
- **Removal path:** all call sites go through `fetchWithRetry(...)`; swapping in cockatiel later touches one file.

## Code sketch 1 — `src/crm/retry.ts` (verified, typechecks strict)

```ts
// Bounded, jittered, cancellation-aware retry wrapper for outbound HTTP.
export class CrmHttpError extends Error {
  constructor(message: string, readonly status: number, readonly attempts: number) {
    super(message);
    this.name = 'CrmHttpError';
  }
}

export class CrmUnavailableError extends Error {
  constructor(message: string, readonly attempts: number, readonly cause?: unknown) {
    super(message);
    this.name = 'CrmUnavailableError';
  }
}

export interface RetryPolicy {
  /** Total attempts including the first. */
  maxAttempts: number;
  /** Backoff base for full jitter: delay ~ U(0, min(cap, base * 2^n)). */
  baseDelayMs: number;
  /** Cap for a single backoff delay (also caps honored Retry-After). */
  maxDelayMs: number;
  /** Hard wall-clock budget across all attempts and waits. */
  totalBudgetMs: number;
  /** Deadline for each individual attempt. */
  perAttemptTimeoutMs: number;
}

export const DEFAULT_POLICY: RetryPolicy = {
  maxAttempts: 3,
  baseDelayMs: 200,
  maxDelayMs: 2_000,
  totalBudgetMs: 10_000,
  perAttemptTimeoutMs: 3_000,
};

export interface RetryRequest {
  url: string;
  init?: RequestInit;
  /**
   * Retries are only allowed when this is true. Set it for GET/HEAD/PUT/DELETE
   * with idempotent semantics, or for POST *only* when an Idempotency-Key
   * (stable per logical operation, not per attempt) is sent and the CRM
   * deduplicates on it. A timed-out POST may already have executed server-side;
   * retrying it without a key duplicates the side effect.
   */
  idempotent: boolean;
  /** Caller cancellation (e.g. inbound request abort). Never retried past. */
  signal?: AbortSignal;
  policy?: Partial<RetryPolicy>;
  /** Injection points for tests and observability. */
  fetchImpl?: typeof fetch;
  sleep?: (ms: number, signal?: AbortSignal) => Promise<void>;
  random?: () => number;
  onRetry?: (info: { attempt: number; delayMs: number; reason: string }) => void;
}

const RETRYABLE_STATUS = new Set([408, 429, 500, 502, 503, 504]);

function defaultSleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(signal.reason ?? new Error('aborted'));
    const t = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(t);
      reject(signal?.reason ?? new Error('aborted'));
    };
    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

function retryAfterMs(res: Response): number | undefined {
  const h = res.headers.get('retry-after');
  if (!h) return undefined;
  const secs = Number(h);
  if (Number.isFinite(secs)) return Math.max(0, secs * 1000);
  const date = Date.parse(h);
  if (!Number.isNaN(date)) return Math.max(0, date - Date.now());
  return undefined;
}

function isTransientNetworkError(err: unknown): boolean {
  // undici surfaces network failures as TypeError('fetch failed') with a cause,
  // or as UND_ERR_* / Node syscall errors.
  const codes = new Set([
    'ECONNRESET', 'ECONNREFUSED', 'ETIMEDOUT', 'EPIPE', 'EAI_AGAIN',
    'UND_ERR_CONNECT_TIMEOUT', 'UND_ERR_HEADERS_TIMEOUT',
    'UND_ERR_BODY_TIMEOUT', 'UND_ERR_SOCKET',
  ]);
  let e: unknown = err;
  for (let depth = 0; e !== null && typeof e === 'object' && depth < 4; depth += 1) {
    const code = (e as { code?: unknown }).code;
    if (typeof code === 'string' && codes.has(code)) return true;
    e = (e as { cause?: unknown }).cause;
  }
  return err instanceof TypeError; // 'fetch failed' without a recognized code
}

/**
 * Execute an outbound HTTP request with a bounded retry policy.
 * Returns the first successful (2xx) Response. Non-retryable statuses throw
 * CrmHttpError immediately; exhausted retries throw CrmUnavailableError.
 */
export async function fetchWithRetry(req: RetryRequest): Promise<Response> {
  const policy: RetryPolicy = { ...DEFAULT_POLICY, ...req.policy };
  const doFetch = req.fetchImpl ?? fetch;
  const sleep = req.sleep ?? defaultSleep;
  const random = req.random ?? Math.random;
  const start = Date.now();

  let lastReason: unknown;

  for (let attempt = 1; attempt <= policy.maxAttempts; attempt += 1) {
    req.signal?.throwIfAborted();
    const remaining = policy.totalBudgetMs - (Date.now() - start);
    if (remaining <= 0) break;

    const attemptTimeout = Math.min(policy.perAttemptTimeoutMs, remaining);
    const attemptSignal = req.signal
      ? AbortSignal.any([req.signal, AbortSignal.timeout(attemptTimeout)])
      : AbortSignal.timeout(attemptTimeout);

    let reason: string;
    try {
      const res = await doFetch(req.url, { ...req.init, signal: attemptSignal });
      if (res.ok) return res;

      if (!RETRYABLE_STATUS.has(res.status)) {
        // 400/401/403/404/409/422...: permanent for this payload; do not retry.
        throw new CrmHttpError(`CRM responded ${res.status}`, res.status, attempt);
      }
      // Retryable status. 429 means "we were told to back off", the request was
      // rejected, so it is safe to retry even for non-idempotent calls. For
      // 5xx/408 the request may have executed: idempotent-only.
      if (!req.idempotent && res.status !== 429) {
        throw new CrmHttpError(
          `CRM responded ${res.status}; not retrying non-idempotent request`,
          res.status, attempt,
        );
      }
      lastReason = new CrmHttpError(`CRM responded ${res.status}`, res.status, attempt);
      reason = `status ${res.status}`;
      // Drain body so the connection can be reused.
      await res.arrayBuffer().catch(() => undefined);

      if (attempt === policy.maxAttempts) break;
      const hinted = retryAfterMs(res);
      const backoff = random() * Math.min(policy.maxDelayMs, policy.baseDelayMs * 2 ** (attempt - 1));
      const delayMs = Math.min(hinted ?? backoff, policy.maxDelayMs);
      if (Date.now() - start + delayMs >= policy.totalBudgetMs) break;
      req.onRetry?.({ attempt, delayMs, reason });
      await sleep(delayMs, req.signal);
      continue;
    } catch (err) {
      if (err instanceof CrmHttpError) throw err;

      // Caller cancelled: never retry, propagate as-is.
      if (req.signal?.aborted) throw req.signal.reason ?? err;

      const timedOut =
        (err as Error)?.name === 'TimeoutError' || (err as Error)?.name === 'AbortError';
      const transient = timedOut || isTransientNetworkError(err);
      if (!transient) throw err;

      // A timeout means the request MAY have reached the CRM and executed.
      // Connection-refused-style errors are safe, but we cannot reliably tell
      // "never sent" from "sent, response lost", so the rule is uniform:
      if (!req.idempotent) {
        throw new CrmUnavailableError(
          'CRM call failed and request is not idempotent; not retrying',
          attempt, err,
        );
      }
      lastReason = err;
      reason = timedOut ? 'timeout' : 'network error';
    }

    if (attempt === policy.maxAttempts) break;
    const backoff = random() * Math.min(policy.maxDelayMs, policy.baseDelayMs * 2 ** (attempt - 1));
    if (Date.now() - start + backoff >= policy.totalBudgetMs) break;
    req.onRetry?.({ attempt, delayMs: backoff, reason });
    await sleep(backoff, req.signal);
  }

  throw new CrmUnavailableError(
    `CRM unavailable after retries (budget ${policy.totalBudgetMs}ms)`,
    policy.maxAttempts, lastReason,
  );
}
```

## Code sketch 2 — `src/crm/client.ts` (call-site shape)

```ts
import { fetchWithRetry, CrmUnavailableError } from './retry.js';

export class CrmClient {
  constructor(
    private readonly cfg: { baseUrl: string; apiKey: string },
    private readonly log: { warn: (o: object, msg: string) => void },
    private readonly metrics?: { retries: (reason: string) => void },
  ) {}

  private headers(extra?: Record<string, string>): Record<string, string> {
    return { authorization: `Bearer ${this.cfg.apiKey}`, 'content-type': 'application/json', ...extra };
  }

  private onRetry = (i: { attempt: number; delayMs: number; reason: string }) => {
    this.log.warn({ crm: true, ...i }, 'retrying CRM call');
    this.metrics?.retries(i.reason);
  };

  /** Read: naturally idempotent, retried freely. */
  async getContact(id: string, opts?: { signal?: AbortSignal }): Promise<unknown> {
    const res = await fetchWithRetry({
      url: `${this.cfg.baseUrl}/contacts/${encodeURIComponent(id)}`,
      init: { headers: this.headers() },
      idempotent: true,
      signal: opts?.signal,
      onRetry: this.onRetry,
    });
    return res.json(); // validate with a schema before trusting, per boundary rules
  }

  /**
   * Write: retried ONLY because we send a stable Idempotency-Key that the CRM
   * dedupes on. `operationId` must identify the business operation (e.g. our
   * record id), NOT a fresh uuid per call — otherwise our own upstream retries
   * still create duplicates.
   * If the CRM does not support idempotency keys, set idempotent: false here
   * and move this write behind a durable queue with an inbox/dedupe check.
   */
  async upsertContact(operationId: string, input: object, opts?: { signal?: AbortSignal }): Promise<unknown> {
    const res = await fetchWithRetry({
      url: `${this.cfg.baseUrl}/contacts`,
      init: {
        method: 'POST',
        headers: this.headers({ 'idempotency-key': `contact-upsert:${operationId}` }),
        body: JSON.stringify(input),
      },
      idempotent: true, // true BECAUSE of the key above
      signal: opts?.signal,
      onRetry: this.onRetry,
    });
    return res.json();
  }
}
```

Fastify wiring: pass the inbound request's abort through (`signal: req.raw.aborted ? ... : someRequestSignal`) or at minimum keep `totalBudgetMs` below the server/request timeout, so retries never outlive the request. Map `CrmUnavailableError` → 502/503 with a generic body; never echo CRM error payloads to clients.

## Verification (final proof contract)

Executed against a **real local HTTP server** with programmable failures, using the fixture's toolchain (`tsx`, Node 25); test harness injects nothing into the retry path except observation hooks. Command: `tsx selftest.ts` in scratchpad; also `tsc --noEmit --strict` on the helper → `TYPECHECK_OK`. All checks inspected and passing:

```
PASS retries transient network errors then succeeds   (socket destroyed twice, 200 on 3rd; exactly 3 requests)
PASS exactly 3 attempts made
PASS backoff delays bounded by cap
PASS retries 503 for idempotent request
PASS 400 not retried                                   (single request, CrmHttpError(400))
PASS 429 retried after Retry-After hint                (waited >= ~1s per header, even for POST)
PASS non-idempotent timeout not retried                (1 request, CrmUnavailableError)  <- duplicate-side-effect guard
PASS non-idempotent 503 not retried
PASS idempotent timeout retried up to maxAttempts then fails
PASS caller abort stops retries immediately            (1 request, caller's reason propagated)
PASS total budget caps elapsed time                    (stopped early despite maxAttempts=10)
ALL CHECKS PASSED
```

Port these scenarios into the repo as vitest tests (same assertions; inject `fetchImpl`/`sleep`/`random` for deterministic timing). Verified files: `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/crmRetry.ts` and `.../selftest.ts`.

## Rollout notes

- Ship with `maxAttempts: 3` and dashboards on `crm_client_retries_total` and retry-exhaustion errors; if exhaustion is frequent, add a circuit breaker rather than more attempts.
- Confirm against the CRM's docs (a) its idempotency-key header name and dedupe window, (b) its documented rate-limit/Retry-After behavior, before enabling retries on writes.
- If the call site is inside a queue worker, disable client-side retries for 5xx/timeout there and let the queue's durable retry own it (single retry layer).

## Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md (loaded via Skill tool)
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/library-decisions.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/src/app.ts
- /Users/oleg/Desktop/backend-skills/fixtures/ts-fastify/package.json
````
