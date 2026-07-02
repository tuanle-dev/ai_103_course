# =============================================================================
# CONCURRENT AGENT
# =============================================================================
# This class encapsulates concurrent execution logic for tasks.

from typing import List, Dict, Any
import time
import asyncio


class ConcurrentAgent:
    """Agent that runs tasks concurrently (in parallel)."""

    def __init__(self, config):
        self.timeout_seconds = config["concurrent"]["timeout_seconds"]

    async def run(self, tasks: List[Dict[str, Any]]) -> tuple[List[str], float]:
        """
        Run multiple tasks at the same time.
        Total time = time of the SLOWEST task.
        Use when tasks are independent (no dependencies between them).
        """
        print("\n" + "=" * 50)
        print("CONCURRENT EXECUTION PATTERN")
        print("=" * 50)
        print("Running multiple tasks at the same time (independent tasks)")
        print("Total time will be the time of the SLOWEST task\n")

        start_time = time.time()

        # Build list of coroutines to run concurrently
        # What are coroutines? They are special functions defined with async def
        # that can be paused and resumed, allowing for concurrent execution.
        # Here we create a list of coroutines by calling each task's function with its arguments.

        coroutines = [
            task_info["func"](*task_info.get("args", []), **task_info.get("kwargs", {}))
            for task_info in tasks
        ]

        try:
            # What does asyncio.gather do?
            # It takes in multiple coroutines (async functions) and runs them concurrently.

            # What does asyncio.wait_for do?
            # It wraps an awaitable (like the result of asyncio.gather) and
            #  raises a TimeoutError if it takes longer than the specified timeout.

            results = await asyncio.wait_for(
                asyncio.gather(*coroutines, return_exceptions=True),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            print(
                f"[CONCURRENT] ERROR: Tasks timed out after {self.timeout_seconds} seconds"
            )
            return [], self.timeout_seconds

        elapsed = time.time() - start_time

        # Separate successful results from failures
        successful_results = []
        failed_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"[CONCURRENT] Task {i+1} failed: {result}")
                failed_count += 1
            else:
                successful_results.append(result)

        if failed_count > 0:
            print(
                f"[CONCURRENT] {failed_count} task(s) failed, "
                f"{len(successful_results)} succeeded"
            )

        print(f"\n[CONCURRENT] Total time: {elapsed:.2f} seconds")
        return successful_results, elapsed
