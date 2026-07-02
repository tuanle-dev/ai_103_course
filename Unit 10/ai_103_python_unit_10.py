"""
UNIT 10: Model Context Protocol (MCP) – Standardized Tool Connectivity

WHAT'S NEW IN THIS UNIT:
1. Model Context Protocol (MCP) - A standardized "handshake" protocol that allows
   agents to discover and call tools from MCP servers without writing custom code
2. MCP Server - A service that exposes tools via the MCP protocol (e.g., SharePoint,
   file system, database servers) and handles the actual API calls
3. Tool Discovery - The agent asks the MCP server "what tools do you have?" at startup
   and receives tool names, descriptions, and parameter schemas automatically
4. Two-Phase Handshake - Phase 1: list_tools (discovery), Phase 2: call_tool (execution)
5. The MCP Server we used for this unit is: https://glama.ai/mcp/connectors/ai.exa/exa
"""

import os
import sys
import yaml

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.contentsafety import ContentSafetyClient

from functions.helper_functions import count_tokens, build_system_instruction
from classes.content_safety import ContentSafety
from classes.model_routing import ModelRouter
from classes.mcp_servers import MCPClient

# =============================================================================
# CONFIGURATION
# =============================================================================

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
LLM_MODEL_DEPLOYMENT_NAME = os.getenv("LLM_MODEL_DEPLOYMENT_NAME")
SLM_MODEL_DEPLOYMENT_NAME = os.getenv("SLM_MODEL_DEPLOYMENT_NAME")
CONTENT_SAFETY_ENDPOINT = os.getenv("CONTENT_SAFETY_ENDPOINT")
USER_NAME = os.getenv("USER_NAME")
USER_ROLE = os.getenv("USER_ROLE")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL")
MCP_SERVER_API_KEY = os.getenv("MCP_SERVER_API_KEY")

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

SESSION_STATE = "Empty"

# =============================================================================
# AUTHENTICATION
# =============================================================================

credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
openai_client = OpenAI(base_url=AZURE_OPENAI_ENDPOINT, api_key=token_provider)
content_safety_client = ContentSafetyClient(
    endpoint=CONTENT_SAFETY_ENDPOINT, credential=credential
)

# =============================================================================
# INSTANTIATE CLASSES
# =============================================================================

# Instantiate ContentSafety class
content_safety = ContentSafety(content_safety_client, config)

# Instantiate MCPClient class
mcp_client = MCPClient(
    server_url=MCP_SERVER_URL,
    api_key=MCP_SERVER_API_KEY,
    openai_client=openai_client,
    llm_deployment_name=LLM_MODEL_DEPLOYMENT_NAME,
    config=config,
)

# Instantiate ModelRouter class
model_router = ModelRouter(
    openai_client=openai_client,
    mcp_client=mcp_client,
    slm_deployment_name=SLM_MODEL_DEPLOYMENT_NAME,
    llm_deployment_name=LLM_MODEL_DEPLOYMENT_NAME,
    config=config,
)

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

user_message_text = "First, what is the weather in Brisbane right now. Then help me with my refund of a broken TV."

# Input filtering (from Unit 3)
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
    session_state=SESSION_STATE,
    grounding_results=None,
)

# Count and warn if token limit exceeded
token_count = count_tokens(system_instruction, model="gpt-4.1-mini")
if token_count > config["system_instructions"]["max_tokens"]:
    print(f"WARNING: System instruction exceeds token limit.")
print(f"System instruction token count: {token_count}")

system_message = {"role": "system", "content": system_instruction}

# Build messages and route to model
user_message = {"role": "user", "content": user_message_text}
messages = [system_message, user_message]

print(
    "\n[MODEL ROUTING] Routing to appropriate model based on intent classification..."
)
reply, model_name, latency_ms, token_usage = model_router.route_to_model(
    user_question=user_message_text,
    messages=messages,
)

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

# Display performance metrics
print("\n" + "=" * 50)
print("PERFORMANCE METRICS:")
print("=" * 50)
print(f"Model used: {model_name}")
print(f"Latency: {latency_ms:.2f} ms")

if token_usage:
    print(f"Prompt tokens: {token_usage['prompt_tokens']}")
    print(f"Completion tokens: {token_usage['completion_tokens']}")
    print(f"Total tokens: {token_usage['total_tokens']}")

    # Approximate cost estimates (actual rates vary by region)
    if model_name == "Phi-4 (SLM)":
        estimated_cost = token_usage["total_tokens"] * 0.0000002
        print(f"Estimated cost: ${estimated_cost:.6f} (SLM rates)")
    else:
        estimated_cost = token_usage["total_tokens"] * 0.00001
        print(f"Estimated cost: ${estimated_cost:.6f} (LLM rates)")


# =============================================================================
# UNIT 10 SUMMARY
# =============================================================================
# This script introduces the Model Context Protocol (MCP):
# 1. TWO-PHASE HANDSHAKE: list_tools (discovery) then call_tool (execution)
# 2. MCP CLIENT: Standardized communication with MCP servers
# 3. TOOL DISCOVERY: No hardcoded tool definitions - ask the server
# 4. RELATIVELY STANDARDIZED FORMAT: Tools aim to be described consistently across servers
