"""
UNIT 11: Multi-Agent – Handoff Pattern
PRIOR UNIT STATE: The script had a single agent that used MCP to discover and call
tools from an MCP server. It could not transfer conversations to specialized agents.

WHAT'S NEW IN THIS UNIT:
1. Handoff Pattern - A multi-agent pattern where one agent transfers control to
   another specialized agent, passing the full conversation history to maintain context.
2. Agent Classes - Separate Python classes for different agent roles (Support and Billing)
3. Handoff Tool - A special tool that allows the LLM to request transfer to another agent
4. Router Function - A function that directs user messages to the currently active agent
"""

import os
import yaml

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.contentsafety import ContentSafetyClient

from classes.content_safety import ContentSafety
from classes.support_agent import SupportAgent
from classes.billing_agent import BillingAgent
from classes.conversation_router import ConversationRouter

# =============================================================================
# CONFIGURATION
# =============================================================================

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
LLM_MODEL_DEPLOYMENT_NAME = os.getenv("LLM_MODEL_DEPLOYMENT_NAME")
CONTENT_SAFETY_ENDPOINT = os.getenv("CONTENT_SAFETY_ENDPOINT")
USER_NAME = os.getenv("USER_NAME")

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

SAFE_RESPONSE = "I cannot generate a response to this request."

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

# Instantiate SupportAgent class
support_agent = SupportAgent(
    openai_client=openai_client,
    llm_deployment_name=LLM_MODEL_DEPLOYMENT_NAME,
    user_name=USER_NAME,
    config=config,
)

# Instantiate BillingAgent class
billing_agent = BillingAgent(
    openai_client=openai_client,
    llm_deployment_name=LLM_MODEL_DEPLOYMENT_NAME,
    user_name=USER_NAME,
    config=config,
)

# Instantiate ConversationRouter class
router = ConversationRouter(
    content_safety=content_safety,
    support_agent=support_agent,
    billing_agent=billing_agent,
    user_name=USER_NAME,
)

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

# Start the conversation
print("\n" + "=" * 60)
print("STARTING CONVERSATION")
print("=" * 60)
print("Type 'quit', 'exit', or 'bye' to end the conversation.\n")

user_input = input("[You] ")

while user_input.lower() not in ["quit", "exit", "bye"]:
    response = router.process_message(user_input)

    # Output filtering (from Unit 3)
    if not content_safety.is_text_safe(response):
        print(f"\n[ASSISTANT - {router.current_agent}] {SAFE_RESPONSE}")
    else:
        print(f"\n[ASSISTANT - {router.current_agent}] {response}")

    user_input = input("\n[You] ")

print("\n" + "=" * 50)
print("CONVERSATION ENDED")
print("=" * 50)
print(f"Final agent: {router.current_agent}")
print(f"Total conversation turns: {len(router.conversation_history) // 2}")


# =============================================================================
# UNIT 11 SUMMARY
# =============================================================================
# This script introduces the Multi-Agent Handoff pattern:
# 1. AGENT CLASSES: Separate classes for different specialized roles
# 2. HANDOFF TOOL: A tool that allows agents to request transfer
# 3. CONVERSATION ROUTER: Manages which agent is active and handles handoffs
