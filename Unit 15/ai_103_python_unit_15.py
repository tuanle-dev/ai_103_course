"""
UNIT 15: Agent Memory – Short-Term Session Memory (Redis)

WHAT'S NEW IN THIS UNIT:
1. Short-Term Memory - Storing conversation history and session state temporarily
   so the agent remembers what was said earlier in the conversation
2. Redis - An in-memory database that provides fast, ephemeral storage with
   automatic expiration (TTL - Time To Live)
3. Session Context - Tracking conversation state like "awaiting_approval" or
   "pending_tool_call" across multiple user messages
4. TTL (Time To Live) - Automatically deleting session data after a period of
   inactivity (e.g., 1 hour)
5. Sliding Window - Keeping only the last N messages when approaching token limits
"""

import os
import sys
import yaml
from datetime import datetime

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.contentsafety import ContentSafetyClient
import redis

from functions.helper_functions import count_tokens, build_system_instruction
from classes.content_safety import ContentSafety
from classes.redis_memory import RedisMemory
from classes.agent_with_memory import AgentWithMemory

# =============================================================================
# CONFIGURATION
# =============================================================================

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
LLM_MODEL_DEPLOYMENT_NAME = os.getenv("LLM_MODEL_DEPLOYMENT_NAME")
CONTENT_SAFETY_ENDPOINT = os.getenv("CONTENT_SAFETY_ENDPOINT")
USER_NAME = os.getenv("USER_NAME")
USER_ROLE = os.getenv("USER_ROLE")
REDIS_HOSTNAME = os.getenv("REDIS_HOSTNAME")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_ACCESS_KEY = os.getenv("REDIS_ACCESS_KEY")

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

# =============================================================================
# AUTHENTICATION
# =============================================================================

credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
openai_client = OpenAI(base_url=AZURE_OPENAI_ENDPOINT, api_key=token_provider)
content_safety_client = ContentSafetyClient(
    endpoint=CONTENT_SAFETY_ENDPOINT, credential=credential
)

redis_client = redis.Redis(
    host=REDIS_HOSTNAME,
    port=int(REDIS_PORT),
    password=REDIS_ACCESS_KEY,
    ssl=True,
    decode_responses=True,
)
if redis_client.ping():
    print("Successfully connected to Redis.")
else:
    print("Failed to connect to Redis.")
    sys.exit(1)

# =============================================================================
# INSTANTIATE CLASSES
# =============================================================================

# Instantiate ContentSafety class
content_safety = ContentSafety(content_safety_client, config)

# Instantiate RedisMemory class
redis_memory = RedisMemory(redis_client, config)

# Instantiate AgentWithMemory class
agent_with_memory = AgentWithMemory(
    llm_model_client=openai_client,
    llm_model_deployment_name=LLM_MODEL_DEPLOYMENT_NAME,
    redis_memory=redis_memory,
)

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

user_message_text = (
    "I'm still waiting for your help with my issue from earlier. Can you assist me now?"
)

# Input filtering
print("\n[INPUT FILTER] Scanning user message...")
if not content_safety.is_text_safe(user_message_text):
    print("User message blocked by Content Safety.")
    sys.exit(0)
print("User message passed safety check.")

print("\n[SYSTEM INSTRUCTION] Building system instruction with grounding results...")
# Build the dynamic system instruction
system_instruction = build_system_instruction(
    user_name=USER_NAME,
    user_role=USER_ROLE,
    session_state="Empty",
    grounding_results=None,
)

# Count and warn if token limit exceeded
token_count = count_tokens(system_instruction, model="gpt-4.1-mini")
if token_count > config["system_instructions"]["max_tokens"]:
    print(f"WARNING: System instruction exceeds token limit.")
print(f"System instruction token count: {token_count}")

print("\n[AGENT WITH MEMORY] Processing message with agent that has memory...")
reply, state = agent_with_memory.process_message(
    session_id="session1",
    user_message=user_message_text,
    system_instruction=system_instruction,
)
agent_with_memory.update_state(
    session_id="session1",
    state_updates={"last_interaction": datetime.utcnow().isoformat()},
)
# agent_with_memory.clear_memory(
#     session_id="session1"
# )  # Uncomment to test memory clearing

# Check if we got a valid response
if reply is None:
    print("ERROR: Failed to get response from model.")
    sys.exit(1)

# Output filtering
print("\n[OUTPUT FILTER] Scanning assistant response...")
if not content_safety.is_text_safe(reply):
    print("Assistant response blocked by Content Safety.")
    print(f"Returning safe default message: '{config['safe_responce']}'")
    print("\n" + "=" * 50)
    print("ASSISTANT REPLY (SAFE DEFAULT):")
    print("=" * 50)
    print(config["safe_responce"])
    print("=" * 50)
else:
    print("Assistant response passed safety check.")
    print("\n" + "=" * 50)
    print("ASSISTANT REPLY:")
    print("=" * 50)
    print(reply)
    print("=" * 50)

# =============================================================================
# UNIT 15 SUMMARY
# =============================================================================
# This script introduces Short-Term Session Memory with Redis:

# 1. SHORT-TERM MEMORY: Stores conversation history for current session only
# 2. REDIS: In-memory database with TTL (Time To Live) auto-expiration
# 3. TTL (TIME TO LIVE): Auto-deletes session after inactivity (1 hour default)
# 4. SESSION STATE: Tracks flags like awaiting_approval across turns
# 5. SLIDING WINDOW: Keeps only last 20 messages to prevent token overflow
