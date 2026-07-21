"""Verifier for infra-gha-pr-permission-toggle-silent-fail (dependency-free)."""
import pytest

from infra_gha_pr_permission_toggle_silent_fail import (
    GitHubAPI,
    run_pipeline_buggy,
    run_pipeline_safe,
)


def test_buggy_pipeline_reports_success_with_no_pr_when_repo_toggle_off():
    api = GitHubAPI(workflow_permissions_write=True, repo_allows_actions_pr=False)
    result = run_pipeline_buggy(api, "case-triage/x")
    assert result == "success"
    assert api.list_prs_for_branch("case-triage/x") == []


def test_buggy_pipeline_creates_pr_when_both_layers_allow():
    api = GitHubAPI(workflow_permissions_write=True, repo_allows_actions_pr=True)
    result = run_pipeline_buggy(api, "case-triage/x")
    assert result == "success"
    assert api.list_prs_for_branch("case-triage/x") == [1]


def test_safe_pipeline_fails_loudly_when_repo_toggle_off():
    api = GitHubAPI(workflow_permissions_write=True, repo_allows_actions_pr=False)
    with pytest.raises(RuntimeError, match="preflight failed"):
        run_pipeline_safe(api, "case-triage/x")
    assert api.list_prs_for_branch("case-triage/x") == []


def test_safe_pipeline_succeeds_when_both_layers_allow():
    api = GitHubAPI(workflow_permissions_write=True, repo_allows_actions_pr=True)
    result = run_pipeline_safe(api, "case-triage/x")
    assert result == "success"
    assert api.list_prs_for_branch("case-triage/x") == [1]


def test_postflight_catches_a_creation_call_that_silently_no_ops():
    # A follow-up defense: even if create_pull_request raises nothing (a race, a
    # client library that swallows the API error), the postflight existence check
    # still catches the missing PR instead of trusting a clean return.
    api = GitHubAPI(workflow_permissions_write=True, repo_allows_actions_pr=True)
    api.create_pull_request = lambda branch: None
    with pytest.raises(RuntimeError, match="postflight failed"):
        run_pipeline_safe(api, "case-triage/x")
