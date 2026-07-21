# backend-craft evidence log

This is not a release changelog. It is the evidence log for rules that become
stronger over time.

Use [`FAILURE_CARDS.md`](../FAILURE_CARDS.md) for the current card corpus.

## Entry format

```md
## YYYY-MM-DD - short-failure-name

Context:
Artifact:
Expected:
Why the agent likely failed:
Failure card:
Rule/reference changed:
Checker/test added:
Status: observed | production-tested | retired
```

## Promotion rule

- one plausible source-backed risk: `draft` in `../FAILURE_CARDS.md`
- one real task failure: add entry here and mark card `observed`
- repeated failure or forward-test proof: mark card `production-tested`
- noisy or harmful rule: mark card `retired` and explain why

## Entries

## 2026-07-21 - infra-gha-pr-permission-toggle-silent-fail-card-added

Context: daily case-triage run over the intake queue. Only one open `case`/
`needs-triage` issue at run time: #15 (workflow-level `pull-requests: write`
looks sufficient for `gh pr create`, but a repo/org-level toggle -- "Allow
GitHub Actions to create and approve pull requests", off by default --
independently blocks it, and the job swallowed the error and reported
`success` with no PR created). A prior run (2026-07-20) had already looked at
#15 alongside #16 and picked #16 first specifically because its verifier
could stay hermetic (pure local git, no GitHub API); #15 was deferred, not
rejected. With #16 already merged and #15 now the only remaining candidate,
this run designed a verifier for #15 without needing live GitHub API calls:
the mechanism (job-level grant is necessary but not sufficient; a swallowed
terminal-step error lets the job report false success) reduces cleanly to a
mocked API client with two independent boolean flags, so it is fully
hermetic and deterministic in CI, same bar the prior run set for #16. No
overlap with any existing card: grepped `FAILURE_CARDS.md` for
`actions/permissions`, `pull-requests: write`, `gh pr create`, `GITHUB_TOKEN`
-- no matches; the existing `infra-*` cards cover deploy/process-management
and git-merge-semantics topics, none cover CI permission layering or
terminal-side-effect verification.
Artifact: `../FAILURE_CARDS.md` (new card
`infra-gha-pr-permission-toggle-silent-fail`),
`tests/cards/infra_gha_pr_permission_toggle_silent_fail.py` (new reducer),
`tests/cards/test_infra_gha_pr_permission_toggle_silent_fail.py` (new
verifier).
Expected: a pipeline that creates a PR as its terminal deliverable should
either produce that PR or fail the job loudly -- never report `success` with
the PR silently missing.
Why the agent likely failed: the workflow's own `permissions:` block is the
only permission surface the job can see and reason about from inside the
run, so it reads as complete; the repo/org toggle is invisible to the job
unless explicitly queried, and GitHub's own error text at PR-creation time is
easy to catch-and-log rather than treat as fatal, especially in a pipeline
built to be resilient to per-step noise. The reducer isolates the two facts
directly: (1) `create_pull_request` only succeeds when both an independent
job-level flag and a repo-level flag are true -- one true and one false still
raises; (2) a pipeline that catches that error and returns `"success"`
regardless does so with zero PRs created, while a pipeline with an explicit
preflight capability check and a postflight existence assertion fails loudly
in the identical scenario, and the postflight check alone still catches a
creation call that returns cleanly without a PR actually landing.
Failure card: `infra-gha-pr-permission-toggle-silent-fail` (new, `observed`
-- matches this pipeline's own real incident referenced in issue #15, plus
the reducer proves the two-layer-permission and swallowed-error mechanisms
directly rather than relying on the issue's narrative alone).
Rule/reference changed: none (the safe pattern is a pipeline-design
discipline -- preflight + postflight checks around a terminal side effect --
not a mechanical code pattern a Semgrep/ast-grep rule can usefully flag).
Checker/test added:
`tests/cards/test_infra_gha_pr_permission_toggle_silent_fail.py`, 5/5
passing; full suite `python -m pytest tests/cards/ -q` green (see PR
verifier output).
Sources verified: this run had no network/WebFetch access, so the GitHub
Docs citations in the card (repo/org toggle off by default;
`can_approve_pull_request_reviews` field on
`GET /repos/{owner}/{repo}/actions/permissions/workflow`) are corroborated
by the `gh api` output the source issue itself reports, not independently
re-fetched against current GitHub Docs this run -- the card notes this and
should be confirmed against live docs before promoting past `observed`.
Status: observed

## 2026-07-20 - infra-shared-append-log-merge-conflict-card-added

Context: daily case-triage run over the intake queue. Open `case`/
`needs-triage` issues at run time: #15 and #16, both filed against this
project's own case-triage pipeline rather than against a consumer backend.
Picked #16 (append-only shared log turns concurrent PRs into guaranteed merge
conflicts, auto-merge stalls silently) over #15 (workflow-level
`pull-requests: write` insufficient without a repo-level toggle, run stays
green while PR creation silently fails): #16's own verifier idea reduces to
pure local git operations with no GitHub API, network, or auth dependency, so
it is fully hermetic and deterministic in CI; #15's verifier would need to
mock `gh api repos/.../actions/permissions/workflow` and a real preflight
step, which is closer to a playbook/checker item than a reducer-provable
card. No overlap with any existing card: the corpus's `infra-*` cards cover
deploy/process-management ops, none cover git merge semantics or multi-branch
automation pipelines. This project's own `EVIDENCE_LOG.md` is itself an
instance of the exact pattern described (every case-triage PR appends to its
tail), so the card generalizes the pipeline's own operating risk, not just
the reporting issue's scenario.
Artifact: `../FAILURE_CARDS.md` (new card
`infra-shared-append-log-merge-conflict`),
`tests/cards/infra_shared_append_log_merge_conflict.py` (new reducer),
`tests/cards/test_infra_shared_append_log_merge_conflict.py` (new verifier).
Expected: two branches that each append a distinct entry to the tail of the
same shared file should both land in the file after both merge, without a
human needing to hand-resolve a conflict.
Why the agent likely failed: appending to a shared log looks like a purely
additive change with no risk of collision, so nothing in the pipeline design
anticipates that git's line-based merge driver treats "both branches touched
the file's final lines" as a real conflict regardless of semantic intent, and
that GitHub auto-merge has no fallback for it -- the PR just sits open with
no alert. The reducer proves three things directly against the installed
git: (1) with the default driver, the first branch's append merges cleanly
and the second branch's append against the same tail is a genuine conflict
(`git merge` exits non-zero, working tree shows `UU`); (2) marking the file
`merge=union` in `.gitattributes` from the start makes both merges clean and
keeps both blocks, using git's built-in union low-level driver (no custom
driver script needed, verified against the installed git); (3) switching to
one file per entry under `entries/` makes both merges clean because the
branches never touch the same path.
Failure card: `infra-shared-append-log-merge-conflict` (new, `observed` --
matches this pipeline's own real incident from 2026-07-19 referenced in the
issue, plus the reducer proves the mechanism directly against the installed
git rather than relying on the issue's description alone).
Rule/reference changed: none (git merge-conflict structure is not a
mechanical single-file pattern a Semgrep/ast-grep rule can usefully flag;
the safe pattern is a repo-configuration choice, not a code-level anti-pattern).
Checker/test added: `tests/cards/test_infra_shared_append_log_merge_conflict.py`,
3/3 passing (see PR verifier output).
Sources verified: gitattributes(5) `merge` attribute semantics and the
built-in `union` driver, confirmed directly by running the reducer against
the git binary installed in this environment (not taken from documentation
alone).
Status: observed

## 2026-07-20 - drf-default-throttle-unset-card-added

Context: daily case-triage run over the intake queue. Open `case`/
`needs-triage` issue at run time: #7 only -- issues #2, #3, #4, #5, and #6
were all already triaged and merged in prior runs
(`auth-cross-layer-prefix-exemption-gap`, `drf-authn-expansion-widens-authz`,
`drf-default-permission-unset`, `drf-authenticator-raises-instead-of-none`,
`drf-permission-flag-nulled-for-post-read`). Picked issue #7 as the single
remaining candidate: no `DEFAULT_THROTTLE_CLASSES` is configured, so the
token/login endpoint accepts unlimited requests -- credential brute force
plus, in a project with a per-request-DB-lookup authenticator, unrestricted
resource consumption. Issue #7's own "Best target artifact" field suggested
a checker, but a global-config-only check would miss the more interesting
half of the mechanism (a project that *does* set a generic project-wide
throttle scope but never gives the login endpoint its own), so this run
produced a card + fixture-tested reducer, matching the sibling DRF cards'
artifact shape and this project's admission bar (card + verifier, not a
claim alone). No overlap with any existing card: none of the corpus covers
throttling/rate limiting. Django 6.0.7 and djangorestframework 3.17.1 are
installed in this environment, so the reducer runs the real
`SimpleRateThrottle`/`ScopedRateThrottle`/`AnonRateThrottle` machinery
instead of a mock.
Artifact: `../FAILURE_CARDS.md` (new card `drf-default-throttle-unset`),
`tests/cards/drf_default_throttle_unset.py` (new reducer),
`tests/cards/test_drf_default_throttle_unset.py` (new verifier).
Expected: repeated requests to the token/login endpoint from one caller
identity should be capped by a rate scoped to that endpoint, independent of
throttle budget consumed by unrelated routes.
Why the agent likely failed: DRF's own built-in default for
`DEFAULT_THROTTLE_CLASSES` is `[]` -- confirmed against the installed
`rest_framework.settings.DEFAULTS` -- so a project that configures
authentication and permissions but never throttling ships an unmetered
login endpoint with nothing erroring. The subtler half: even a project that
adds a generic `AnonRateThrottle` project-wide shares one cache key
(`throttle_anon_<ip>`) across every anonymous route, so the login endpoint's
guess budget and an unrelated read endpoint's browsing budget are the same
bucket -- three unrelated GETs against a sibling endpoint can burn the
budget an attacker's first three login attempts would otherwise have used,
and neither traffic class gets a rate actually sized to what it is. The
reducer proves this with three variants in one process family, run each in
its own subprocess (Django settings configure once per process): `unset`
(ten rapid login POSTs, all 200), `shared` (three unrelated GETs then three
login POSTs from the same IP -- the third login attempt already 429s),
`dedicated` (the login view gets its own `ScopedRateThrottle` scope --
exhausting a sibling scope via five GETs does not touch the login budget,
and the login scope enforces its own independent cap).
Failure card: `drf-default-throttle-unset` (new, `draft` -- source-backed
against the DRF throttling docs and fixture-tested against real Django/DRF,
not yet observed on a second independent project or forward-tested).
Rule/reference changed: none (config-plus-scoping gap, not a mechanical
pattern suited to a Semgrep rule at this scope -- absence of a setting and
absence of a per-view attribute are both non-signals for a syntax-only
checker).
Checker/test added: `tests/cards/drf_default_throttle_unset.py` +
`tests/cards/test_drf_default_throttle_unset.py`. Three requests-sequence
assertions against the same two views (`ListView`, `LoginView`) and the
same anonymous IP, varying only the `REST_FRAMEWORK` throttle config: (1)
`unset` -- `[200]*10` on the login endpoint; (2) `shared` -- reads
`[200,200,200]`, then login `[200,200,429]`, proving the shared bucket
conflates the two traffic classes; (3) `dedicated` -- reads
`[200,200,200,200,200]` (scope exhausted), login still
`[200,200,200,429]` unaffected, proving scope independence.
```
$ python -m pytest tests/cards/test_drf_default_throttle_unset.py -q
3 passed

$ python -m pytest tests/cards/ -q
23 passed, 1 skipped (pre-existing PostgreSQL card, no reachable DB in this environment)

$ python scripts/validate_repo.py
validate_repo: ok
```
Status: draft

