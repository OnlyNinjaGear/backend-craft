"""Reducer for python-gather-partial-failure-leak (dependency-free).

Proves two distinct facts, without relying on a timing race:

1. asyncio.gather does NOT cancel a sibling when one awaitable raises: the sibling
   keeps running and commits its side effect AFTER gather already propagated the
   error. Ordering is controlled by an Event, not by sleeps.

2. asyncio.TaskGroup DOES cancel the remaining tasks, but it cannot roll back a
   side effect the sibling already committed BEFORE the cancellation was delivered.
   The sibling commits its side effect before the failing task even exists, so this
   is not a delayed-side-effect artifact.

Run: python3 tests/cards/gather_partial_failure.py
"""
import asyncio


async def _fail_fast():
    raise RuntimeError("primary op failed")


# ---- Fact 1: gather leaves the sibling running -> side effect commits after the error
async def gather_leaves_sibling_running() -> dict:
    state: dict = {}
    released = asyncio.Event()

    async def sibling():
        await released.wait()          # cannot commit until we release it
        state["side_effect"] = "committed"

    fut = asyncio.gather(_fail_fast(), sibling())
    try:
        await fut
    except RuntimeError:
        pass
    # gather has already raised. If it had cancelled the sibling, releasing the
    # event would do nothing. We release it and yield control:
    released.set()
    await asyncio.sleep(0.05)
    return state                        # side_effect == 'committed' proves no cancel


# ---- Fact 2: TaskGroup cancels the sibling but does NOT undo an already-committed effect
async def taskgroup_cancels_but_cannot_rollback() -> dict:
    state: dict = {}

    async def sibling():
        state["side_effect"] = "committed"   # commits BEFORE any cancellation point
        try:
            await asyncio.sleep(3600)        # will be cancelled by the group
        except asyncio.CancelledError:
            state["sibling_cancelled"] = True
            raise

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(sibling())
            await asyncio.sleep(0)           # let the sibling commit its side effect
            tg.create_task(_fail_fast())     # now a task fails -> group cancels sibling
    except* RuntimeError:
        pass
    return state


async def main():
    g = await gather_leaves_sibling_running()
    t = await taskgroup_cancels_but_cannot_rollback()
    print("gather:   sibling side effect =", g.get("side_effect"),
          " (committed AFTER gather raised -> not cancelled)")
    print("taskgroup: sibling side effect =", t.get("side_effect"),
          " cancelled =", t.get("sibling_cancelled"),
          " (cancelled, but the committed side effect was NOT rolled back)")


if __name__ == "__main__":
    asyncio.run(main())
