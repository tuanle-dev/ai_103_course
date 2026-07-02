"""
UNIT 14: OpenTelemetry Debugging

WHAT'S NEW IN THIS UNIT:
1. OpenTelemetry - An industry standard for collecting traces (records of what
   happened during execution) from distributed systems
2. Spans - Individual units of work within a trace (e.g., one LLM call, one tool call)
3. Span Attributes - Key-value pairs attached to spans that record details like
   model name, token count, latency, tool name, etc.
"""

import os
import sys
import yaml
import uuid

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.contentsafety import ContentSafetyClient

from functions.helper_functions import count_tokens, build_system_instruction
from classes.content_safety import ContentSafety
from classes.model_routing import ModelRouter
from classes.tool_functions import ToolFunctions
from classes.open_telemetry import OpenTelemetry

# =============================================================================
# MAIN SCRIPT LOGIC WITH TRACING
# =============================================================================


def main():
    # =============================================================================
    # CONFIGURATION
    # =============================================================================

    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    LLM_MODEL_DEPLOYMENT_NAME = os.getenv("LLM_MODEL_DEPLOYMENT_NAME")
    SLM_MODEL_DEPLOYMENT_NAME = os.getenv("SLM_MODEL_DEPLOYMENT_NAME")
    CONTENT_SAFETY_ENDPOINT = os.getenv("CONTENT_SAFETY_ENDPOINT")
    USER_NAME = os.getenv("USER_NAME")
    USER_ROLE = os.getenv("USER_ROLE")
    WEATHER_API_ENDPOINT = os.getenv("WEATHER_API_ENDPOINT")
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
    EXCHANGE_RATE_API_ENDPOINT = os.getenv("EXCHANGE_RATE_API_ENDPOINT")
    EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")
    APPLICATION_INSIGHTS_CONNECTION_STRING = os.getenv(
        "APPLICATION_INSIGHTS_CONNECTION_STRING"
    )

    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)

    SESSION_STATE = "Empty"

    # =============================================================================
    # AUTHENTICATION
    # =============================================================================

    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential, "https://ai.azure.com/.default"
    )
    openai_client = OpenAI(base_url=AZURE_OPENAI_ENDPOINT, api_key=token_provider)
    content_safety_client = ContentSafetyClient(
        endpoint=CONTENT_SAFETY_ENDPOINT, credential=credential
    )

    # =============================================================================
    # INSTANTIATE CLASSES
    # =============================================================================

    # Instantiate ContentSafety class
    content_safety = ContentSafety(content_safety_client, config)

    print("\n[TRACING] Initializing OpenTelemetry for distributed tracing...")
    # Instantiate OpenTelemetry class
    open_telemetry_client = OpenTelemetry(
        application_insights_connection_string=APPLICATION_INSIGHTS_CONNECTION_STRING,
        user_name=USER_NAME,
        user_role=USER_ROLE,
    )

    # Instantiate ModelRouter class
    model_router = ModelRouter(
        openai_client=openai_client,
        open_telemetry_client=open_telemetry_client,
        slm_deployment_name=SLM_MODEL_DEPLOYMENT_NAME,
        llm_deployment_name=LLM_MODEL_DEPLOYMENT_NAME,
        weather_endpoint=WEATHER_API_ENDPOINT,
        weather_api_key=WEATHER_API_KEY,
        exchange_rate_endpoint=EXCHANGE_RATE_API_ENDPOINT,
        exchange_rate_api_key=EXCHANGE_RATE_API_KEY,
        config=config,
    )

    try:
        user_message_text = "Help me with my refund of a broken TV."

        # Get available tools using ToolFunctions class
        print("\n" + "=" * 60)
        print("\n[TOOLS] Retrieving available tools for the agent...")
        tools = ToolFunctions.get_available_tools()

        # Input filtering (from Unit 3)
        print("\n[INPUT FILTER] Scanning user message...")

        is_safe = content_safety.is_text_safe(user_message_text)
        if not is_safe:
            print("User message blocked by Content Safety.")
            sys.exit(0)
        print("User message passed safety check.")

        print(
            "\n[SYSTEM INSTRUCTION] Building system instruction with grounding results..."
        )

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
        print("[TRACING] Starting trace with conversation ID generation...")
        print(
            "[TRACING] All spans (intent_classification, model_selection, model_execution, llm_generation) will be automatically recorded."
        )

        # Route to model (now with automatic tracing inside ModelRouter)
        reply, model_name, latency_ms, token_usage = model_router.route_to_model(
            user_question=user_message_text,
            messages=messages,
            tools=tools,
        )

        print(
            "[TRACING] Model routing complete. All spans have been recorded and exported."
        )

        # Ensure all spans are exported before the script exits (fail safe)
        print("\n[TRACING] Performing final flush and shutdown of tracer provider...")
        open_telemetry_client.flush_and_shutdown()
        print("[TRACING] All spans flushed and tracer shutdown complete.")

        if reply is None:
            print("ERROR: Failed to get response from model.")
            sys.exit(1)

        # Output filtering with tracing
        print("\n[OUTPUT FILTER] Scanning assistant response...")

        is_safe = content_safety.is_text_safe(reply)
        if not is_safe:
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

        # Display tracing information
        print("\n" + "=" * 50)
        print("TRACING INFORMATION:")
        print("=" * 50)
        print(f"Conversation ID: {open_telemetry_client.get_conversation_id()}")
        print(
            f"Tracer Provider: {'Enabled' if APPLICATION_INSIGHTS_CONNECTION_STRING else 'Disabled'}"
        )

        if open_telemetry_client.get_conversation_id():
            print(f"\n[TRACE VISUALIZATION] To view the trace waterfall diagram:")
            print(f"  1. Go to your Application Insights / Foundry Trace dashboard")
            print(
                f"  2. Search for conversation.id: {open_telemetry_client.get_conversation_id()}"
            )
            print(f"  3. You should see the following span hierarchy:")
            print(f"     └── model_routing (root span)")
            print(f"         ├── intent_classification")
            print(f"         ├── model_selection")
            print(f"         └── model_execution")
            print(f"             └── llm_generation or llm_with_tools")

        if APPLICATION_INSIGHTS_CONNECTION_STRING:
            print("\n[TRACE STATUS] ✓ Spans successfully sent to Application Insights.")
            print("[TRACE STATUS] ✓ All spans correlated with conversation.id")
            print(
                "[TRACE STATUS] ✓ Waterfall diagram available in Foundry Trace dashboard"
            )
        else:
            print("\n[TRACE STATUS] ✗ APPLICATION_INSIGHTS_CONNECTION_STRING not set.")
            print("[TRACE STATUS] ✗ Spans not exported to backend.")
            print(
                "[TRACE STATUS] ✗ To see traces, set APPLICATION_INSIGHTS_CONNECTION_STRING and run again."
            )

    except Exception as e:
        # Fail safe: Ensure spans are flushed even on error
        print(f"\n[ERROR] An unexpected error occurred: {e}")
        print("[TRACING] Attempting to flush spans before exit (fail safe)...")
        try:
            open_telemetry_client.flush_and_shutdown()
            print("[TRACING] Spans flushed successfully despite error.")
        except:
            print("[TRACING] Failed to flush spans during error handling.")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()

# =============================================================================
# UNIT 14 SUMMARY
# =============================================================================
# This script introduces Foundry Trace and OpenTelemetry debugging:
# 1. OPEN TELEMETRY: Industry standard for distributed tracing
# 2. SPANS: Individual units of work (LLM call, tool call, handoff, etc.)
# 3. SPAN ATTRIBUTES: Key-value pairs that record details about operations