## 2026-07-20 - auth-cross-layer-prefix-exemption-gap-card-added

Context: daily case-triage run over the intake queue. Open `case`/
`needs-triage` issues at run time: #2 and #7 (issues #3, #4, #5, and #6 were
already triaged and merged in prior runs -- `drf-authn-expansion-widens-authz`,
`drf-default-permission-unset`, `drf-authenticator-raises-instead-of-none`,
`drf-permission-flag-nulled-for-post-read`). Picked issue #2 as the single
most promising remaining candidate: a global auth middleware exempts a URL
prefix (e.g. `/api/*`) trusting DRF to authenticate everything mounted there,
but a plain non-framework handler registered on that same prefix inherits
neither check and ships fully unauthenticated. Checked for overlap with the
existing `auth-middleware-scope-miss` card first: that card is about hook/
dependency encapsulation among *sibling routers within one framework layer*
(a Fastify hook or FastAPI router dependency not reaching a sibling router).
Issue #2 is a different mechanism -- a seam *between two layers* (a prefix-
exempting middleware and the framework it trusts to cover that prefix), so it
gets its own card rather than folding into the existing one. Issue #7 (no
default throttle on the token endpoint) targets a checker/config-assertion
artifact rather than a new failure card and was left for a future run.
Django 6.0.7 and djangorestframework 3.17.1 are installed in this
environment, so the reducer runs the real middleware/view dispatch instead of
a mock.
Artifact: `../FAILURE_CARDS.md` (new card
`auth-cross-layer-prefix-exemption-gap`),
`tests/cards/auth_cross_layer_prefix_exemption_gap.py` (new reducer),
`tests/cards/test_auth_cross_layer_prefix_exemption_gap.py` (new verifier).
Expected: every route reachable under the exempted prefix -- framework view
or not -- should require authentication before returning data.
Why the agent likely failed: the middleware's prefix check ("skip auth under
`/api/`, DRF handles it") is correct for DRF views and silently wrong for any
plain handler on the same prefix, because nothing else ever runs an auth
check for that handler. The middleware sees an exempted path and steps aside;
the plain handler has no auth code of its own and just returns data. Nothing
errors, and the diff that added the plain handler looks identical to any
other small utility view.
Failure card: `auth-cross-layer-prefix-exemption-gap` (new, `draft` --
source-backed and fixture-tested against real Django/DRF, not yet observed on
a second independent project or forward-tested).
Rule/reference changed: none (the gap is a cross-layer trust assumption, not
a mechanical pattern suited to a Semgrep rule at this scope).
Checker/test added: `tests/cards/auth_cross_layer_prefix_exemption_gap.py` +
`tests/cards/test_auth_cross_layer_prefix_exemption_gap.py`. One process,
one middleware instance, and a manual `get_response` dispatcher (standing in
for the URL resolver) prove four facts against the same middleware and the
same anonymous caller: (1) a plain non-DRF view under the exempted prefix
returns 200 with no credentials; (2) the same middleware still redirects an
anonymous caller outside the exempted prefix, proving the middleware itself
is not broken; (3) a real DRF view under the same exempted prefix still 403s,
proving the gap is specific to non-framework handlers, not the whole prefix;
(4) the same plain handler, once it checks `request.user.is_authenticated`
itself instead of trusting the prefix, 403s -- the safe pattern.
```
$ python -m pytest tests/cards/test_auth_cross_layer_prefix_exemption_gap.py -q
4 passed

$ python -m pytest tests/cards/ -q
20 passed, 1 skipped (pre-existing PostgreSQL card, no reachable DB in this environment)

$ python scripts/validate_repo.py
validate_repo: ok
```
Status: draft

