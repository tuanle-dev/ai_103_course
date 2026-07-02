"""
UNIT 16: Agent Memory – Long-Term User Memory (Cosmos DB)

WHAT'S NEW IN THIS UNIT:
1. Long-Term Memory - Storing user preferences and history across multiple sessions
   so the agent remembers returning users between conversations
2. Cosmos DB - A globally distributed NoSQL database that provides persistent
   storage with automatic indexing and TTL (Time To Live)
3. User Profile - A document storing user preferences that persists across sessions
4. Hybrid Memory - Combining short-term (Redis) and long-term (Cosmos DB) memory:
   load long-term preferences at conversation start, store short-term during session
5. Partition Key - A field that determines how data is distributed across Cosmos DB
   (using userId as partition key for performance)
"""

import os
import sys
import yaml
from datetime import datetime

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.contentsafety import ContentSafetyClient
import redis
from azure.cosmos import CosmosClient

from functions.helper_functions import count_tokens, build_system_instruction
from classes.content_safety import ContentSafety
from classes.redis_memory import RedisMemory
from classes.cosmos_memory import CosmosMemory
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
COSMOS_DB_ENDPOINT = os.getenv("COSMOS_DB_ENDPOINT")
COSMOS_PRIMARY_KEY = os.getenv("COSMOS_PRIMARY_KEY")
COSMOS_DB_NAME = os.getenv("COSMOS_DB_NAME")
COSMOS_CONTAINER_NAME = os.getenv("COSMOS_CONTAINER_NAME")

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

cosmos_db_client = CosmosClient(
    url=COSMOS_DB_ENDPOINT,
    credential=COSMOS_PRIMARY_KEY,
)
# Check if the database and continer exists
database_client = cosmos_db_client.get_database_client(COSMOS_DB_NAME)
database_client.read()

container_client = database_client.get_container_client(COSMOS_CONTAINER_NAME)
container_client.read()

# =============================================================================
# INSTANTIATE CLASSES
# =============================================================================

# Instantiate ContentSafety class
content_safety = ContentSafety(content_safety_client, config)

# Instantiate CosmosMemory class
cosmos_memory = CosmosMemory(
    cosmos_client=cosmos_db_client,
    database_client=database_client,
    container_client=container_client,
    config=config,
)

# Instantiate RedisMemory class
redis_memory = RedisMemory(redis_client, config)

# Instantiate AgentWithMemory class
agent_with_memory = AgentWithMemory(
    llm_model_client=openai_client,
    llm_model_deployment_name=LLM_MODEL_DEPLOYMENT_NAME,
    redis_memory=redis_memory,
    cosmos_memory=cosmos_memory,
)

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

user_message_text = "I'm trying to refund my broken TV. Can you assist me now?"

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
reply, state, user_prefs = agent_with_memory.process_message(
    session_id="session123",
    user_id="luke.ginn1",
    user_message=user_message_text,
    system_instruction=system_instruction,
)
agent_with_memory.update_state(
    session_id="session123",
    state_updates={"last_interaction": datetime.utcnow().isoformat()},
)
# agent_with_memory.clear_memory(
#     session_id="session1"
# )  # Uncomment to test memory clearing

agent_with_memory.update_user_preference(
    user_id="luke.ginn1", key="language", value="Spanish"
)  # Example of updating a user preference.

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
# UNIT 16 SUMMARY
# =============================================================================
# This script introduces Long-Term User Memory with Cosmos DB:
# 1. LONG-TERM MEMORY: Stores user preferences across multiple sessions
# 2. COSMOS DB: Globally distributed NoSQL database for persistent storage
# 3. PARTITION KEY: '/userId' distributes data evenly across partitions
# 4. HYBRID MEMORY: Short-term (Redis for conversation) + Long-term (Cosmos DB)
# 5. USER PROFILE: Preferences loaded at conversation start, saved on change
# 6. TTL: Auto-deletes inactive user profiles to manage costs
