"""
UNIT 12: Multi-Agent – Magentic (Manager) Pattern
PRIOR UNIT STATE: The script used a handoff pattern where two peer agents (Support
and Billing) transferred control directly to each other. Agents were aware of each
other and could hand off conversations.

WHAT'S NEW IN THIS UNIT:
1. Magentic/Manager Pattern - A hierarchical pattern where a manager agent receives
   all user requests and delegates to specialized sub-agents without the sub-agents
   knowing about each other
2. Manager Agent - An agent that never answers directly but identifies intent and
   routes to the correct specialist sub-agent
3. Sub-Agents - Specialized agents (Refund, Product, Account) that receive delegated
   tasks and return results to the manager, not directly to the user
4. Routing Metrics - Tracking which sub-agent handles how many requests for monitoring
5. No State Transfer - Unlike handoff, sub-agents don't receive conversation history
"""

import os
import yaml

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.contentsafety import ContentSafetyClient

from classes.content_safety import ContentSafety
from classes.manager_agent import ManagerAgent
from classes.refund_agent import RefundAgent
from classes.product_agent import ProductAgent
from classes.account_agent import AccountAgent

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

# Instantiate RefundAgent class
refund_agent = RefundAgent(
    openai_client=openai_client,
    llm_deployment_name=LLM_MODEL_DEPLOYMENT_NAME,
)

# Instantiate ProductAgent class
product_agent = ProductAgent(
    openai_client=openai_client,
    llm_deployment_name=LLM_MODEL_DEPLOYMENT_NAME,
)

# Instantiate AccountAgent class
account_agent = AccountAgent(
    openai_client=openai_client,
    llm_deployment_name=LLM_MODEL_DEPLOYMENT_NAME,
)

# Instantiate ManagerAgent class with references to sub-agents
manager_agent = ManagerAgent(
    openai_client=openai_client,
    llm_deployment_name=LLM_MODEL_DEPLOYMENT_NAME,
    refund_agent=refund_agent,
    product_agent=product_agent,
    account_agent=account_agent,
    user_name=USER_NAME,
)

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

print("\n" + "=" * 60)
print("MULTI-AGENT MAGENTIC (MANAGER) PATTERN DEMONSTRATION")
print("=" * 60)
print("This system uses a MANAGER agent that delegates to specialized sub-agents:")
print("  1. ManagerAgent - Routes requests to the correct specialist")
print("  2. RefundAgent - Handles refunds and returns")
print("  3. ProductAgent - Answers product questions")
print("  4. AccountAgent - Manages account settings")
print("\nThe manager NEVER answers directly - it only delegates.")
print("Sub-agents do NOT know about each other.\n")

print("-" * 40)
print("WHAT EACH SPECIALIST HANDLES:")
print("-" * 40)
print("• RefundAgent: refunds, returns, money back")
print("• ProductAgent: product specs, features, comparisons")
print("• AccountAgent: password, profile, account settings")
print("-" * 40)

# Start the conversation
print("\n" + "=" * 60)
print("STARTING CONVERSATION")
print("=" * 60)
print("Type 'quit', 'exit', or 'bye' to end the conversation.\n")
print("Try asking about:")
print("  - 'I want a refund for order #12345'")
print("  - 'What are the specs of the Pro model?'")
print("  - 'How do I reset my password?'\n")

user_input = input("[You] ")

while user_input.lower() not in ["quit", "exit", "bye"]:
    # Input filtering (from Unit 3)
    if not content_safety.is_text_safe(user_input):
        print("\n[ASSISTANT] I cannot process that request due to content safety.")
        user_input = input("\n[You] ")
        continue

    # Process through manager (delegates to appropriate specialist)
    response = manager_agent.process_message(user_input)

    # Output filtering (from Unit 3)
    if not content_safety.is_text_safe(response):
        print(f"\n[ASSISTANT] {SAFE_RESPONSE}")
    else:
        print(f"\n[ASSISTANT] {response}")

    user_input = input("\n[You] ")

# Display routing metrics
print("\n" + "=" * 50)
print("CONVERSATION ENDED")
print("=" * 50)

metrics = manager_agent.get_metrics()
print("\nROUTING METRICS:")
print("-" * 40)
print(f"Total requests routed: {metrics['total_requests']}")
print(f"  → RefundAgent: {metrics['refund']}")
print(f"  → ProductAgent: {metrics['product']}")
print(f"  → AccountAgent: {metrics['account']}")
print(f"  → Unable to route: {metrics['unable_to_route']}")


# =============================================================================
# UNIT 12 SUMMARY
# =============================================================================
# This script introduces the Magentic (Manager) multi-agent pattern:
# 1. MANAGER AGENT: Routes requests to specialists, never answers directly
# 2. SUB-AGENTS: Specialized agents that handle specific domains
# 3. NO STATE TRANSFER: Sub-agents don't get conversation history (unlike handoff)
# 4. ROUTING METRICS: Track which sub-agent handles how many requests
# 5. HIERARCHICAL CONTROL: Manager knows about sub-agents, but sub-agents don't
#    know about each other or the manager
