"""Reducer for infra-gha-pr-permission-toggle-silent-fail (dependency-free).

Models the two-layer GitHub Actions PR-creation permission gate with a mock API
client (no network, no gh CLI, no auth) and proves two facts:

1. The job-level `permissions: pull-requests: write` grant is necessary but not
   sufficient: a separate repo/org policy flag independently blocks PR creation,
   and a naive pipeline that only relies on its own declared permissions has no
   way to see that from inside the run.

2. A pipeline that catches the creation error and does not assert the terminal
   side effect (a PR that actually exists) reports "success" with zero PRs
   created. A pipeline with a preflight capability check AND a postflight
   existence assertion fails loudly in the same scenario instead.

Run: python3 tests/cards/infra_gha_pr_permission_toggle_silent_fail.py
"""


class GitHubAPI:
    """Mock of the two independent permission layers GitHub actually enforces."""

    def __init__(self, workflow_permissions_write: bool, repo_allows_actions_pr: bool):
        self.workflow_permissions_write = workflow_permissions_write  # job-level `permissions:` block
        self.repo_allows_actions_pr = repo_allows_actions_pr  # repo/org toggle, off by default
        self.prs: dict[str, int] = {}

    def create_pull_request(self, branch: str) -> int:
        if not self.workflow_permissions_write:
            raise PermissionError("workflow lacks pull-requests: write permission")
        if not self.repo_allows_actions_pr:
            # This is the actual GitHub error text; it fires even when the workflow
            # itself declared pull-requests: write, because the repo/org toggle is
            # a second, independent gate the job cannot see or change.
            raise PermissionError(
                "GitHub Actions is not permitted to create or approve pull requests"
            )
        pr_number = len(self.prs) + 1
        self.prs[branch] = pr_number
        return pr_number

    def list_prs_for_branch(self, branch: str) -> list[int]:
        return [number for b, number in self.prs.items() if b == branch]


def run_pipeline_buggy(api: GitHubAPI, branch: str) -> str:
    """Mirrors the observed incident: the creation error is caught and logged,
    the run still concludes success regardless of whether a PR exists."""
    try:
        api.create_pull_request(branch)
    except PermissionError as exc:
        print(f"warning: pr creation failed: {exc}")
    return "success"


def run_pipeline_safe(api: GitHubAPI, branch: str) -> str:
    """Preflight capability check plus postflight existence assertion."""
    if not api.repo_allows_actions_pr:
        raise RuntimeError(
            "preflight failed: repo/org policy blocks Actions from creating PRs "
            "(can_approve_pull_request_reviews=false) -- fix repo settings before running"
        )
    api.create_pull_request(branch)
    if not api.list_prs_for_branch(branch):
        raise RuntimeError(f"postflight failed: no PR found for branch {branch!r}")
    return "success"


def main():
    branch = "case-triage/example"

    # Scenario from the issue: workflow-level write is granted, but the repo/org
    # toggle is off (the default) -- the OUTER layer blocks creation even though
    # the INNER (job) layer looks sufficient by itself.
    buggy_api = GitHubAPI(workflow_permissions_write=True, repo_allows_actions_pr=False)
    buggy_result = run_pipeline_buggy(buggy_api, branch)
    print(
        f"buggy pipeline result: {buggy_result!r}, "
        f"PRs created: {buggy_api.list_prs_for_branch(branch)}"
    )

    safe_api = GitHubAPI(workflow_permissions_write=True, repo_allows_actions_pr=False)
    try:
        safe_result = run_pipeline_safe(safe_api, branch)
    except RuntimeError as exc:
        safe_result = f"failed loudly: {exc}"
    print(
        f"safe pipeline result: {safe_result!r}, "
        f"PRs created: {safe_api.list_prs_for_branch(branch)}"
    )


if __name__ == "__main__":
    main()