## 2026-07-20 - drf-permission-flag-nulled-for-post-read-card-added

Context: daily case-triage run over the intake queue. Open `case`/
`needs-triage` issues at run time: #2, #6, #7 (same anonymized Django/DRF
authorization case source as prior runs). Issues #3, #4, and #5 were already
triaged and merged (`drf-authn-expansion-widens-authz`,
`drf-default-permission-unset`, `drf-authenticator-raises-instead-of-none`).
Picked issue #6 as the single most promising remaining candidate: it names a
concrete, mechanism-rich bug -- a method-based authorization mixin "fixed" for
two reads-over-POST actions by nulling the shared permission-flag attribute
instead of mapping those actions to the permission they actually need -- with
no overlap in the existing card corpus (distinct from
`drf-authn-expansion-widens-authz`, which is a coarse check silently widening
when a new authenticator is added; this is a guard attribute being cleared
outright inside the view's own permission check). Issue #7 (missing default
throttle) targets a checker/config-assertion artifact rather than a new card
and was left for a future run. Django + DRF are installed in this environment
(Django 6.0.7, djangorestframework 3.17.1), so the reducer runs against the
real library instead of a mock.
Artifact: `../FAILURE_CARDS.md` (new card
`drf-permission-flag-nulled-for-post-read`),
`tests/cards/drf_permission_flag_nulled_for_post_read.py` (new reducer),
`tests/cards/test_drf_permission_flag_nulled_for_post_read.py` (new verifier).
Expected: an authenticated principal holding none of a view's permissions
should get 403 on every action guarded by that view's permission flag,
including actions reached over `POST` that are semantically reads.
Why the agent likely failed: the mixin's `check_permissions` override
branches on `self.action`, and for the two misclassified read actions it sets
`self.permission_flag = None` before calling `super().check_permissions()`,
then restores the flag afterward. The shared permission class treats a falsy
flag as "nothing to check" -- a pattern that reads naturally as "these actions
don't need the write permission" but actually disables authorization for them
entirely, including for principals with none of the view's permissions. The
diff looks like an intentional, narrow read-classification fix, so it is easy
to approve in review without noticing the guard is gone.
Failure card: `drf-permission-flag-nulled-for-post-read` (new, `draft` --
source-backed and fixture-tested against real Django/DRF, not yet observed on
a second independent project or forward-tested).
Rule/reference changed: none (semantic view-logic bug, not a mechanical
pattern suited to a Semgrep rule at this scope).
Checker/test added: `tests/cards/drf_permission_flag_nulled_for_post_read.py`
+ `tests/cards/test_drf_permission_flag_nulled_for_post_read.py`. Both run in
a single process (unlike the sibling authn/permission cards, nothing here
touches `django.conf.settings` between variants) and prove, against the same
permission class and same two principals: (1) the buggy mixin returns 200 for
an unprivileged principal on `by_key` but still 403s the same principal on the
untouched `moderate` write action; (2) the fixed mixin (explicit
`action -> permission` map, no nulling) 403s the unprivileged principal on
`by_key` and 200s a principal holding only the mapped read permission, while
still 403ing that same read-only principal on `moderate`.
```
$ python -m pytest tests/cards/test_drf_permission_flag_nulled_for_post_read.py -q
4 passed

$ python -m pytest tests/cards/ -q
16 passed, 1 skipped (pre-existing PostgreSQL card, no reachable DB in this environment)

$ python scripts/validate_repo.py
validate_repo: ok
```
Status: draft

## 2026-07-20 - drf-authenticator-raises-instead-of-none-card-added

