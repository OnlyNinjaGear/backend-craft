# forward-test 107: retry-wrapper (round 2)

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
Verifier quality (judge): Strong. Not prescriptive-only: an executable 9-test suite exists in the scratchpad and passes when re-run by the grader (Ran 9 tests, OK). Coverage maps directly to the reference's verifier list: retry count/timing, jitter-within-cap, Retry-After-as-floor, oversized-Retry-After fail-fast, permanent-error zero-retry, attempt cap, per-attempt cancellation of a hung call (fake handler observes CancelledError), idempotency-key stability across attempts, retryable-status set. Deferred items (contract test against real CRM sandbox, outbox SKIP LOCKED and poison-row tests) are honestly scoped as needing a real environment.

## Prompt

```text

```

## Round-2 focus verdict

Focus 1 (idempotent vs mutating distinguished, stated assumption): PASS — explicit operation classification table plus stated assumptions and a docs-check gate. Focus 2 (bounded exponential backoff with jitter, max attempts/elapsed, Retry-After, no retry on permanent errors): PASS — all five elements present in both Python and TS implementations and each covered by a passing test. Focus 3 (no retry of non-idempotent mutation without idempotency key): PASS — POST retry conditional on a key created once per logical operation and reused every attempt (tested), with upsert/lookup/enqueue fallbacks and outbox row id as the durable key.

## References loaded

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/library-decisions.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md

## Judge summary

Round 2 fully closes the round-1 gaps. The agent led with the Impact Read, identified the ambiguous-timeout duplicate-write as the real P0, produced a complete safe retry shape (bounded attempts, max elapsed, full jitter, Retry-After floor, permanent-error fast-fail, cancellation propagation), and hard-gated retry of non-idempotent mutations behind a stable idempotency key with concrete fallbacks and an outbox design for must-succeed writes. Routing matched the SKILL.md table exactly, the library-decisions review-output format was followed, and the proof is real — the grader re-executed the 9-test suite in the scratchpad and it passes, covering jitter caps, Retry-After-vs-budget interplay, per-attempt cancellation, and idempotency-key stability. No generic checklist content; every recommendation carries a value, a code path, or a test. Score 4: non-obvious failure modes plus safe implementation plus verified proof.

## Misses

- none

## Changes needed

- none

## Tested agent answer (verbatim)

````text
# Retries around the external CRM API call — design and implementation plan

## Impact Read (per backend-craft; assumptions stated since there is no repo)

1. **Public contracts:** no field/schema changes, but the calling endpoint's worst-case latency grows to `attempts × per_attempt_timeout + backoff gaps`. The retry budget must fit inside the caller's own request deadline, or upstream clients will time out and re-submit — multiplying load.
2. **Data:** if the CRM call is a write (create contact/deal, update record), a retry can duplicate it. A **timeout is ambiguous** — the request may have succeeded server-side before the response was lost. This is the P0 risk in this task, not the missing retry loop.
3. **Principal/tenant:** unchanged; CRM credentials/tenant scoping are untouched by retry logic.
4. **Side effects that can repeat:** the CRM write itself, plus any local DB write paired with it (partial-failure risk).
5. **Existing proof:** none (no repo). Verifiers are prescribed below and the core helper is already test-proven (see Proof).

**Assumptions:** async service (sketches given for Python/asyncio and TypeScript/Node; the pattern is language-portable), CRM is HTTP/JSON, mix of reads (GET) and writes (POST/PUT), moderate call volume, and the CRM either supports an `Idempotency-Key`-style header or exposes upsert/natural-key semantics — verify against the actual CRM docs before shipping writes-with-retry.

---

## Design decisions

### 1. Classify operations before retrying anything (non-negotiable)

| Operation | Retry? | Precondition |
|---|---|---|
| GET / search | Yes | none |
| PUT full-resource update, DELETE | Yes | endpoint is genuinely idempotent |
| POST create / non-idempotent update | **Only with an idempotency key** | key generated once per logical operation and reused on every attempt (and across process restarts). If the CRM has no idempotency support: use its upsert-by-natural-key endpoint, or do lookup-before-create on reattempt, or don't retry in-request — enqueue for async reconciliation instead |

