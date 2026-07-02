"""
UNIT 18: Input Transformation – NLP Preprocessing

WHAT'S NEW IN THIS UNIT:
1. Azure AI Language - A cloud service that provides Natural Language Processing
   (NLP) capabilities including language detection, PII redaction, entity extraction,
   key phrase extraction, and sentiment analysis
2. PII (Personally Identifiable Information) Redaction - Automatically detecting and
   removing sensitive information like credit card numbers, social security numbers,
   and email addresses from user input before the LLM sees it
3. NER (Named Entity Recognition) - Extracting and tagging entities like people,
   organizations, dates, and locations from text
4. Language Detection - Identifying what language the user is writing in
5. Sentiment Analysis - Determining if the user's message is positive, negative,
   or neutral
6. Transformation Pipeline - The order of preprocessing steps: language detection →
   PII redaction → entity extraction → key phrase extraction → sentiment analysis
"""

import os
import sys
import yaml

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential

from functions.helper_functions import count_tokens, build_system_instruction
from classes.content_safety import ContentSafety
from classes.basic_agent import BasicAgent
from classes.azure_nlp_services import AzureNLPService

# =============================================================================
# CONFIGURATION
# =============================================================================

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
LLM_MODEL_DEPLOYMENT_NAME = os.getenv("LLM_MODEL_DEPLOYMENT_NAME")
CONTENT_SAFETY_ENDPOINT = os.getenv("CONTENT_SAFETY_ENDPOINT")
USER_NAME = os.getenv("USER_NAME")
USER_ROLE = os.getenv("USER_ROLE")
LANGUAGE_ENDPOINT = os.getenv("LANGUAGE_ENDPOINT")
LANGUAGE_KEY = os.getenv("LANGUAGE_KEY")

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
language_client = TextAnalyticsClient(
    endpoint=LANGUAGE_ENDPOINT, credential=AzureKeyCredential(LANGUAGE_KEY)
)

# =============================================================================
# INSTANTIATE CLASSES
# =============================================================================

# Instantiate ContentSafety class
content_safety = ContentSafety(content_safety_client, config)

# Instantiate AzureNLPService class
azure_nlp_service = AzureNLPService(language_client=language_client, config=config)

# Instantiate BasicAgent class
basic_agent = BasicAgent(
    llm_model_client=openai_client,
    llm_model_deployment_name=LLM_MODEL_DEPLOYMENT_NAME,
)

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

user_message_text = "What's the weather like in New York next week? Also, my credit card number is 4111 1111 1111 1111."

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

print("\n[AZURE NLP SERVICE] Preprocessing user input with Azure AI Language...")
azure_nlp_service_response = azure_nlp_service.preprocess_user_input(user_message_text)
print(
    "\n[EXTEND SYSTEM INSTRUCTION] Adding NLP preprocessing context to system instruction..."
)

# Replace original user message with redacted and tagged version for the agent to process
user_message_text = azure_nlp_service_response["tagged"]

# Extend system instruction with NLP context
system_instruction = azure_nlp_service.extend_system_instruction_with_context(
    system_instruction, azure_nlp_service_response
)

print("\n[BASIC AGENT] Processing message with agent that has nlp capabilities...")
reply = basic_agent.process_message(
    user_message=user_message_text,
    system_instruction=system_instruction,
)

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
# UNIT 18 SUMMARY
# =============================================================================
# This script introduces Input Transformation with Azure AI Language:

# 1. LANGUAGE DETECTION: Identifies what language the user is writing in
# 2. PII REDACTION: Removes sensitive info (credit cards, SSNs, emails) from input
# 3. NAMED ENTITY RECOGNITION (NER): Tags people, organizations, dates, locations
# 4. KEY PHRASE EXTRACTION: Identifies main topics in user's message
# 5. SENTIMENT ANALYSIS: Detects positive, negative, or neutral mood
# 6. TRANSFORMATION PIPELINE: Language → PII → Entities → Key Phrases → Sentiment