Context: daily case-triage run over the intake queue (issues #2, #5, #6, #7 --
same anonymized Django/DRF authorization case source as the 2026-07-19 and
prior 2026-07-20 runs). Issues #3 and #4 were already triaged in earlier runs
(`drf-authn-expansion-widens-authz` and `drf-default-permission-unset`, both
merged). Picked issue #5 as the single most promising remaining candidate: it
names a concrete, mechanism-rich bug in a custom `BaseAuthentication` --
raising instead of returning `None`, plus inferring credentials from an
unconstrained header scan -- with no overlap in the existing card corpus
(distinct from `drf-authn-expansion-widens-authz`, which is about a coarse
permission check silently widening; this is about the authenticator itself
breaking the fallback chain for principals it was never meant to touch).
Django + DRF are installed in this environment (Django 6.0.7,
djangorestframework 3.17.1), so the reducer runs against the real library
instead of a mock.
Artifact: `../FAILURE_CARDS.md` (new card
`drf-authenticator-raises-instead-of-none`),
`tests/cards/drf_authenticator_raises_instead_of_none.py` (new reducer),
`tests/cards/test_drf_authenticator_raises_instead_of_none.py` (new verifier).
Expected: a request carrying a valid session cookie should authenticate via
the session/JWT authenticator regardless of what a sibling API-key
authenticator does with headers it does not recognize.
Why the agent likely failed: DRF's documented contract is "return `None` if
authentication is not attempted, raise `AuthenticationFailed` if it is
attempted and fails" -- but "I could not find my own credentials" reads to a
model like a failure, not a no-op, so it raises. `Request._authenticate()` in
the installed djangorestframework 3.17.1 source stops the authenticator loop
on the first raised `APIException` and never tries the next authenticator, so
this is silent until a real session/JWT user happens to omit the API key or
sends an unrecognized header. Reducer runs the same protected `APIView`
(`permission_classes = [IsAuthenticated]`) against a buggy and a fixed
authenticator variant, each in a fresh subprocess (Django settings configure
once per process), across three request shapes: valid session cookie with no
API key, valid session cookie plus one unrelated header (e.g. a tracing
header), and a valid API key alone. The buggy variant returns 401 for the
first two despite a valid session and 200 only for the third; the fixed
variant (checks one named header, returns `None` if absent, uses
`hmac.compare_digest`) returns 200 for all three.
Failure card: `drf-authenticator-raises-instead-of-none` (draft --
source-backed via the DRF authentication docs and now fixture-tested via a
real installed Django/DRF reducer; not yet observed against a second
independent real project or forward-tested).
Rule/reference changed: card added; no existing card or reference edited.
Checker/test added: `python -m pytest
tests/cards/test_drf_authenticator_raises_instead_of_none.py -q` -- 6 passed;
full suite `python -m pytest tests/cards/ -q` -> 12 passed, 1 skipped (skip is
the pre-existing PostgreSQL card with no reachable DB in this environment,
unrelated to this change).
Status: draft (card-level; fixture-tested reducer proves the mechanism, no
forward test or second real-project sighting yet)

## 2026-07-20 - drf-authn-expansion-widens-authz-card-added

Context: daily case-triage run over the intake queue (issues #2-#7, the same
anonymized Django/DRF authorization case source as the 2026-07-19 run). Issue
#4 was already triaged in that prior run (`drf-default-permission-unset`,
merged). Picked issue #3 as the single most promising remaining candidate: it
names a distinct mechanism -- authentication-principal expansion silently
widening every bare-`IsAuthenticated` endpoint -- that none of the existing
cards cover (`drf-default-permission-unset` is about a missing default,
`authz-handler-only` and `auth-middleware-scope-miss` are about
encapsulation/scope, not the meaning of an authentication check changing
underneath an unedited permission check). Django + DRF are installed in this
environment (Django 6.0.7, djangorestframework 3.17.1), so the reducer runs
against the real library.
Artifact: `../FAILURE_CARDS.md` (new card `drf-authn-expansion-widens-authz`),
`tests/cards/drf_authn_expansion_widens_authz.py` (new reducer),
`tests/cards/test_drf_authn_expansion_widens_authz.py` (new verifier).
Expected: a view guarded only by `permission_classes = [IsAuthenticated]`
should keep denying a principal that was never meant to reach it, regardless
of which authentication classes are configured.
Why the agent likely failed: `IsAuthenticated` only checks
`request.user.is_authenticated`; it says nothing about which authenticator
resolved that user. Adding an authentication class to
`DEFAULT_AUTHENTICATION_CLASSES` is a global, one-line config change that
touches zero view files, so review of that change does not surface the
views it silently re-scopes. Reducer runs the same `APIView`
(`permission_classes = [IsAuthenticated]`, never edited) in two subprocesses
(Django settings configure once per process): one with only an empty
authenticator list (a request carrying a machine API-key header gets 403),
one with a machine API-key authenticator added (the same request now gets
200); a zero-credential request stays denied in both, showing the gap is
specific to the newly recognized principal, not a blanket `AllowAny` regression.
Failure card: `drf-authn-expansion-widens-authz` (draft -- source-backed and
now fixture-tested via a real installed Django/DRF reducer; not yet observed
against a second independent real project or forward-tested).
Rule/reference changed: card added; no existing card or reference edited.
Checker/test added: `python -m pytest tests/cards/test_drf_authn_expansion_widens_authz.py -q`
-- 2 passed (narrow -> 403/403, widened -> 200/401); full suite
`python -m pytest tests/cards/ -q` -> 6 passed, 1 skipped (skip is the
pre-existing PostgreSQL card with no reachable DB in this environment,
unrelated to this change).
Status: draft (card-level; fixture-tested reducer proves the mechanism, no
forward test or second real-project sighting yet)

## 2026-07-19 - inference-node-readiness-assumptions

Context: wiring a Go backend to self-hosted inference services (embedding,
OCR, moderation, VLM) on a heterogeneous fleet — two Apple Silicon nodes, one
Linux node with a Pascal-class GPU — reached over an overlay network. Owner
requested this scope extension (session 2026-07-19). Three independent "the
node is not what the plan assumed" failures during first deploys.
Artifact: node deploy scripts and service env files (project-private;
distilled into the cards and `references/self-hosted-inference.md`).
Expected: public model weights download anonymously; the default torch wheel
uses the node's GPU; the node's default `python3` can build the service venv.
Why the agent likely failed:
- a stale `~/.cache/huggingface/token` from another project was sent
  implicitly; the Hub 401s a PUBLIC repo while `curl` gets 200 — the error
  reads as "repo does not exist" and points away from the real cause;
- default PyPI torch is built for sm_75+ and a newer CUDA runtime than the
  node's driver; `torch.cuda.is_available()` is False and the "GPU node"
  silently serves on CPU;
- node `python3` was 3.14 (no ML wheels yet), and non-login SSH hides
  `/opt/homebrew/bin` from PATH, so `which python3.12` claimed a working
  interpreter did not exist.
Failure card: `inference-hf-implicit-token-401` (new),
`inference-gpu-arch-wheel-mismatch` (new),
`infra-node-python-too-new-for-wheels` (new) — all observed.
Rule/reference changed: new reference pack
`references/self-hosted-inference.md` (hardware inventory before stack
choice; download env hygiene; absolute interpreter path as a deploy
parameter); SKILL.md routing row for self-hosted inference signals.
Checker/test added: none mechanical; verifiers are the pre-deploy probe
commands recorded in each card.
Status: observed

## 2026-07-19 - redeploy-served-stale-process

