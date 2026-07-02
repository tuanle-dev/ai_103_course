"""
UNIT 17: Multimodal Integration – Vision, Speech, Document Intelligence

WHAT'S NEW IN THIS UNIT:
1. Azure AI Vision - A cloud service that analyzes images to generate captions
   (descriptions of what's in the image) and extract text (OCR - Optical Character
   Recognition)
2. Azure AI Speech - A cloud service that converts spoken audio to text (speech-to-text)
   and text to spoken audio (text-to-speech)
3. Azure AI Document Intelligence - A cloud service that extracts structured data
   from documents like invoices, receipts, and ID cards
"""

import os
import sys
import yaml

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.vision.imageanalysis import ImageAnalysisClient
import azure.cognitiveservices.speech as speechsdk
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

from functions.helper_functions import count_tokens, build_system_instruction
from classes.content_safety import ContentSafety
from classes.basic_agent import BasicAgent
from classes.azure_ai_services import AzureAIService

# =============================================================================
# CONFIGURATION
# =============================================================================

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
LLM_MODEL_DEPLOYMENT_NAME = os.getenv("LLM_MODEL_DEPLOYMENT_NAME")
CONTENT_SAFETY_ENDPOINT = os.getenv("CONTENT_SAFETY_ENDPOINT")
USER_NAME = os.getenv("USER_NAME")
USER_ROLE = os.getenv("USER_ROLE")
VISION_ENDPOINT = os.getenv("VISION_ENDPOINT")
VISION_KEY = os.getenv("VISION_KEY")
SPEECH_REGION = os.getenv("SPEECH_REGION")
SPEECH_KEY = os.getenv("SPEECH_KEY")
DOC_INTEL_ENDPOINT = os.getenv("DOC_INTEL_ENDPOINT")
DOC_INTEL_KEY = os.getenv("DOC_INTEL_KEY")

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
vision_client = ImageAnalysisClient(
    endpoint=VISION_ENDPOINT, credential=AzureKeyCredential(VISION_KEY)
)
speech_config_client = speechsdk.SpeechConfig(
    subscription=SPEECH_KEY, region=SPEECH_REGION
)
doc_intel_client = DocumentIntelligenceClient(
    endpoint=DOC_INTEL_ENDPOINT, credential=AzureKeyCredential(DOC_INTEL_KEY)
)

# =============================================================================
# INSTANTIATE CLASSES
# =============================================================================

# Instantiate ContentSafety class
content_safety = ContentSafety(content_safety_client, config)

# Instantiate AzureAIService class
azure_ai_service = AzureAIService(
    vision_client=vision_client,
    speech_config=speech_config_client,
    doc_intel_client=doc_intel_client,
)

# Instantiate BasicAgent class
basic_agent = BasicAgent(
    llm_model_client=openai_client,
    llm_model_deployment_name=LLM_MODEL_DEPLOYMENT_NAME,
)

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

user_message_text = "What do you see in what I've uploaded?"

azure_ai_service_response = azure_ai_service.route_multimodal_request(
    content_type="jpeg", content_path="inputs/broken_tv.jpeg"
)
# azure_ai_service_response = azure_ai_service.route_multimodal_request(
#     content_type="invoice", content_path="inputs/invoice_2001321.pdf"
# )
# azure_ai_service_response = azure_ai_service.route_multimodal_request(
#     content_type="wav", content_path="inputs/voice_recording.wav"
# )

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

print(
    "\n[BASIC AGENT] Processing message with agent that has multimodal capabilities..."
)
reply = basic_agent.process_message(
    user_message=user_message_text,
    system_instruction=system_instruction,
    azure_ai_service_response=azure_ai_service_response,
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
# UNIT 17 SUMMARY
# =============================================================================
# This script introduces Multimodal Integration:
# 1. AZURE AI VISION: Analyzes images (caption description + OCR text extraction)
# 2. AZURE AI SPEECH: Converts speech to text (STT) and text to speech (TTS)
# 3. AZURE AI DOCUMENT INTELLIGENCE: Extracts structured data from invoices,
#    receipts, and ID documents using prebuilt models
