"""
UNIT 8: Integrating Azure AI Search for Grounding Results & Advanced Parameter Exploration

NEW IN THIS UNIT:
1. Azure AI Search Integration – Introduce Azure AI Search to provide grounding results for user queries. Relevant documents are retrieved and incorporated into the system prompt, improving the factual accuracy and relevance of model responses.
2. Understand how tuning parameters and grounding with Azure AI Search impacts response quality, cost, and performance
3. Compare parameter effects for both SLM and LLM deployments, now with grounded context
4. Continue to use intent classification and model routing from previous unit, now enhanced with grounded search results
"""

import os
import sys
import yaml

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.contentsafety import ContentSafetyClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

from functions.helper_functions import (
    count_tokens,
    is_text_safe,
    build_system_instruction,
)
from functions.model_routing import route_to_model
from functions.ai_search_functions import (
    create_index,
    get_documents,
    upload_documents,
    search_documents,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
LLM_MODEL_DEPLOYMENT_NAME = os.getenv("LLM_MODEL_DEPLOYMENT_NAME")
SLM_MODEL_DEPLOYMENT_NAME = os.getenv("SLM_MODEL_DEPLOYMENT_NAME")
EMBEDDING_MODEL_DEPLOYMENT_NAME = os.getenv("EMBEDDING_MODEL_DEPLOYMENT_NAME")
CONTENT_SAFETY_ENDPOINT = os.getenv("CONTENT_SAFETY_ENDPOINT")
AI_SEARCH_SERVICE_ENDPOINT = os.getenv("AI_SEARCH_SERVICE_ENDPOINT")
USER_NAME = os.getenv("USER_NAME")
USER_ROLE = os.getenv("USER_ROLE")

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

SESSION_STATE = "Empty"
INDEX_NAME = "my-index"

# =============================================================================
# AUTHENTICATION
# =============================================================================

credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
openai_client = OpenAI(base_url=AZURE_OPENAI_ENDPOINT, api_key=token_provider)
content_safety_client = ContentSafetyClient(
    endpoint=CONTENT_SAFETY_ENDPOINT, credential=credential
)
index_client = SearchIndexClient(AI_SEARCH_SERVICE_ENDPOINT, credential)
ai_search_client = SearchClient(AI_SEARCH_SERVICE_ENDPOINT, INDEX_NAME, credential)

# =============================================================================
# AI SEARCH SETUP
# =============================================================================

# Step 1: Create index
index_status = create_index(index_client, INDEX_NAME)

if index_status != "Index already exists":

    # Step 2: Get documents to upload
    documents = get_documents()

    # Step 3: Upload documents
    upload_documents(
        ai_search_client,
        openai_client,
        EMBEDDING_MODEL_DEPLOYMENT_NAME,
        INDEX_NAME,
        documents,
    )

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

user_message_text = "Can you please refund my order? I bought a TV previously, with an order ID of 12345, and it was not functioning when I first got it out of the box."

print("\n" + "=" * 60)
print("CONTENT SAFETY & MODEL ROUTING DEMONSTRATION")
print("=" * 60)

# Input filtering (from Unit 3)
print("\n[INPUT FILTER] Scanning user message...")
if not is_text_safe(
    content_safety_client,
    user_message_text,
    config["content_safety"]["severity_threshold"],
):
    print("User message blocked by Content Safety.")
    sys.exit(0)
print("User message passed safety check.")


print("\n" + "=" * 60)
print("GROUNDING DEMONSTRATION: AI Search for Relevant Documents")
print("=" * 60)
grounding_results = search_documents(
    ai_search_client,
    openai_client,
    EMBEDDING_MODEL_DEPLOYMENT_NAME,
    user_message_text,
    config["ai_search"]["top_k"],
)

print("\n" + "=" * 60)
print("MODEL SELECTION DEMONSTRATION")
print("=" * 60)
print("This agent routes simple questions to Phi-4 (SLM) and")
print("complex questions to GPT-4.1-Mini (LLM) for cost optimization.\n")

# Build the dynamic system instruction
system_instruction = build_system_instruction(
    user_name=USER_NAME,
    user_role=USER_ROLE,
    session_state=SESSION_STATE,
    grounding_results=grounding_results,
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

reply, model_name, latency_ms, token_usage = route_to_model(
    openai_client,
    user_message_text,
    messages,
    use_slm_classifier=True,
    intent_classifier_max_tokens=config["intent_classifier"]["max_tokens"],
    intent_classifier_temperature=config["intent_classifier"]["temperature"],
    intent_classifier_top_p=config["intent_classifier"]["top_p"],
    llm_deployment_name=LLM_MODEL_DEPLOYMENT_NAME,
    llm_max_past_messages=config["llm"]["max_past_messages"],
    llm_max_tokens=config["llm"]["max_tokens"],
    llm_temperature=config["llm"]["temperature"],
    llm_top_p=config["llm"]["top_p"],
    slm_deployment_name=SLM_MODEL_DEPLOYMENT_NAME,
    slm_max_past_messages=config["slm"]["max_past_messages"],
    slm_max_tokens=config["slm"]["max_tokens"],
    slm_temperature=config["slm"]["temperature"],
    slm_top_p=config["slm"]["top_p"],
)

if reply is None:
    print("ERROR: Failed to get response from model.")
    sys.exit(1)

# Output filtering (from Unit 3)
print("\n[OUTPUT FILTER] Scanning assistant response...")
if not is_text_safe(
    content_safety_client, reply, config["content_safety"]["severity_threshold"]
):
    print("Assistant response blocked by Content Safety.")
    print(f"Returning safe default message: '{config['safe_response']}'")
    print("\n" + "=" * 50)
    print("ASSISTANT REPLY (SAFE DEFAULT):")
    print("=" * 50)
    print(config["safe_response"])
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
# UNIT 8 SUMMARY
# =============================================================================
# This script demonstrates the integration of Azure AI Search to provide grounding results for user queries, enhancing the factual accuracy and relevance of model responses.
#
# Key features:
# 1. Azure AI Search: Retrieves relevant documents and incorporates them into the system prompt for grounding. The behavior of Azure AI Search is controlled by parameters such as the number of results to return, ranking strategy, and relevance thresholds. Adjusting these parameters allows fine-tuning of how much and what type of information is provided to the model, directly impacting the quality and specificity of grounded responses.
# 2. Parameter Exploration: Demonstrates how both model and search parameters (e.g., max_past_messages, max_tokens, temperature, top_p, and search-specific settings) can be tuned to optimize response quality, cost, and performance.
# 3. Continues to use intent classification and model routing, now enhanced with grounded search results.
# 4. Tracks cost and latency for each model call.
