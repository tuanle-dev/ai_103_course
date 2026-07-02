# =============================================================================
# MODEL ROUTING CLASS WITH OPEN TELEMETRY
# =============================================================================

import time
import uuid
from datetime import datetime
from opentelemetry.trace import Status, StatusCode, SpanKind

from classes.intent_classification import IntentClassifier
from classes.tool_functions import ToolFunctions


class ModelRouter:
    def __init__(
        self,
        openai_client,
        open_telemetry_client,
        slm_deployment_name,
        llm_deployment_name,
        weather_endpoint,
        weather_api_key,
        exchange_rate_endpoint,
        exchange_rate_api_key,
        config,
    ):
        self.openai_client = openai_client
        self.open_telemetry_client = open_telemetry_client
        self.slm_deployment_name = slm_deployment_name
        self.llm_deployment_name = llm_deployment_name
        self.weather_endpoint = weather_endpoint
        self.weather_api_key = weather_api_key
        self.exchange_rate_endpoint = exchange_rate_endpoint
        self.exchange_rate_api_key = exchange_rate_api_key
        self.config = config

        # Instantiate ToolFunctions class
        self.tool_functions = ToolFunctions(
            weather_endpoint=weather_endpoint,
            weather_api_key=weather_api_key,
            exchange_rate_endpoint=exchange_rate_endpoint,
            exchange_rate_api_key=exchange_rate_api_key,
            tool_call_timeout_seconds=config["tools"]["tool_call_timeout_seconds"],
            max_retries=config["tools"]["max_retries"],
            backoff_seconds=config["tools"]["backoff_seconds"],
            openai_client=openai_client,
        )

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
        tools,
    ):
        """
        Route question to appropriate model based on intent classification.
        Returns: (response_text, model_name, latency_ms, token_usage)

        Uses reusable span creation with conversation correlation.
        """

        # Setup tracing
        self.conversation_id = str(uuid.uuid4())
        self.open_telemetry_client.setup_tracing()
        self.open_telemetry_client.set_conversation_id(self.conversation_id)

        # If Open Telemetry is not available, run without tracing
        if not self.open_telemetry_client or not self.open_telemetry_client.tracer:
            return self._route_to_model_without_tracing(user_question, messages, tools)

        conversation_start = datetime.now().isoformat()
        self.conversation_start = conversation_start

        # Use the reusable create_span context manager for the main routing span
        with self.open_telemetry_client.create_span(
            "model_routing",
            kind=SpanKind.INTERNAL,  # Options include: INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER
            attributes={
                "conversation.start_time": self.conversation_start,  # Add start time
                "routing.user_question_length": len(user_question),
                "routing.user_question_preview": user_question[:200],
                "routing.timestamp": datetime.now().isoformat(),
            },
        ) as root_span:

            # ========== INTENT CLASSIFICATION SPAN ==========
            with self.open_telemetry_client.create_span(
                "intent_classification",
                attributes={
                    "intent.user_question": user_question[:200],
                },
            ) as intent_span:

                use_slm_classifier = self.config["intent_classifier"][
                    "use_slm_classifier"
                ]

                # Record which classifier method is being used
                intent_span.set_attribute(
                    "intent.classifier_method",
                    "slm" if use_slm_classifier else "keyword",
                )

                classification_start = time.time()

                if use_slm_classifier:
                    print(
                        "\n[INTENT CLASSIFIER] Using SLM (Phi-4) for classification..."
                    )
                    intent = self.intent_classifier.classify_intent_via_slm(
                        user_question
                    )
                else:
                    print("\n[INTENT CLASSIFIER] Using keyword-based classification...")
                    intent = self.intent_classifier.classify_intent(user_question)

                classification_latency = (time.time() - classification_start) * 1000

                # Record classification results
                intent_span.set_attribute("intent.result", intent.upper())
                intent_span.set_attribute(
                    "intent.classification_latency_ms", classification_latency
                )

                print(f"\n[INTENT CLASSIFIER] Question classified as: {intent.upper()}")

            # ========== MODEL SELECTION SPAN ==========
            with self.open_telemetry_client.create_span(
                "model_selection"
            ) as selection_span:
                selection_span.set_attribute("model_selection.intent", intent.upper())

                if intent == "simple":
                    print("[ROUTING] Sending to Phi-4 (SLM) - faster and cheaper")
                    model_name = "Phi-4 (SLM)"
                    deployment = self.slm_deployment_name
                    max_past_messages = self.config["slm"]["max_past_messages"]
                    max_tokens = self.config["slm"]["max_tokens"]
                    temperature = self.config["slm"]["temperature"]
                    top_p = self.config["slm"]["top_p"]
                    use_tools = False
                else:
                    print(
                        "[ROUTING] Sending to GPT-4.1-Mini (LLM) - more capable for complex tasks"
                    )
                    model_name = "GPT-4.1-Mini (LLM)"
                    deployment = self.llm_deployment_name
                    max_past_messages = self.config["llm"]["max_past_messages"]
                    max_tokens = self.config["llm"]["max_tokens"]
                    temperature = self.config["llm"]["temperature"]
                    top_p = self.config["llm"]["top_p"]
                    use_tools = True

                # Record selection attributes
                selection_span.set_attribute(
                    "model_selection.selected_model", model_name
                )
                selection_span.set_attribute(
                    "model_selection.deployment_name", deployment
                )
                selection_span.set_attribute(
                    "model_selection.max_past_messages", max_past_messages
                )
                selection_span.set_attribute("model_selection.max_tokens", max_tokens)
                selection_span.set_attribute("model_selection.temperature", temperature)
                selection_span.set_attribute("model_selection.use_tools", use_tools)

            # Trim message history
            original_msg_count = len(messages)
            messages = messages[-max_past_messages:]

            # ========== MODEL EXECUTION SPAN ==========
            with self.open_telemetry_client.create_span(
                "model_execution",
                attributes={
                    "model_execution.model_name": model_name,
                    "model_execution.deployment": deployment,
                    "model_execution.messages_original_count": original_msg_count,
                    "model_execution.messages_used_count": len(messages),
                    "model_execution.max_tokens": max_tokens,
                    "model_execution.temperature": temperature,
                },
            ) as execution_span:

                start_time = time.time()

                try:
                    if not use_tools or intent == "simple":
                        # Simple LLM call without tools
                        with self.open_telemetry_client.create_span(
                            "llm_generation"
                        ) as llm_span:
                            llm_span.set_attribute("llm.model", model_name)
                            llm_span.set_attribute("llm.deployment", deployment)
                            llm_span.set_attribute("llm.use_tools", False)

                            response = self.openai_client.chat.completions.create(
                                model=deployment,
                                messages=messages,
                                max_tokens=max_tokens,
                                temperature=temperature,
                                top_p=top_p,
                            )

                            # Record LLM specific attributes
                            if hasattr(response, "usage") and response.usage:
                                llm_span.set_attribute(
                                    "llm.prompt_tokens", response.usage.prompt_tokens
                                )
                                llm_span.set_attribute(
                                    "llm.completion_tokens",
                                    response.usage.completion_tokens,
                                )
                                llm_span.set_attribute(
                                    "llm.total_tokens", response.usage.total_tokens
                                )

                    else:
                        # Complex call with tool support
                        with self.open_telemetry_client.create_span(
                            "llm_with_tools"
                        ) as tools_span:
                            tools_span.set_attribute("llm.model", model_name)
                            tools_span.set_attribute("llm.deployment", deployment)
                            tools_span.set_attribute("llm.use_tools", True)
                            tools_span.set_attribute(
                                "llm.available_tools_count", len(tools) if tools else 0
                            )

                            if tools:
                                tools_span.set_attribute(
                                    "llm.available_tools",
                                    str(
                                        [
                                            t.get("function", {}).get("name")
                                            for t in tools
                                        ]
                                    ),
                                )

                            response = self.tool_functions.call_llm_with_possible_tools(
                                model_deployment_name=deployment,
                                messages=messages,
                                max_tokens=max_tokens,
                                temperature=temperature,
                                top_p=top_p,
                                tools=tools,
                            )

                            # Record LLM specific attributes
                            if hasattr(response, "usage") and response.usage:
                                tools_span.set_attribute(
                                    "llm.prompt_tokens", response.usage.prompt_tokens
                                )
                                tools_span.set_attribute(
                                    "llm.completion_tokens",
                                    response.usage.completion_tokens,
                                )
                                tools_span.set_attribute(
                                    "llm.total_tokens", response.usage.total_tokens
                                )

                            # Check if tool calls were made
                            if (
                                hasattr(response.choices[0].message, "tool_calls")
                                and response.choices[0].message.tool_calls
                            ):
                                tools_span.set_attribute(
                                    "llm.tool_calls_count",
                                    len(response.choices[0].message.tool_calls),
                                )
                                tools_span.set_attribute("llm.tool_calls_made", True)

                    latency_ms = (time.time() - start_time) * 1000
                    reply = response.choices[0].message.content

                    # Record execution results
                    execution_span.set_attribute(
                        "model_execution.latency_ms", latency_ms
                    )
                    execution_span.set_attribute(
                        "model_execution.response_length", len(reply) if reply else 0
                    )
                    execution_span.set_attribute("model_execution.success", True)

                    token_usage = None
                    if hasattr(response, "usage") and response.usage:
                        token_usage = {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens,
                        }
                        execution_span.set_attribute(
                            "model_execution.total_tokens", token_usage["total_tokens"]
                        )

                    # Record routing decision in root span
                    root_span.set_attribute("routing.success", True)
                    root_span.set_attribute("routing.total_latency_ms", latency_ms)

                    return reply, model_name, latency_ms, token_usage

                except Exception as error:
                    # Record error in spans (create_span context manager auto-records)
                    # But we still need to set status for the execution span
                    execution_span.set_status(Status(StatusCode.ERROR, str(error)))
                    execution_span.record_exception(error)
                    raise

            root_span.set_attribute("conversation.end_time", datetime.now().isoformat())

    def _route_to_model_without_tracing(self, user_question, messages, tools):
        """
        Fallback method when Open Telemetry is not available.
        Original routing logic without any tracing.
        """
        use_slm_classifier = self.config["intent_classifier"]["use_slm_classifier"]

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
            max_past_messages = self.config["slm"]["max_past_messages"]
            max_tokens = self.config["slm"]["max_tokens"]
            temperature = self.config["slm"]["temperature"]
            top_p = self.config["slm"]["top_p"]
            use_tools = False
        else:
            print(
                "[ROUTING] Sending to GPT-4.1-Mini (LLM) - more capable for complex tasks"
            )
            model_name = "GPT-4.1-Mini (LLM)"
            deployment = self.llm_deployment_name
            max_past_messages = self.config["llm"]["max_past_messages"]
            max_tokens = self.config["llm"]["max_tokens"]
            temperature = self.config["llm"]["temperature"]
            top_p = self.config["llm"]["top_p"]
            use_tools = True

        # Trim message history
        messages = messages[-max_past_messages:]

        start_time = time.time()

        try:
            if not use_tools or intent == "simple":
                response = self.openai_client.chat.completions.create(
                    model=deployment,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )
            else:
                response = self.tool_functions.call_llm_with_possible_tools(
                    model_deployment_name=deployment,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    tools=tools,
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

        except Exception as error:
            print(f"[ERROR] Model routing failed: {error}")
            raise
