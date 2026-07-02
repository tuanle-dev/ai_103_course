# =============================================================================
# MODEL ROUTING CLASS
# =============================================================================

import time
from classes.intent_classification import IntentClassifier


class ModelRouter:
    def __init__(
        self,
        openai_client,
        slm_deployment_name,
        llm_deployment_name,
        mcp_client,
        config,
    ):
        self.openai_client = openai_client
        self.config = config
        self.slm_deployment_name = slm_deployment_name
        self.llm_deployment_name = llm_deployment_name
        self.mcp_client = mcp_client

        # Instantiate IntentClassifier class
        self.intent_classifier = IntentClassifier(
            openai_client=openai_client,
            slm_deployment_name=slm_deployment_name,
            max_tokens=config["intent_classifier"]["max_tokens"],
            temperature=config["intent_classifier"]["temperature"],
            top_p=config["intent_classifier"]["top_p"],
        )

    def route_to_model(
        self,
        user_question,
        messages,
    ):
        """
        Route question to appropriate model based on intent classification.
        Returns: (response_text, model_name, latency_ms, token_usage)
        """
        cfg = self.config
        use_slm_classifier = cfg["intent_classifier"]["use_slm_classifier"]
        if use_slm_classifier:
            print("\n[INTENT CLASSIFIER] Using SLM (Phi-4) for classification...")
            intent = self.intent_classifier.classify_intent_via_slm(user_question)
        else:
            print("\n[INTENT CLASSIFIER] Using keyword-based classification...")
            intent = self.intent_classifier.classify_intent(user_question)

        print(f"\n[INTENT CLASSIFIER] Question classified as: {intent.upper()}")

        if intent == "simple":
            print("[ROUTING] Sending to Phi-4 (SLM) - faster and cheaper")
            model_name = "Phi-4 (SLM)"
            deployment = self.slm_deployment_name
            max_past_messages = cfg["slm"]["max_past_messages"]
            max_tokens = cfg["slm"]["max_tokens"]
            temperature = cfg["slm"]["temperature"]
            top_p = cfg["slm"]["top_p"]
        else:
            print(
                "[ROUTING] Sending to GPT-4.1-Mini (LLM) - more capable for complex tasks"
            )
            model_name = "GPT-4.1-Mini (LLM)"
            deployment = self.llm_deployment_name
            max_past_messages = cfg["llm"]["max_past_messages"]
            max_tokens = cfg["llm"]["max_tokens"]
            temperature = cfg["llm"]["temperature"]
            top_p = cfg["llm"]["top_p"]

        messages = messages[-max_past_messages:]

        start_time = time.time()

        if intent == "simple":
            response = self.openai_client.chat.completions.create(
                model=deployment,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
        else:
            response = self.mcp_client.call_llm_with_possible_tools(
                messages=messages,
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
