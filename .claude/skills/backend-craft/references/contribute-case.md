# Contributing an anonymized case (opt-in)

How backend-craft grows from real projects that use it. This is OFF by default.
The skill never sends anything on its own. A contribution happens only when the
user asks or explicitly confirms an offer, under the user's OWN GitHub account,
after seeing the exact text that will be posted.

## When to offer

After work that surfaces a *generalizable, repeatable* backend failure mode —
useful to other projects, not a bug specific to this codebase — you may offer
ONCE:

  "This looks like a reusable failure pattern. Want me to prepare an anonymized
   case to contribute to backend-craft? You review and confirm before anything
   is sent."

If the user declines or ignores it, drop it. Never nag, never send.

Three high-value sources qualify:
1. A review/audit finding on real backend code.
2. An agent MISS: the agent wrote plausible code that a test, human, or reviewer
   later proved wrong.
3. A reviewer-vs-agent correction (e.g. Codex catching Claude). See the dedicated
   section below — these are the strongest signal, and the easiest to leak the
   wrong thing, so treat them carefully.

Do NOT offer for: a bug specific to this repo with no general lesson; process or
tooling nitpicks (doc counts, file layout, commit hygiene); anything you cannot
fully anonymize; work the user marked private/NDA.

## Hard rules (non-negotiable)

- Opt-in only. No submission without an explicit "yes" in this session.
- The user's own GitHub identity submits it. There is no shared token and no
  background channel; you cannot and must not send data silently.
- Anonymize first, then SHOW the user the exact final payload, then ask to
  confirm. Only after a clear yes do you open the issue.
- One case per submission, distilled to a pattern, not a data dump.
- If you cannot fully anonymize it, do not submit — offer to save it locally.

## Step 1 — Distill to a pattern

- Summary (one or two lines)
- Stack (generic, e.g. "FastAPI + Postgres" — no product name)
- Failure mode (the repeatable mistake)
- Evidence (a MINIMAL anonymized reducer you write from scratch, or a link to a
  public issue/PR/postmortem — never the user's real source)
- Verifier idea (how to prove it)
- Best target artifact (card / fixture / checker / not sure)

## Step 2 — Scrub checklist (run before showing)

Remove or generalize ALL of: company/product/service/team names; real
hostnames, domains, URLs, IPs, ports; credentials, tokens, API keys, secrets,
connection strings (even "example" ones that look real); personal or customer
data, order ids, emails, phone numbers; internal identifiers, ticket numbers,
repo names, exact file paths (say "the payments module", not
`app/billing/charge.py`). Keep only the abstract pattern and a synthetic
reducer. If anything private survives, stop and fix it.

## Step 3 — Show and confirm

Print the full case exactly as it will be posted, then ask:

  "Post this anonymized case to github.com/OnlyNinjaGear/backend-craft as a
   PUBLIC issue under YOUR GitHub account? (yes / no)"

Remind the user in the same message that the repo is public and that by
confirming they take responsibility that it contains nothing under NDA or
private. On "no" -> stop; offer to save it to a local file instead.

## Step 4 — Submit (only after "yes")

This repo has `blank_issues_enabled: false` — a plain title/body URL does
NOT work here. Submission must go through the "Real backend case" issue
form (`real-backend-case.yml`), which applies `case` + `needs-triage`
automatically.

A. One-click prefilled FORM (no tooling needed). Build a URL against the
   template with the form's own field ids, URL-encoding each value, and give
   it to the user to open, review once more in GitHub, and press Submit:

   https://github.com/OnlyNinjaGear/backend-craft/issues/new?template=real-backend-case.yml&title=<[case] short summary>&summary=<Summary>&stack=<Stack>&failure_mode=<Failure mode>&evidence=<Evidence>&verifier=<Verifier idea>

   The user still picks "Best target artifact" in the dropdown and ticks the
   2 privacy checkboxes themselves — those aren't prefillable. If the URL
   would exceed roughly 8000 characters, open the blank form instead
   (`.../issues/new?template=real-backend-case.yml`) and hand the user the
   text to paste into each field.

B. GitHub CLI, only if `gh auth status` shows the user is authenticated:

   gh issue create --repo OnlyNinjaGear/backend-craft \
     --title "[case] <short summary>" \
     --label case --label needs-triage \
     --body-file <the-case-file>

Never use a token that is not the user's own. Never automate past the
confirmation. After submission, give the user the issue URL.

### No GitHub account

If the contributor has no GitHub account, submission (Step 4) is blocked —
there is no anonymous or shared-identity path, by design (see Hard rules).
Offer, in order:

1. Suggest creating a free GitHub account (~2 minutes, no payment, an email
   is enough) and then continuing with method A above.
2. If they decline, do NOT submit on their behalf under any other identity.
   Save the finished, scrubbed case to a local file instead, and tell them
   it can be posted later by them or handed to someone who already has an
   account.

This is a deliberate gap, not a missing feature: no background service or
shared token exists to route around it.

## Turning a reviewer's corrections into cases (the "review-miss" handle)

When a reviewer — Codex, a senior engineer, a failing test, a postmortem —
corrects the agent's own work, each correction that is a *generalizable* backend
mistake is the single most valuable case type: a proven agent miss with a known
fix. Capture them like this:

1. Take the reviewer's findings for one review cycle.
2. Split into two buckets and KEEP ONLY the first:
   - **Transferable failure modes** — "the agent used asyncio.gather and assumed
     it cancels siblings"; "the verifier passed only because of a sleep". These
     become cases.
   - **Process/meta nitpicks** — doc counts, file names, commit messages, repo
     hygiene. These are NOT skill material; drop them.
3. For each transferable one, run Steps 1–3 above (distill, scrub, confirm). The
   "agent miss" framing is a strong prior signal, so state plainly in the case:
   what the agent did, why it looked right, what the reviewer caught, the
   verifier that would have failed the wrong version.
4. Submit via Step 4 after the user confirms. One issue per distinct failure
   mode; do not bundle a whole review into one issue.

Filter hard: a reviewer being pedantic about layout is not a backend failure
mode. Only patterns that would bite another project, provable by a verifier,
qualify.

## What happens next (set expectations)

The case lands in the intake queue (label `needs-triage`). The project's daily
worker triages real-project cases FIRST, before official sources, into a draft
card candidate; the owner reviews and merges. Contribution is not acceptance —
a case may be deduped, backlogged, or rejected. That is normal, and nothing is
auto-merged.
