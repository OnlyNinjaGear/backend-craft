# Self-hosted inference and fleet operations

Read this when wiring a backend to self-hosted inference services (embedding,
VLM, OCR, ASR, moderation) on local or heterogeneous hardware: Apple Silicon
nodes, older NVIDIA cards, mixed OS, nodes reached over an overlay network.

Every rule here maps to a failure card with a verifier. Nothing below is
theory; each one cost real time on a real fleet before it became a rule.

## Inference read

In addition to the standard Impact Read, identify:

- GPU arch, driver, and OS of every target node — never assume CUDA works
- reachability in both directions: app host -> node AND node -> app host
- where model weights come from and whether the node can fetch them
  non-interactively and anonymously
- which services share one node's CPU/GPU and what happens under ingest
  concurrency
- what restarts the service after a redeploy and after a reboot

## Non-negotiables

### Inventory hardware before choosing the serving stack

Run `nvidia-smi` (arch + driver) or `system_profiler` before picking a
torch/serving/quantization stack. Default PyPI torch wheels target sm_75+ and
a recent CUDA runtime; on an older card (Pascal = sm_60) with an older driver,
`torch.cuda.is_available()` is False and the "GPU node" silently runs on CPU.
AWQ/int4 kernels also need sm_75+. A GPU node that can only run CPU is a CPU
node — plan capacity that way, and put the CPU fallback in the service config,
not in a comment.

Pre-deploy probe on the target node:

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_arch_list())"
```

On Apple Silicon use Metal-native stacks (MLX, llama.cpp), not CUDA-only
servers.

### Model downloads must not depend on ambient credentials

A stale `~/.cache/huggingface/token` left by another project is sent
implicitly and 401s PUBLIC repos, while `curl` on the same file URL gets 200.
Set `HF_HUB_DISABLE_IMPLICIT_TOKEN=1` in the service environment and pass
`token=False` to explicit `snapshot_download` calls. Do not delete the token
file — it is another project's credential. First pulls are multi-GB: run them
detached with a log file, never inline in an interactive SSH session.

### Build venvs with an explicit interpreter path

The node's default `python3` may be too new for ML wheels (no cpXX wheels yet,
pip fails). On macOS, non-login SSH sessions do not have `/opt/homebrew/bin`
on PATH, so `which` lies about what is installed. Create venvs with an
absolute, versioned interpreter path and make it a deploy-script parameter.

```bash
ssh node '<abs-python> -c "import sys; print(sys.version)"'
```

### Prove reachability before choosing media transport

Overlay networks are often one-directional: app host -> node works because
you configured it; node -> app host does not, because nothing configured the
reverse route or identity. A service that accepts media only as `http(s)` URL
or local path cannot see app-hosted files, and it fails on the first real
request, not at deploy. Make every inference service accept `data:` URIs
(base64) in the same input field as URLs, and have the client inline media.
Probe the reverse direction (`curl` from node to app host) before relying on
URL transport.

### Encode once; cache constant embeddings

The encoder forward pass is the cost. Encode each input once per request and
reuse the features across every prompt ladder/scorer; cache embeddings of
constant prompt/label sets at process scope (`functools.lru_cache` or
init-time precompute). Re-running the encoder per prompt set is a measured
5-10x latency waste on CPU (11.4 s -> 1.3-1.8 s on a live moderation
service). Gate expensive stages: run the cheap path on everything and the
heavy zero-shot pass only on the ambiguous middle.

### Do not co-locate CPU-bound services; cap concurrency server-side

Two CPU-heavy services on one node contend under ingest: responses cross the
client timeout, the queue retries, retries add load (measured collapse:
2/1500 items in 100 minutes). Spread CPU-bound services across nodes. Every
service gets its own max-concurrency semaphore so it protects itself
regardless of client behavior. Size worker concurrency from the slowest
shared resource, not the fastest. Count and log the skip rate of every
best-effort stage — a silently skipped stage is data loss without an error.

### A deploy is not done until the process restarts

`systemctl --user enable --now` does not restart an already-running unit, and
launchd `RunAtLoad` does not either: the sync succeeds and the stale process
keeps serving. After syncing code/env run `systemctl --user restart` (or
`try-restart`) or `launchctl kickstart -k gui/$UID/<label>`, then hit a health
endpoint that reports a version marker. If launchd `bootstrap` fails with
"Input/output error 5", the label is mid-transition — do not rewrite the
plist; run: `bootout` (ignore "No such process") -> `sleep 3` -> `bootstrap`
-> `enable` -> `kickstart -k`. Manage only your own labels.

### Serialize access to non-thread-safe runtimes

MLX/Metal streams are thread-local; FastAPI runs sync endpoints in a
threadpool, so concurrency 2 crashes generation ("There is no Stream(gpu, N)
in current thread"). Wrap generate in a `threading.Lock` — one GPU generates
one sequence at a time anyway, the lock only makes the queueing explicit.
Smoke-test every inference service at concurrency >= 2 before calling it
deployed.

## Cross-links

- the Go/TS client and the Python service drift on the wire shape (a decision
  enum the service never emits, wrapped vs bare embedding arrays) ->
  `api-contracts.md`; verify with a live client-to-service call, not only
  mocked tests
- queue retries, client timeouts, worker concurrency -> `reliability-async.md`
- coverage metrics for best-effort stages -> `observability-ops.md`

## Common failure cards

- `inference-gpu-arch-wheel-mismatch`
- `inference-hf-implicit-token-401`
- `infra-node-python-too-new-for-wheels`
- `infra-one-way-overlay-inline-media`
- `inference-encoder-in-prompt-loop`
- `infra-colocated-cpu-services-retry-storm`
- `infra-enable-now-not-a-restart`
- `infra-launchd-bootstrap-io-error`
- `inference-mlx-not-thread-safe`

## Verifiers

- pre-deploy node probe: `torch.cuda.is_available()` + arch list; absolute
  interpreter version; pip dry-run of the requirement set
- implicit-token check: `curl -sI` on a hub file URL returns 200 while the
  hub client 401s => stale ambient token; after the env fix the download
  completes anonymously
- post-deploy: health endpoint returns the new version marker
- parallel smoke test at concurrency >= 2: all responses 200
- live call with a `data:` URI payload from the app host returns 200
- load run of N items: throughput does not degrade as worker concurrency
  rises; per-stage coverage metric is ~100% or the gap is explained
- latency measured before/after any encoder-path change
