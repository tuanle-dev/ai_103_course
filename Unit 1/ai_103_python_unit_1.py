"""
UNIT 1: Foundation – Your First Agent Call
This script demonstrates how to call an Azure OpenAI model using the OpenAI SDK and Azure Identity for authentication.

KEY CONCEPTS IN THIS UNIT:
1. Azure OpenAI service: Cloud-hosted large language models (LLMs) accessed via REST API.
2. Secure authentication: Uses Azure Identity to obtain a bearer token instead of a static API key.
3. Agent call pattern: Sends a system message (instructions) and a user message (question) to the model.
4. Response extraction: Retrieves the AI's answer from the SDK's structured response object.
"""

import os

# The OpenAI SDK provides ready-to-use functions for calling Azure's AI models
from openai import OpenAI

# The Azure Identity library helps us securely authenticate to Azure services without hardcoding secrets.
# get_bearer_token_provider creates a token provider using Azure's identity system for secure access.
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# =============================================================================
# CONFIGURATION
# =============================================================================
# These configuration variables tell our code WHERE to send the request (endpoint),
# WHAT secret key to use for permission (API key), and which model deployment to use.

# ENDPOINT: The web address (URL) of your deployed Azure OpenAI resource.
# Example: "https://your-resource.openai.azure.com/"
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

# DEPLOYMENT NAME: The name you gave your model deployment in Azure OpenAI Studio or Foundry.
# One endpoint can host multiple deployments; this name selects which one to use.
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# =============================================================================
# AUTHENTICATION
# =============================================================================
# Create a client object that will handle all communication with Azure OpenAI.
# Instead of a static API key, we use a bearer token provider for secure authentication.
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://ai.azure.com/.default"
)
client = OpenAI(base_url=AZURE_OPENAI_ENDPOINT, api_key=token_provider)


# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

# SYSTEM MESSAGE: A special instruction that tells the AI how to behave.
# Not shown to the user; defines the agent's "personality" and rules.
system_message = {"role": "system", "content": "You are a helpful assistant."}

# USER MESSAGE: The question or request from the person using the agent.
# In a real application, this would come from user input (e.g., a chat box).
# Here, we use a fixed message for demonstration.
user_message = {
    "role": "user",
    "content": "What is an AI agent? Explain in one sentence.",
}

# MESSAGES ARRAY: Holds the conversation history for the model.
# Always starts with the system message, then user messages, and later assistant responses.
messages = [system_message, user_message]

# Send the request to Azure OpenAI and wait for the response.
# .chat.completions.create() is the SDK function that calls the chat completion API.
print("Sending request to Azure OpenAI...")


# Call the API. This is a synchronous call - the code pauses here and waits
# for Azure to respond. (Async patterns are covered in later units.)
response = client.chat.completions.create(
    model=AZURE_OPENAI_DEPLOYMENT_NAME,
    messages=messages,
)

# Extract the assistant's reply from the response object.
# The response is a structured object:
# response.choices[0].message.content -> The actual text answer from the assistant.
assistant_reply = response.choices[0].message.content

# Print the assistant's reply to the console so the user can see it.
print("\n" + "=" * 50)
print("ASSISTANT REPLY:")
print("=" * 50)
print(assistant_reply)
print("=" * 50)

# Print token usage information if available.
# Tokens are how Azure measures usage. Each request costs tokens.
# For GPT-4 models, a token is roughly 4 characters of English text.
if hasattr(response, "usage") and response.usage:
    print(
        f"\nToken usage - Prompt: {response.usage.prompt_tokens}, "
        f"Completion: {response.usage.completion_tokens}, "
        f"Total: {response.usage.total_tokens}"
    )

# =============================================================================
# UNIT 1 SUMMARY
# =============================================================================
# This script demonstrates the minimum viable agent:
# 1. Configuration via environment variables (never hardcode secrets!)
# 2. Authentication using Azure Identity and bearer tokens
# 3. A system message defining agent behavior
# 4. A user message with the actual question
# 5. Sending the messages array to the model
# 6. Extracting and displaying the assistant's reply
