"""
UNIT 2: Content Safety – Input and Output Filtering
PRIOR UNIT STATE: The script sent a prompt to Azure OpenAI.
It had no safety filtering before or after the LLM call.
WHAT'S NEW IN THIS UNIT:
1. Azure AI Content Safety - A cloud service that scans text for four categories
   of harmful content: hate, sexual, violence, and self-harm
2. Input Filtering - Scanning user messages BEFORE they reach the LLM
3. Output Filtering - Scanning assistant responses BEFORE they are shown to the user
4. Severity Thresholds - Configurable levels (0-6) that determine when to block content
"""

import os
import sys

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# Content Safety SDK provides functions to scan text for harmful content
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeTextOptions

# =============================================================================
# CONFIGURATION
# =============================================================================

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# Content Safety configuration (NEW in Unit 2)
# This is a separate Azure service from Azure OpenAI.
CONTENT_SAFETY_ENDPOINT = os.getenv("CONTENT_SAFETY_ENDPOINT")

# SEVERITY THRESHOLD: Numbers from 0 (safe) to 6 (extremely harmful)
# If any category exceeds this threshold, the content is blocked.
SEVERITY_THRESHOLD = 1

# SAFE DEFAULT MESSAGE: Returned when Content Safety blocks output
SAFE_RESPONSE = "I cannot generate a response to this request."

# =============================================================================
# AUTHENTICATION
# =============================================================================

# Create Azure OpenAI client (from Unit 1)
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://ai.azure.com/.default"
)
client = OpenAI(base_url=AZURE_OPENAI_ENDPOINT, api_key=token_provider)

# Create Content Safety client (NEW in Unit 2)
# This client scans text for harmful content before and after the LLM call.
content_safety_client = ContentSafetyClient(
    endpoint=CONTENT_SAFETY_ENDPOINT, credential=DefaultAzureCredential()
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def is_text_safe(text_to_check):
    """
    Scan text for harmful content using Azure AI Content Safety.
    Returns True if safe (below threshold for all categories).
    Returns False if any category exceeds the threshold.

    The four categories Content Safety checks:
    1. HATE: Attacks based on race, religion, gender identity, etc.
    2. SEXUAL: Explicit sexual content or references
    3. VIOLENCE: Threats, descriptions of harm, or glorification of violence
    4. SELF_HARM: Content related to self-injury or suicide
    """
    analysis_request = AnalyzeTextOptions(text=text_to_check)
    analysis_result = content_safety_client.analyze_text(analysis_request)

    categories_result = analysis_result["categoriesAnalysis"]
    hate_severity = next(
        (c["severity"] for c in categories_result if c["category"] == "Hate"), None
    )
    sexual_severity = next(
        (c["severity"] for c in categories_result if c["category"] == "Sexual"), None
    )
    violence_severity = next(
        (c["severity"] for c in categories_result if c["category"] == "Violence"), None
    )
    self_harm_severity = next(
        (c["severity"] for c in categories_result if c["category"] == "SelfHarm"), None
    )

    # Check each category against the severity threshold
    if hate_severity > SEVERITY_THRESHOLD:
        print(f"Blocked: HATE content (severity {hate_severity})")
        return False

    if sexual_severity > SEVERITY_THRESHOLD:
        print(f"Blocked: SEXUAL content (severity {sexual_severity})")
        return False

    if violence_severity > SEVERITY_THRESHOLD:
        print(f"Blocked: VIOLENCE content (severity {violence_severity})")
        return False

    if self_harm_severity > SEVERITY_THRESHOLD:
        print(f"Blocked: SELF_HARM content (severity {self_harm_severity})")
        return False

    return True


# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

# System message defines agent behavior (from Unit 1)
system_message = {
    "role": "system",
    "content": "You are a helpful assistant that provides safe, respectful responses.",
}

# Get user input
user_message_text = "I hate you"
# user_message_text = "What is a quick description of an LLM?"

print("\n" + "=" * 60)
print("CONTENT SAFETY DEMONSTRATION")
print("=" * 60)

# STEP 1: INPUT FILTERING - Scan user message BEFORE it reaches the LLM
# This protects the agent from harmful user inputs.
print("\n[INPUT FILTER] Scanning user message for harmful content...")

if not is_text_safe(user_message_text):
    print("User message blocked by Content Safety. No request sent to AI.")
    print("The agent was protected from harmful input.")
    sys.exit(0)

print("User message passed safety check. Sending to AI...")

# If input is safe, proceed to call the LLM
user_message = {"role": "user", "content": user_message_text}
messages = [system_message, user_message]


# Call the Azure OpenAI API
response = client.chat.completions.create(
    model=AZURE_OPENAI_DEPLOYMENT_NAME,
    messages=messages,
)

assistant_reply = response.choices[0].message.content

# STEP 2: OUTPUT FILTERING - Scan assistant response BEFORE showing to user
# This protects the user from harmful agent outputs.
print("\n[OUTPUT FILTER] Scanning assistant response for harmful content...")

if not is_text_safe(assistant_reply):
    print("Assistant response blocked by Content Safety.")
    print(f"Returning safe default message: '{SAFE_RESPONSE}'")
    print("\n" + "=" * 50)
    print("ASSISTANT REPLY (SAFE DEFAULT):")
    print("=" * 50)
    print(SAFE_RESPONSE)
    print("=" * 50)
else:
    print("Assistant response passed safety check. Showing to user.")
    print("\n" + "=" * 50)
    print("ASSISTANT REPLY:")
    print("=" * 50)
    print(assistant_reply)
    print("=" * 50)

# Print token usage if available
if hasattr(response, "usage") and response.usage:
    print(
        f"\nToken usage - Prompt: {response.usage.prompt_tokens}, "
        f"Completion: {response.usage.completion_tokens}, "
        f"Total: {response.usage.total_tokens}"
    )


# =============================================================================
# UNIT 2 SUMMARY
# =============================================================================
# This script introduces Azure AI Content Safety for responsible AI:
# 1. INPUT FILTERING: Scans user messages before they reach the LLM
# 2. OUTPUT FILTERING: Scans assistant responses before they reach the user
# 3. FOUR CATEGORIES: Hate, Sexual, Violence, Self-harm (severity 0-6)
# 4. CONFIGURABLE THRESHOLDS: Set severity levels that trigger blocking
#
# Key takeaways for the AI-103 exam:
# - Content Safety requires BOTH input and output filtering
# - Severity thresholds are configurable per application
# - Content Safety is a separate Azure service with its own endpoint and key
# - Always "fail closed" (block) when Content Safety is unavailable
