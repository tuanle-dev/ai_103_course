# =============================================================================
# MODEL ROUTING
# =============================================================================

import time
from functions.intent_classification import classify_intent, classify_intent_via_slm


def route_to_model(
    openai_client,
    user_question,
    messages,
    use_slm_classifier,
    intent_classifier_max_tokens,
    intent_classifier_temperature,
    intent_classifier_top_p,
    llm_deployment_name,
    llm_max_past_messages,
    llm_max_tokens,
    llm_temperature,
    llm_top_p,
    slm_deployment_name,
    slm_max_past_messages,
    slm_max_tokens,
    slm_temperature,
    slm_top_p,
):
    """
    Route question to appropriate model based on intent classification.
    Returns: (response_text, model_name, latency_ms, token_usage)
    """
    if use_slm_classifier:
        print("\n[INTENT CLASSIFIER] Using SLM (Phi-4) for classification...")
        intent = classify_intent_via_slm(
            openai_client,
            slm_deployment_name,
            user_question,
            intent_classifier_max_tokens,
            intent_classifier_temperature,
            intent_classifier_top_p,
        )
    else:
        print("\n[INTENT CLASSIFIER] Using keyword-based classification...")
        intent = classify_intent(user_question)

    print(f"\n[INTENT CLASSIFIER] Question classified as: {intent.upper()}")

    if intent == "simple":
        print("[ROUTING] Sending to Phi-4 (SLM) - faster and cheaper")
        model_name = "Phi-4 (SLM)"
        deployment = slm_deployment_name
        max_past_messages = slm_max_past_messages
        max_tokens = slm_max_tokens
        temperature = slm_temperature
        top_p = slm_top_p
    else:
        print(
            "[ROUTING] Sending to GPT-4.1-Mini (LLM) - more capable for complex tasks"
        )
        model_name = "GPT-4.1-Mini (LLM)"
        deployment = llm_deployment_name
        max_past_messages = llm_max_past_messages
        max_tokens = llm_max_tokens
        temperature = llm_temperature
        top_p = llm_top_p

    messages = messages[
        -max_past_messages:
    ]  # Keep only the most recent messages within the limit

    start_time = time.time()

    response = openai_client.chat.completions.create(
        model=deployment,
        messages=messages,
        max_tokens=max_tokens,  # Set the maximum length of the response
        temperature=temperature,  # Control the creativity of the response
        top_p=top_p,  # Control the diversity of the token selection
    )

    latency_ms = (time.time() - start_time) * 1000
    reply = response.choices[0].message.content

    token_usage = None
    if hasattr(response, "usage") and response.usage:
        token_usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return reply, model_name, latency_ms, token_usage
