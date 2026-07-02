"""
UNIT 19: Secure Secret Management with Azure Key Vault

WHAT'S NEW IN THIS UNIT:
1. Azure Key Vault - A cloud service for securely storing and managing secrets,
   keys, and certificates, eliminating hardcoded credentials from code
2. Bicep Integration - Deploying Key Vault and storing secrets directly through
   infrastructure-as-code templates during deployment
3. RBAC Permissions - Using Azure Role-Based Access Control via CLI to grant
   fine-grained access to secrets without modifying infrastructure code
4. Managed Identity Authentication - Connecting to Key Vault using Azure AD
   identities instead of connection strings or keys
5. Secret Caching - Implementing an LRU cache to minimize network calls to
   Key Vault and improve application performance
6. SecretManager Pattern - Creating a reusable class that handles secret
   retrieval, caching, and error handling with minimal code changes
"""

import os
import sys
import yaml

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from azure.keyvault.secrets import SecretClient

from functions.helper_functions import count_tokens, build_system_instruction
from classes.content_safety import ContentSafety
from classes.basic_agent import BasicAgent
from classes.azure_nlp_services import AzureNLPService
from classes.secret_manager import SecretManager

# =============================================================================
# CONFIGURATION
# =============================================================================

key_vault_url = os.getenv("KEY_VAULT_URL")
user_name = os.getenv("USER_NAME")
user_role = os.getenv("USER_ROLE")

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

# =============================================================================
# AUTHENTICATION
# =============================================================================

credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
secret_manager = SecretManager(secret_client)

token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
openai_client = OpenAI(
    base_url=secret_manager.get_secret("AZURE-OPENAI-ENDPOINT"), api_key=token_provider
)
content_safety_client = ContentSafetyClient(
    endpoint=secret_manager.get_secret("CONTENT-SAFETY-ENDPOINT"), credential=credential
)
language_client = TextAnalyticsClient(
    endpoint=secret_manager.get_secret("LANGUAGE-ENDPOINT"),
    credential=AzureKeyCredential(secret_manager.get_secret("LANGUAGE-KEY")),
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
    llm_model_deployment_name=secret_manager.get_secret("LLM-MODEL-DEPLOYMENT-NAME"),
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
    user_name=user_name,
    user_role=user_role,
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
# UNIT 19 SUMMARY
# =============================================================================
# This script introduces Secure Secret Management with Azure Key Vault:

# 1. KEY VAULT DEPLOYMENT: Create vault with Bicep, store secrets during deployment
# 2. RBAC PERMISSIONS: Grant "Key Vault Secrets User" role using Azure CLI
# 3. MANAGED IDENTITY: Authenticate without credentials using Azure AD
# 4. SECRET MANAGER: Retrieve secrets with @lru_cache for performance
# 5. MIGRATION: Move from env vars to Key Vault without changing business logic