Never retry: 400, 401, 403, 404, 409, 422 (validation/auth/permanent errors). Fail fast and surface them.
Retry: connect errors, timeouts, 408, 429, 500, 502, 503, 504.

### 2. Retry shape (safe defaults)

- **Bounded attempts:** 4 total tries (3 retries).
- **Max elapsed budget:** 15 s overall (tune to fit inside the caller's deadline; for a 30 s upstream request timeout this leaves headroom).
- **Per-attempt timeout:** ~5 s total per attempt (connect ~2 s if the client separates it), nested inside the overall budget — the last attempt gets `min(per_attempt, remaining)`.
- **Exponential backoff with full jitter:** `delay = random() × min(cap, base × 2^(attempt−1))`, base 250 ms, cap 4 s. Jitter is mandatory — synchronized retries from many instances are a retry storm.
- **Respect `Retry-After`:** use it as a floor over the jittered delay; if it exceeds the remaining budget, give up immediately rather than sleeping past the deadline.
- **Cancellation propagates:** the per-attempt timeout must cancel the in-flight HTTP call (`asyncio.timeout` cancels the awaitable; Node passes `AbortSignal` into `fetch`; Go passes `context.Context`). An outer timer with the request still running is not a timeout.

### 3. Transaction boundary (cross-link fired: DB write paired with external call)

Never hold a DB transaction open across the CRM call. Two acceptable flows:

- **Read or best-effort sync path:** commit local state first, then call CRM with the in-request retry wrapper; on final failure return a degraded response or mark the record "sync pending".
- **Must-eventually-succeed writes (recommended for CRM sync):** **outbox pattern** — in the same short transaction as the local write, insert an outbox row (`id` doubles as the idempotency key). A worker drains the outbox, calls the CRM through the same retry wrapper, and updates `attempts` / `next_attempt_at`; after N worker-level attempts it parks the row as `dead` for alerting/manual replay. In-request retries then stay short (or are skipped entirely) because durability lives in the queue. Do not stack retry layers blindly: HTTP-client transport retries + wrapper retries + queue redelivery multiply attempts — pick one owner per layer (wrapper for transient blips, outbox/queue for durability).

### 4. Downstream protection

- **Bound concurrency** to the CRM (semaphore / pool sized to its rate limit); no `Promise.all`/`gather` over unbounded collections of CRM calls.
- If the CRM is fragile and called at volume, add a **circuit breaker** (open on failure-rate threshold, half-open probe) so 4×-amplified traffic doesn't hammer a dead dependency. At minimum, treat repeated `CrmUnavailableError` as a fast-fail signal.

### 5. Observability

- Log each retry with attempt number, reason (`transport: TimeoutError` / `http 503`), chosen delay, correlation id (the `on_retry` hook below).
- Metrics: `crm_request_total{outcome=success|permanent|unavailable}`, `crm_retry_total{reason}`, latency histogram per attempt. Alert on retry-rate spikes (leading indicator) rather than only on final failures.

---

## Code sketch 1 — retry wrapper (Python, verified by tests)

`crm_retry.py` (full verified source at `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/crm_retry.py`):

```python
RETRYABLE_STATUSES = frozenset({408, 429, 500, 502, 503, 504})

@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 4
    base_delay: float = 0.25
    max_delay: float = 4.0
    max_elapsed: float = 15.0
    per_attempt_timeout: float = 5.0

async def call_with_retry(attempt_fn, policy=RetryPolicy(), *, sleep=asyncio.sleep,
                          rand=random.random, clock=time.monotonic, on_retry=None):
    start = clock()
    attempts_made = 0
    while attempts_made < policy.max_attempts:
        remaining = policy.max_elapsed - (clock() - start)
        if remaining <= 0:
            break
        attempts_made += 1
        retry_after = None
        try:
            async with asyncio.timeout(min(policy.per_attempt_timeout, remaining)):
                resp = await attempt_fn(attempts_made)
        except (TimeoutError, ConnectionError, OSError) as exc:
            last_reason = f"transport: {type(exc).__name__}"
        else:
            if resp.status < 400:
                return resp
            if resp.status not in RETRYABLE_STATUSES:
                raise CrmPermanentError(resp.status)          # no retry
            last_reason = f"http {resp.status}"
            retry_after = _parse_retry_after(resp.headers)
        if attempts_made >= policy.max_attempts:
            break
        backoff_cap = min(policy.max_delay, policy.base_delay * 2 ** (attempts_made - 1))
        delay = rand() * backoff_cap                          # full jitter
        if retry_after is not None:
            delay = max(delay, retry_after)                   # server floor
        if delay >= policy.max_elapsed - (clock() - start):
            break                                             # would blow budget
        if on_retry: on_retry(attempts_made, last_reason, delay)
        await sleep(delay)
    raise CrmUnavailableError(attempts_made, clock() - start)
```

Usage with HTTPX (idempotency key created **once**, outside the attempt closure):

```python
async def create_crm_contact(client: httpx.AsyncClient, payload: dict) -> dict:
    idempotency_key = str(uuid.uuid4())          # or the outbox row id
    async def attempt(n: int):
        return await client.post(
            "/v1/contacts", json=payload,
            headers={"Idempotency-Key": idempotency_key},
            timeout=httpx.Timeout(5.0, connect=2.0),
        )
    resp = await call_with_retry(attempt, on_retry=log_retry)
    return resp.json()
```

## Code sketch 2 — same wrapper in TypeScript/Node (fetch/Undici + AbortSignal)

```typescript
const RETRYABLE = new Set([408, 429, 500, 502, 503, 504]);
interface Policy { maxAttempts: number; baseDelayMs: number; maxDelayMs: number;
                   maxElapsedMs: number; perAttemptMs: number; }
const DEFAULTS: Policy = { maxAttempts: 4, baseDelayMs: 250, maxDelayMs: 4_000,
                           maxElapsedMs: 15_000, perAttemptMs: 5_000 };

export async function callWithRetry(
  attempt: (n: number, signal: AbortSignal) => Promise<Response>,
  p: Policy = DEFAULTS,
): Promise<Response> {
  const start = Date.now();
  for (let n = 1; n <= p.maxAttempts; n++) {
    const remaining = p.maxElapsedMs - (Date.now() - start);
    if (remaining <= 0) break;
    let reason: string; let retryAfterMs: number | undefined;
    try {
      // AbortSignal.timeout cancels the in-flight fetch — no zombie requests
      const res = await attempt(n, AbortSignal.timeout(Math.min(p.perAttemptMs, remaining)));
      if (res.ok) return res;
      if (!RETRYABLE.has(res.status)) throw new CrmPermanentError(res.status);
      reason = `http ${res.status}`;
      const ra = Number(res.headers.get("retry-after"));
      if (Number.isFinite(ra) && ra >= 0) retryAfterMs = ra * 1000;
    } catch (err) {
      if (err instanceof CrmPermanentError) throw err;
      reason = `transport: ${(err as Error).name}`;   // TimeoutError, fetch failure
    }
    if (n === p.maxAttempts) break;
    let delay = Math.random() * Math.min(p.maxDelayMs, p.baseDelayMs * 2 ** (n - 1));
    if (retryAfterMs !== undefined) delay = Math.max(delay, retryAfterMs);
    if (delay >= p.maxElapsedMs - (Date.now() - start)) break;
    log.warn({ attempt: n, reason, delayMs: delay }, "crm retry");
    await setTimeout(delay);   // from "node:timers/promises"
  }
  throw new CrmUnavailableError();
}
```

Go shape (not sketched in full): same policy struct; pass `context.WithTimeout` per attempt derived from an overall-deadline context into `http.NewRequestWithContext`; classify by status; full-jitter backoff via `rand.Float64()`.

## Code sketch 3 — outbox for must-succeed CRM writes

```sql
CREATE TABLE crm_outbox (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),  -- = Idempotency-Key
  operation       text NOT NULL,           -- 'contact.create', 'deal.update'
  payload         jsonb NOT NULL,
  status          text NOT NULL DEFAULT 'pending',  -- pending|done|dead
  attempts        int  NOT NULL DEFAULT 0,
  next_attempt_at timestamptz NOT NULL DEFAULT now(),
  last_error      text,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON crm_outbox (next_attempt_at) WHERE status = 'pending';
```

Worker loop (pseudocode): `SELECT ... WHERE status='pending' AND next_attempt_at <= now() ORDER BY next_attempt_at LIMIT 50 FOR UPDATE SKIP LOCKED` → call CRM via the retry wrapper with `Idempotency-Key = row.id` → on success `status='done'`; on failure `attempts += 1`, `next_attempt_at = now() + jittered_backoff(attempts)` (worker-level backoff in minutes, capped); after e.g. 8 attempts `status='dead'` + alert. The local business write and the outbox insert share one short transaction; the CRM call happens outside any transaction.

---

## Library recommendation (per library-decisions review-output format)

- **Chosen:** small explicit helper as above (~70 lines, fully tested). The skill's rule applies directly: retries are semantics the team must reason about (idempotency, budgets, Retry-After), and hiding them behind a generically-configured library is how double-retry layers and unjittered storms ship.
- **Alternatives rejected:** Python `tenacity` (solid, but `Retry-After` and overall-elapsed-vs-per-attempt budget need custom wait/stop wiring anyway — at that point the explicit loop is smaller and clearer); Node `p-retry`/`axios-retry` (no first-class `Retry-After` floor + budget interplay); `got` (built-in retry with Retry-After is good — reasonable choice if the project already uses got). Go: `cenkalti/backoff/v4` is fine if the org already depends on it.
- **Failure cards addressed:** `retry-without-jitter-or-cap`, `timeout-without-cancellation-propagation`, duplicate-side-effect on ambiguous timeout.
- **First verifier:** the bounded retry test suite below — already written and passing.
- **Docs check:** exact CRM idempotency-header semantics and rate-limit headers must be verified against the vendor's docs before enabling retry on writes; that is the one external unknown in this design.

## Verifier plan (what CI must hold)

1. **Retry count and timing test** — attempts capped, delays within jitter caps (done, passing).
2. **Retry-After respected as floor; oversized Retry-After fails fast** (done, passing).
3. **Permanent errors not retried** — 400 raises immediately, zero sleeps (done, passing).
4. **Cancellation test** — hung CRM call is actually cancelled by the per-attempt timeout (done, passing: fake handler observes `CancelledError` on both attempts).
5. **Duplicate-delivery/idempotency test** — same idempotency key observed on every attempt (done, passing); once wired to the real client, add a contract-level test that two identical keyed POSTs yield one CRM record (needs sandbox).
6. **Outbox tests (when built):** duplicate worker pickup is safe (`SKIP LOCKED` + idempotency key), poison row reaches `dead` and alerts.

## Proof (final proof contract)

Test run: `python3 test_crm_retry.py` in the scratchpad — **9 tests, all OK** (`Ran 9 tests in 0.112s — OK`): `test_succeeds_after_two_timeouts_with_bounded_backoff`, `test_jitter_stays_within_cap`, `test_respects_retry_after_as_floor`, `test_permanent_error_not_retried`, `test_attempt_cap_enforced`, `test_overall_budget_stops_early_when_retry_after_exceeds_it`, `test_per_attempt_timeout_cancels_hung_call`, `test_idempotency_key_stable_across_attempts`, `test_retryable_status_set`. Sources: `/private/tmp/claude-501/-Users-oleg-Desktop-backend-skills/865896dc-0bc7-415d-9004-f7ecf2e11c41/scratchpad/crm_retry.py` and `.../scratchpad/test_crm_retry.py`. The TypeScript and SQL sketches are design artifacts, untested here because no Node/DB project exists in this environment.

## Open items before shipping

1. Confirm the CRM's idempotency mechanism (header name, key TTL, scope) — gates retry-on-write.
2. Set the overall budget from the real upstream deadline, not the defaults above.
3. Decide in-request retry vs outbox per call site (reads: in-request; must-succeed writes: outbox).
4. Ensure the HTTP client's own transport retries are disabled or accounted for (single retry owner per layer).

## Files read

- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/SKILL.md (loaded via Skill tool)
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/reliability-async.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/persistence-migrations.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/library-decisions.md
- /Users/oleg/Desktop/backend-skills/.claude/skills/backend-craft/references/language-adapters.md
````
