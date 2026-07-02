"""
UNIT 13 : Sequential vs Concurrent Agent Execution with Real LLM Calls
PRIOR UNIT STATE: The script used a manager agent that delegated to sub-agents,
but all operations ran one after another (sequentially). There was no ability to
run multiple independent tasks at the same time.

WHAT'S NEW IN THIS UNIT:
1. Sequential Execution - Running tasks one after another when the output of task A
   is needed for task B (dependent tasks)
2. Concurrent Execution - Running multiple tasks at the same time using asyncio.gather()
   when tasks are independent and don't need each other's results
3. Dependency Detection - Analyzing whether task outputs flow into other tasks
4. Timeout Handling - Setting maximum wait time for concurrent tasks
5. Partial Failure Handling - Continuing with successful tasks even if some fail
"""

import os
import yaml
import asyncio

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from classes.llm_calls import LLMAgent
from classes.sequential import SequentialAgent
from classes.concurrent import ConcurrentAgent

# =============================================================================
# CONFIGURATION
# =============================================================================

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
LLM_MODEL_DEPLOYMENT_NAME = os.getenv("LLM_MODEL_DEPLOYMENT_NAME")
USER_NAME = os.getenv("USER_NAME")

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

# =============================================================================
# AUTHENTICATION
# =============================================================================

credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
openai_client = OpenAI(base_url=AZURE_OPENAI_ENDPOINT, api_key=token_provider)

# =============================================================================
# INSTANTIATE CLASSES
# =============================================================================

# Instantiate LLM agent (used by sub-agents for LLM tasks)
llm_agent = LLMAgent(
    openai_client=openai_client,
    llm_deployment_name=LLM_MODEL_DEPLOYMENT_NAME,
    config=config,
)

# Instantiate execution pattern agents
sequential_agent = SequentialAgent()
concurrent_agent = ConcurrentAgent(config=config)

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

# ===== EXAMPLE 1: INDEPENDENT TASKS (Best for CONCURRENT) =====
# We use asyncio to run multiple independent LLM tasks at the same time for efficiency.
# What is asyncio? It's a Python library for writing concurrent code using the async/await syntax.
# It allows us to run multiple llm calls simultaneously without blocking the main thread

tasks = [
    {
        "func": llm_agent.get_weather,
        "args": ["London"],
        "description": "Weather for London",
    },
    {
        "func": llm_agent.get_exchange_rate,
        "args": ["USD", "EUR"],
        "description": "Exchange rate USD to EUR",
    },
]
concurrent_results, concurrent_time = asyncio.run(concurrent_agent.run(tasks))

# ===== EXAMPLE 2: DEPENDENT TASKS (Best for SEQUENTIAL) =====
# We use asyncio to run tasks one after another, passing results from one to the next.
# This is necessary when task B needs the output of task A to run

# why do we have kwargs?
# kwargs allows us to specify special instructions for how to pass results between tasks
# 'use_previous_result' tells the agent to take the result of the previous task and
#  pass it as an argument to the current task
# 'use_original_arg' allows us to pass the original input (e.g., user text) to all tasks,
#  even if they are not the first task
# This way we can have a chain of tasks where each one can use the original input
#  and the results of previous tasks as needed

tasks = [
    {
        "func": llm_agent.analyze_sentiment,
        "args": ["I love this product!"],
        "description": "Sentiment analysis of user feedback",
    },
    {
        "func": llm_agent.generate_response_to_sentiment,
        "args": [],
        "kwargs": {
            "use_previous_result": "sentiment_analysis",
            "use_original_arg": "user_text",
        },
        "description": "Generate response based on sentiment",
    },
]
sequential_results, sequential_time = asyncio.run(sequential_agent.run(tasks))

# =============================================================================
# UNIT 13 SUMMARY
# =============================================================================
# This script demonstrates concurrent and sequential execution patterns for multi-agent LLM tasks:
# 1. CONCURRENT AGENT: Runs independent LLM tasks in parallel for efficiency
# 2. SEQUENTIAL AGENT: Runs dependent LLM tasks in sequence, passing results between them
# 3. TASK STRUCTURING: Shows how to define LLM tasks as callables with arguments for flexible execution
# 4. REUSABLE PATTERNS: Provides agent classes for both execution patterns, supporting scalable multi-agent workflows
