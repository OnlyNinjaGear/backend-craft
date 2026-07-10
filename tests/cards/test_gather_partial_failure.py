"""Verifier for python-gather-partial-failure-leak (dependency-free; asyncio.run)."""
import asyncio

from gather_partial_failure import (
    gather_leaves_sibling_running,
    taskgroup_cancels_but_cannot_rollback,
)


def test_gather_does_not_cancel_sibling():
    state = asyncio.run(gather_leaves_sibling_running())
    # gather propagated the error yet the sibling still committed -> not cancelled
    assert state.get("side_effect") == "committed"


def test_taskgroup_cancels_but_does_not_rollback():
    state = asyncio.run(taskgroup_cancels_but_cannot_rollback())
    assert state.get("sibling_cancelled") is True       # TaskGroup DID cancel it
    assert state.get("side_effect") == "committed"      # but could NOT undo the effect