Context: same fleet. A redeploy rsynced new code and env to an inference
node; the service kept answering with old behavior (stale app code, stale
`cuda` device setting). Separately, `launchctl bootstrap` failed with
"Bootstrap failed: 5: Input/output error" during redeploys on two macOS
nodes.
Artifact: deploy scripts (rsync + `systemctl --user enable --now`); launchd
plists and load sequence.
Expected: a deploy replaces the running process; bootstrap loads the agent.
Why the agent likely failed: `enable --now` starts a unit only if it is not
already running — it never restarts one, and launchd `RunAtLoad` behaves the
same, so the deploy log says success while the old process serves. The
bootstrap error looks like a broken plist but is a label caught in a
transitional state.
Failure card: `infra-enable-now-not-a-restart` (new, observed),
`infra-launchd-bootstrap-io-error` (new, observed — seen on two nodes).
Rule/reference changed: `references/self-hosted-inference.md` — a deploy
ends with an explicit restart plus a version-marker health probe; documented
bootout -> sleep -> bootstrap -> kickstart sequence.
Checker/test added: none mechanical; verifier is the post-deploy version
marker check.
Status: observed

## 2026-07-19 - encoder-rerun-per-prompt-set

Context: SigLIP zero-shot moderation service on CPU. Each request ran the
image encoder once per prompt ladder (4x) and re-encoded constant prompt
texts every request: 11.4 s per image.
Artifact: moderation service inference path (project-private; reduced to the
card's Detect/Safe pattern).
Expected: one image-encoder forward per request; constant prompt embeddings
computed once per process.
Why the agent likely failed: wrote the scoring loop as "for each prompt set:
encode and compare", which reads naturally and never errors; it is only
5-10x slower than encoding once.
Failure card: `inference-encoder-in-prompt-loop` (new, production-tested:
before/after measured with curl on the live service — 11.4 s -> 1.3-1.8 s
warm after encoding the image once and caching text features in
`lru_cache`).
Rule/reference changed: `references/self-hosted-inference.md` — "Encode
once; cache constant embeddings".
Checker/test added: none mechanical; verifier is the before/after latency
measurement plus grep for encoder calls inside prompt-set loops.
Status: production-tested

## 2026-07-19 - colocated-cpu-services-retry-collapse

Context: OCR and moderation, both CPU-bound, on one node; queue worker with
concurrency 8 and a 60 s client timeout feeding both.
Artifact: worker pipeline configuration and service logs (project-private).
Expected: bulk ingest completes; the best-effort OCR stage populates its
field.
Why the agent likely failed: sized worker concurrency to the fast path and
assumed colocation was free. Under load the two services contended for the
same cores, moderation crossed the client timeout, the queue retried, and
retries added load: 2/1500 items processed in 100 minutes. The best-effort
OCR stage skipped silently — coverage 1/1500 rows with zero errors logged.
Failure card: `infra-colocated-cpu-services-retry-storm` (new, observed).
Rule/reference changed: `references/self-hosted-inference.md` — spread
CPU-bound services; server-side max-concurrency semaphore per service;
worker concurrency sized from the slowest shared resource; skip rate counted
for every best-effort stage.
Checker/test added: none mechanical; verifiers are the load run (throughput
vs concurrency) and the per-stage coverage metric.
Status: observed

## 2026-07-19 - mlx-generate-not-thread-safe

Context: mlx-vlm captioning service behind sync FastAPI endpoints on an
Apple Silicon node.
Artifact: service endpoint code (project-private; pattern captured in the
card).
Expected: concurrent requests queue up and all succeed.
Why the agent likely failed: FastAPI runs sync endpoints in a threadpool and
MLX Metal streams are thread-local; at concurrency 2, 3 of 4 requests failed
with "There is no Stream(gpu, N) in current thread".
Failure card: `inference-mlx-not-thread-safe` (new, observed).
Rule/reference changed: `references/self-hosted-inference.md` — serialize
generate with a process-wide lock; smoke test at concurrency >= 2 before a
service counts as deployed.
Checker/test added: none mechanical; verifier is the parallel smoke test.
Status: observed

## 2026-07-19 - one-way-overlay-broke-url-transport

Context: same fleet. The app host serves media over its own HTTP; inference
services accepted media only as an `http(s)` URL or a local path.
Artifact: node-side fetch probe (curl exit 000, empty access log on the app
host) and service input loaders.
Expected: the node downloads media from the app host the same way the app
host reaches the node.
Why the agent likely failed: assumed reachability is symmetric because
app-host-to-node calls worked; the overlay had no reverse route/identity, so
the first real media request failed after a green deploy.
Failure card: `infra-one-way-overlay-inline-media` (new, observed).
Rule/reference changed: `references/self-hosted-inference.md` — every
inference service accepts `data:` URIs; reverse-fetch probe before choosing
URL transport.
Checker/test added: none mechanical; verifier is the live data-URI call plus
the node-to-app-host curl probe.
Status: observed

## 2026-07-19 - bytea-dedupe-key-silent-miss

Context: Go/pgx write path of the same project. BYTEA sha256 column with a
UNIQUE constraint used as the content dedupe key.
Artifact: live database check (reduced to the card's verifier).
Expected: `UNIQUE(sha256)` rejects duplicate content.
Why the agent likely failed: passed the hex string instead of the raw
`[]byte`; the driver encoded 64 ASCII bytes instead of the 32 digest bytes,
so UNIQUE kept "working" against values that never match — dedupe silently
stopped, with no error anywhere.
Failure card: `pg-bytea-key-without-length-check` (new, production-tested:
`CHECK (octet_length(sha256) = 32)` added and live-verified in both
directions — hex-text insert rejected, 32-byte insert accepted).
Rule/reference changed: none beyond the card; the rule is card-level.
Checker/test added: none mechanical; verifier is the pair of live inserts
against the CHECK.
Status: production-tested

## 2026-07-19 - drf-default-permission-unset-card-added

Context: daily case-triage run over the intake queue (issues #2-#7, all
Django/DRF authorization findings from one anonymized case source). Picked
issue #4 as the single most promising candidate: it is the root-cause failure
mode several of the sibling issues build on top of, it does not duplicate any
existing card (`authz-handler-only` and `auth-middleware-scope-miss` are about
encapsulation/scope, not the framework's own permission default), and Django +
DRF are actually installed in this environment (Django 6.0.7,
djangorestframework 3.17.1) so the reducer runs against the real library
instead of a mock.
Artifact: `../FAILURE_CARDS.md` (new card `drf-default-permission-unset`),
`tests/cards/drf_permission_fail_open.py` (new reducer),
`tests/cards/test_drf_permission_fail_open.py` (new verifier).
Expected: a view with no `permission_classes` should deny an unauthenticated,
zero-credential request.
Why the agent likely failed: `REST_FRAMEWORK` sets
`DEFAULT_AUTHENTICATION_CLASSES` (so it looks like auth is "handled") but
never sets `DEFAULT_PERMISSION_CLASSES`; confirmed against the installed
`rest_framework.settings.DEFAULTS` that DRF's own shipped default for that key
is `AllowAny`. A view that forgets `permission_classes` is not a 500, it is
silently public. Reducer runs the same `APIView` in two subprocesses (Django
settings can only be configured once per process, and
`APIView.permission_classes` binds to `api_settings.DEFAULT_PERMISSION_CLASSES`
at `rest_framework.views` import time) -- one with the setting unset (200 to
zero credentials), one with `DEFAULT_PERMISSION_CLASSES` set to
`IsAuthenticated` (403 to the same request).
Failure card: `drf-default-permission-unset` (draft -- source-backed and now
fixture-tested via a real installed Django/DRF reducer; not yet observed
against a second independent real project or forward-tested).
Rule/reference changed: card added; no existing card or reference edited.
Checker/test added: `python -m pytest tests/cards/test_drf_permission_fail_open.py -q`
-- 2 passed (unset -> 200, fixed -> 403); full suite
`python -m pytest tests/cards/ -q` -> 4 passed, 1 skipped (skip is the
pre-existing PostgreSQL card with no reachable DB in this environment,
unrelated to this change).
Status: draft (card-level; fixture-tested reducer proves the mechanism, no
forward test or second real-project sighting yet)

## 2026-07-10 - coverage-and-cards-fix-pass-after-hostile-review

Context: `backend-craft/coverage-and-cards` branch. An adversarial Codex review
of an earlier version of this branch found the new material was overclaimed:
the two new Semgrep SQL rules matched ANY `text(...)`/`Sprintf(...)`, two cards
were promoted to `observed` without a defensible in-folder occurrence, and doc
counts drifted. This pass narrows the rules to something precise, keeps every
new card and rule at `draft`, and adds runnable proof for each card.
Artifact: `rules/semgrep/backend-craft.yml` (3 new rules, all `draft`),
`rules/semgrep/tests/` (probe corpus + `check_probes.py`), `tests/cards/`
(gather + PostgreSQL reducers and tests), `FAILURE_CARDS.md` (2 new cards),
`README.md`, `README.en.md`, `docs/STATUS.md`, `scripts/validate_repo.py`,
`hooks/README.md`.
Expected: rules fire on the real SQL-building shape and stay silent on the safe
shape (proven by a persistent probe matrix, not a claim); each new card carries
a reducer that actually reproduces the failure; no status inflated on evidence
that cannot be checked from inside this folder.
Why the agent likely failed (the two new cards' failure modes):
- `python-gather-partial-failure-leak`: an agent reads `asyncio.gather` as an
  atomic batch — assumes a raise cancels the siblings and leaves no partial
  writes. Neither holds; even `TaskGroup` (which does cancel) cannot roll back a
  side effect committed before the cancel point.
- `pg-non-atomic-poll-queue-claim`: an agent claims a job with `SELECT ...
  pending` then a separate `UPDATE ... running` with no lock/guard; two workers
  read the same row and both process it. The defect is the non-atomic claim, not
  "missing SKIP LOCKED" specifically.
Failure card: `python-gather-partial-failure-leak` (new, draft),
`pg-non-atomic-poll-queue-claim` (new, draft); the 3 new rules map to the
existing `sql-string-concat` card (unchanged).
Rule/reference changed: the 3 new rules are scoped so they only match the real
sink — the Python rules rely on Semgrep import resolution to match
`sqlalchemy.text(...)` (a local `text()`/`ui.text()` is not matched); the Go
rule matches `fmt.Sprintf` passed INLINE to a pgx `Query/QueryRow/Exec(ctx,...)`
only (a pre-built string is a documented FN, not a false "clean"). No existing
rule or card logic was changed.
Checker/test added: `rules/semgrep/tests/check_probes.py` (deterministic TP/CLEAN
matrix over `sql_text_sqlalchemy.py`, `sql_text_not_sqlalchemy.py`, `go_pgx.go`;
`python3 rules/semgrep/tests/check_probes.py` → PASS); `tests/cards/
gather_partial_failure.py` + `test_gather_partial_failure.py`; `tests/cards/
pg_non_atomic_claim.py` + `test_pg_non_atomic_claim.py` (PostgreSQL; 4 tests).
Decisions on the two earlier promotions (both reverted to card status on main):
- `secret-in-config-or-log`: NOT promoted. Establishing "observed" needs proof
  the file was tracked and not a fixture/example/deterministic-fake key, and the
  only candidate is a private key I was instructed not to read/verify. Insufficient
  in-folder evidence → stays `draft`.
- `python-swallowed-exception`: NOT promoted. The real occurrence is already the
  henry real-backend record below (the checker rule `python.swallowed-exception-pass`
  is production-tested there); adding a new "first occurrence" entry would
  contradict it. Card stays `draft`; no new claim invented.
Status: draft. No card or rule was promoted in this pass.

## 2026-07-10 - codex-re-review-round-2

Context: external Codex re-review of commits f2e346e/afa85c5 plus fresh
artifacts. Five findings, all verified and fixed.
Artifact: `forward-test-results/0*.md`, `hooks/backend-craft-check.py`,
`../hooks/test-hook.sh`, status docs, `../FAILURE_CARDS.md`.
Expected: previous remediation complete; hook contract airtight.
Why the agent likely failed (per finding):
1. P1 confirmed — round-1 result files 001-014 still had empty Prompt blocks
   (previous fix only covered 1xx). Filled from the round-1 script.
2. P1 confirmed — hook crashed (exit 1) when no writable temp dir exists:
   `state_paths()` was unguarded. Fixed: probe-write with fallback to
   stateless mode (dedup degrades, findings still emitted), plus a global
   catch-all exit-0 backstop; `test-hook.sh` now fails fast when `mktemp`
   itself is broken. Verified: hostile `TMPDIR` -> rc=0 with findings.
3. P2 confirmed — docs said "pack fixture-tested" while the two later-added
   Go server-timeout rules are `draft`. Scope note added to CHECKERS/README/
   HANDOFF instead of overclaiming.
4. P2 confirmed — `go-goroutine-without-lifecycle` safe pattern named errgroup
   without panic capture. Card now requires in-goroutine defer/recover and
   cites the x/sync no-panic-propagation design (verified v0.22.0 source).
5. P3 confirmed — no-local-checker warning claimed "Only the Semgrep
   gap-filler ran" even when Semgrep was unavailable. `check_semgrep` now
   reports whether it actually ran; the warning states "NOTHING checked this
   edit" when true.
Status: observed

## 2026-07-10 - real-backend-validation-henry

Context: pack + hook run read-only against the henry monorepo (NestJS admin
API, Go Temporal workers, Python workers). Full record in `CHECKERS.md`
"Real-backend validation record".
Outcome: 49 findings, 0 parse errors, 0 wrong-match FPs; sample-verified TPs
(sync fs in a @Put handler; documented-but-unmetered swallowed exception).
`node.sync-fs-in-code` and `python.swallowed-exception-pass` promoted to
production-tested. FN-probes confirmed silent rules are true negatives.
Hook: found and fixed the monorepo eslint/lockfile-at-workspace-root detection
bug; latency ~1.3-1.8s (Semgrep), ~8s cold go vet.
Status: observed

## 2026-07-10 - forward-test-round-3

Context: targeted regression round for the round-2 miss (test-writing without
`testing-verification.md`). Two 114-style tasks on fresh leak-stripped copies:
301 "write tests for search + user update", 302 exact rerun of the NestJS
rewrite question. Results in `forward-test-results/30x-*.md`.
Artifact: `.claude/skills/backend-craft/SKILL.md`.
Expected: the round-2 fixes (testing routing signals + proof-contract gate)
fire; no recurrence.
Outcome: both 4/4, both regression_closed. 302 clean sweep — zero misses:
testing-verification.md loaded for the 5 new regression tests AND
persistence-migrations.md fired via the new "fixing SQL injection" signal.
301 passed all FOCUS items (differential pre-fix test run proving the tests
catch the planted bugs; judge reproduced 27/27 + clean typecheck) but exposed
the same gap-class on a different path: persistence-migrations.md not loaded
when the SQL fix emerged mid-task, i.e. after the initial Impact Read chose
references.
Failure card: none new.
Rule/reference changed: SKILL.md — proof contract gains a SQL hard gate
(mirror of the testing gate), and the routing section now requires a
pre-report re-scan of the actual diff against the table (closes the
class: rows that start matching mid-task).
Checker/test added: none (semantic).
Status: observed. Hard gates demonstrably work where routing-table matching
alone does not (302 proved the round-2 gates; 301's miss was on the one row
without a gate at the time).

## 2026-07-10 - errgroup-panic-claim-corrected

Context: round-2 judge (test 109) asserted errgroup >= v0.9.0 re-panics on the
waiting goroutine; the claim entered `language-adapters.md`. External review
(Codex) flagged it for verification.
Artifact: `references/language-adapters.md` Goroutines section.
Expected: library claims verified against source before entering references.
Why it was wrong: x/sync v0.22.0 `errgroup.go` contains an explicit design
comment REJECTING panic propagation (delays panics, hides stacks from crash
tooling, deadlock risk; issues #53757, #74275, #74304, #74306). Verified in
the module source, not from memory.
Rule/reference changed: section rewritten — errgroup does NOT propagate
panics; goroutines that may panic need their own defer/recover.
Lesson recorded: judge-suggested edits that assert library behavior go through
the same official-docs/source gate as any dependency guidance.
Status: observed

## 2026-07-10 - forward-test-round-2

Context: 14 tests rerun on disposable fixture copies (grading markers and
READMEs stripped from copies — also closes a round-1 validity hole where
tested agents could see `PLANTED:` comments). Judges verified explicit
ROUND-2 FOCUS items for every round-1 miss. Originals verified untouched via
`git status`. Results in `forward-test-results/1xx-*.md`.
Artifact: `.claude/skills/backend-craft/`.
Expected: both round-1 3-scores close; no regressions.
Outcome: mean 3.93/4 (round 1: 3.86). 104 payment-idempotency 3->4 (agent
loaded persistence-migrations.md via the new payment/money routing signals,
discussed transaction boundary + outbox). 108 node-csv-export 3->4 (agent
loaded reliability-async.md via the new export signals, streamed with query-
level cap and concrete verifier). 13/14 round-1 misses closed.
Why the agent likely failed (the one regression): 114 rewrite-discipline 4->3
— wrote a 6-test regression file without loading testing-verification.md; the
Retrofit-mode sentence was not self-enforcing, and an SQL-injection fix loaded
only the security reference, not persistence-migrations.md.
Failure card: none new.
Rule/reference changed: SKILL.md testing row signals += "adding or writing any
new test file, regression tests for a fix"; SQL row += "fixing SQL injection /
parameterizing queries"; proof contract now requires testing-verification.md
in files-read when tests change; Continue mode mirrors the Retrofit testing
rule. From judge suggestions: api-contracts.md idempotency in-progress-key
lease/expiry rule + crash-retry verifier, export row cap enforced in the query
itself, language-adapters.md goroutine panic-recovery rule with sanctioned
stdlib fallback.
Checker/test added: none new (semantic).
Status: observed; `db-transaction-around-network-call` (104) and
`event-loop-blocking` (108) promoted to production-tested.

## 2026-07-10 - forward-test-round-1

Context: 14 blind forward tests (`FORWARD_TESTS.md`) run by fresh subagents
against the skill, scored by separate judges. Mean 3.86/4; twelve 4s, two 3s;
zero generic-advice answers. Full transcripts in `forward-test-results/`.
Artifact: `.claude/skills/backend-craft/` (SKILL.md + references).
Expected: every expected behavior in `FORWARD_TESTS.md` hit.
Why the agent likely failed (the misses):
- 004: task said "payment", never "transaction" — persistence-migrations.md
  never loaded, so transaction-around-network-call and outbox went unmentioned.
- 008: no routing signal for "export/bulk/streaming" — reliability-async.md not
  loaded; agent kept whole-CSV-in-memory with a "dataset is small" comment.
- 002: verify commands written as npm in a pnpm repo despite correct inventory.
- 009/010/014: single-row routing — second matching reference not loaded.
- 012: "log redaction test" satisfied by design comment, not a test.
Failure card: `db-transaction-around-network-call`, `event-loop-blocking`,
`api-idempotency-missing-on-mutation-retry` (safe pattern extended).
Rule/reference changed: SKILL.md routing table signals + load-all-matched-rows
rule + retrofit server-baseline/lockfile deliverables + proof-contract
re-verify clause; cross-links and prescriptive verifiers in
reliability-async.md, persistence-migrations.md, observability-ops.md,
api-contracts.md (exports-are-bounded-work), codebase-fit.md (lockfile rule).
Checker/test added: none new (misses are semantic, not mechanical).
Status: observed; 13 cards with direct forward-test proof promoted to
production-tested (test ids recorded in each card's Status line).

## 2026-07-10 - forward-test-isolation-incident

Context: same run. Implementation-shaped tasks ("add an endpoint...") made
tested agents edit the shared fixtures in place, mid-run: the BOLA plant was
"fixed", 20 new files appeared, sibling tests read mutated state.
Artifact: `fixtures/*`.
Expected: fixtures immutable during forward tests.
Why the agent likely failed: harness (this repo's process), not the tested
agents — prompts lacked a read-only/copy constraint and the repo has no VCS
snapshot.
Failure card: none (process failure).
Rule/reference changed: `FORWARD_TESTS.md` now has isolation rules: disposable
copy or design-only phrasing, do-not-read grading materials, restore +
re-verify after every run.
Checker/test added: post-restore acceptance = 3 fixture test suites green +
Semgrep hit set identical to the recorded baseline (9 hits; see CHECKERS.md).
Fixtures were restored from builder-transcript reconstruction and re-verified.
Status: observed

## 2026-07-10 - semgrep-floating-promise-rule-retired

Context: checker verification against a hand-built probe corpus (TP/CLEAN
labelled lines) before fixture testing.
Artifact: `rules/semgrep/backend-craft.yml` (old `ts.floating-promise-expression`).
Expected: flag only bare promise-valued call statements.
Why the rule failed: Semgrep matches subexpressions, so every awaited call
whose method name matched the prefix regex fired; measured precision ~1/8.
Statement anchoring (`$X;`, `$EXPR;` + metavariable-pattern) does not constrain
matching in the JS grammar. Name-prefix heuristics also missed real floating
calls (`auditLog.record`).
Failure card: `ts-floating-promise` (card kept; Semgrep verifier removed).
Rule/reference changed: rule deleted from the pack; `CHECKERS.md` documents the
delegation to type-aware `@typescript-eslint/no-floating-promises`.
Checker/test added: probe corpus kept the regression visible.
Status: retired (Semgrep rule only, not the card)

## 2026-07-10 - checker-pack-fixture-verification

Context: rule pack tested against probe corpus plus the three fixtures in
`fixtures/` (15 planted flaws total, 13 mechanically detectable by design).
Artifact: `rules/semgrep/backend-craft.yml`.
Expected: catch all mechanically detectable plants, zero false positives on
clean contrast code.
Why the agent likely failed: initial rules had arity/shape gaps — Python
`execute(f"...", params)` (two args) and adjacent f-string concatenation were
missed; constant f-strings were false positives; Go SQL-via-Sprintf had no rule
at all; Go goroutine/context rules fired on legitimate `main()` setup code.
Failure card: `sql-string-concat`, `go-goroutine-without-lifecycle`,
`timeout-without-cancellation-propagation`, `python-swallowed-exception`,
`api-mass-assignment`, `event-loop-blocking`.
Rule/reference changed: rules narrowed/added as recorded in `CHECKERS.md`
"Verification record (2026-07-10)"; all shipped rules now
`status: fixture-tested`.
Checker/test added: fixtures serve as the permanent regression corpus; rerun
command documented in `CHECKERS.md`.
Status: observed (checker-level evidence; cards unchanged pending forward tests)

## 2026-07-10 - go-server-timeout-rules-promoted-to-fixture-tested

Context: the two Go server-timeout rules (`go.listen-and-serve-no-timeouts`,
`go.server-missing-read-timeouts`) were probe-validated `draft` with no
fixture plant; closing the last non-fixture-tested gap in the shipped pack.
Artifact: `fixtures/go-http/ops.go` (new), `fixtures/go-http/main.go`,
`rules/semgrep/backend-craft.yml`, `CHECKERS.md`, fixture READMEs,
regenerated `fixtures/pristine-baseline-20260710.tar.gz`.
Expected: both rules catch a realistic plant and stay silent on the fixture's
correctly configured server.
Why the agent likely failed (the card's failure mode): ops/debug listeners are
the classic spot — a bare `&http.Server{Addr, Handler}` ops endpoint and the
canonical-looking `http.ListenAndServe(":6060", nil)` debug listener, both on
all interfaces (the docs' own example uses `localhost:6060`; dropping the host
silently widens exposure with zero timeouts).
Failure card: `go-http-server-no-timeouts` (card itself stays `draft` on the
card ladder — planted, not yet observed in a real project or forward test).
Rule/reference changed: both rules `draft` -> `fixture-tested`; promotion
record in `CHECKERS.md`; go-http plant count 5 -> 6 (16 total across
fixtures); expected Semgrep baseline 9 -> 11 hits.
Checker/test added: fixture plants are the permanent regression; probe corpus
rerun 4/4 TP, 0 FP on clean variants (ReadHeaderTimeout-only,
ReadTimeout-only, method-call ListenAndServe, httptest); `go vet` + happy-path
tests green; the new `go startOps()`/`go startDebug()` in `main()` double as
a no-fire scoping regression for `go.naked-goroutine-in-handler`.
Status: observed (checker-level evidence)

## 2026-07-10 - auth-middleware-scope-miss-card-added

Context: handoff item "framework-specific auth docs for the fixture stacks";
admission bar = concrete card/verifier only, no generic advice.
Artifact: `../FAILURE_CARDS.md` (new card), `SOURCES.md` (3 rows),
`references/auth-tenancy-security.md` (non-negotiable + verifier line).
Expected: auth guards cover every non-public route.
Why the agent likely fails: registers the auth guard on a sub-scope assuming
it is global — Fastify hooks are encapsulated per plugin context (siblings
unaffected), FastAPI router-level dependencies "only affect that APIRouter",
a wrapped Go sub-mux covers only what it wraps; a route module added outside
the guarded scope ships unauthenticated and nothing errors.
Failure card: `auth-middleware-scope-miss` (draft — source-backed, not yet
observed in a project or forward test).
Rule/reference changed: card added; auth reference gained "Auth guards attach
at the shared ancestor scope" and the route-table sweep verifier.
Checker/test added: none mechanical (scope topology is semantic); verifier is
the unauthenticated route-table sweep (all non-allowlisted routes 401/403).
Sources verified against fastify.dev and fastapi.tiangolo.com on 2026-07-10.
Status: draft (card-level; no fixture plant — fixtures use fake header auth
by design, zero-dep philosophy)

## 2026-07-20 - validation-guard-admits-its-own-blocked-case

Context: a deploy script gained a guard to stop `rm -rf .venv` from running on an
ML-incompatible Python. v1 was `^3[.]1[0-9]$` (intended: 3.10-3.12).
Artifact: `inference/deploy.sh` venv-recreate guard.
Expected: reject the node-default 3.14 so a forgotten `PYTHON=` override cannot destroy a good 3.12 venv.
Why the agent likely failed: `1[0-9]` reads as "3.1x" at a glance; the author verified a good value passes, not that the dangerous value is rejected.
Failure card: infra-guard-regex-admits-blocked-case.
Rule/reference changed: new card; reinforces self-hosted-inference.md (venv recreate) verifier discipline.
Checker/test added: version-gate truth table (3.9/3.12/3.13/3.14/3.20) asserting 3.14 -> block.
Status: observed
