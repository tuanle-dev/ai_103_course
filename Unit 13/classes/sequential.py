# =============================================================================
# SEQUENTIAL AGENT
# =============================================================================
# This class encapsulates sequential execution logic for tasks.

from typing import List, Dict, Any
import time


class SequentialAgent:
    """Agent that runs tasks sequentially (one after another)."""

    def __init__(self):
        pass

    async def run(self, tasks: List[Dict[str, Any]]) -> tuple[List[str], float]:
        """
        Run tasks one after another.
        Total time = sum of all task times.
        Use when tasks have dependencies (task B needs output from task A).
        Supports passing previous result and original argument to dependent tasks via special keys in kwargs:
          - 'use_previous_result': name of argument to receive previous result
          - 'use_original_arg': name of argument to receive the first task's main arg
        """
        print("\n" + "=" * 50)
        print("SEQUENTIAL EXECUTION PATTERN")
        print("=" * 50)
        print("Running tasks one after another (dependent tasks)")
        print("Total time will be the SUM of all task durations\n")

        results = []
        start_time = time.time()

        # Store the first task's main arg (if any)
        original_arg = None
        if tasks and tasks[0].get("args"):
            original_arg = tasks[0]["args"][0]

        # The explaination of the loop is:
        # We loop through each task in the list of tasks.
        # For each task, we print a header indicating which task we're starting.
        # We then check if the task has any special instructions in its kwargs
        #  for using previous results or the original argument.
        # If the task wants to use the previous result and we have one,
        #  we add that to the kwargs for the current task.
        # If the task wants to use the original argument and we have it,
        #  we add that to the kwargs for the current task.
        # Finally, we call the task's function with its arguments and kwargs,
        #  await the result, and append it to our results list.
        for i, task_info in enumerate(tasks, 1):
            print(f"\n--- Starting task {i}/{len(tasks)} ---")
            task_func = task_info["func"]
            task_args = task_info.get("args", [])
            task_kwargs = dict(
                task_info.get("kwargs", {})
            )  # copy to avoid mutating input

            # If the task expects a previous result and we have one
            if "use_previous_result" in task_kwargs and results:
                arg_name = task_kwargs.pop("use_previous_result")
                task_kwargs[arg_name] = results[-1]

            # If the task expects the original arg (e.g., user_text)
            if "use_original_arg" in task_kwargs and original_arg is not None:
                arg_name = task_kwargs.pop("use_original_arg")
                task_kwargs[arg_name] = original_arg

            result = await task_func(*task_args, **task_kwargs)
            results.append(result)

        elapsed = time.time() - start_time
        print(f"\n[SEQUENTIAL] Total time: {elapsed:.2f} seconds")
        return results, elapsed
