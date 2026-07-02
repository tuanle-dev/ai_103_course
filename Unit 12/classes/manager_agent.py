# =============================================================================
# MANAGER AGENT
# =============================================================================
# The manager agent receives all user messages, identifies intent, and delegates
# to the appropriate sub-agent. It never answers directly - its only job is routing.

import json


class ManagerAgent:
    """
    The Manager (Magentic) pattern agent.
    Receives user requests and delegates to specialized sub-agents.
    Does not answer questions directly - only routes and synthesizes responses.
    """

    def __init__(
        self,
        openai_client,
        llm_deployment_name,
        refund_agent,
        product_agent,
        account_agent,
        user_name,
    ):
        self.openai_client = openai_client
        self.llm_deployment_name = llm_deployment_name
        self.refund_agent = refund_agent
        self.product_agent = product_agent
        self.account_agent = account_agent
        self.user_name = user_name

        # Routing metrics - tracks which sub-agent handles how many requests
        self.metrics = {
            "refund_agent_requests": 0,
            "product_agent_requests": 0,
            "account_agent_requests": 0,
            "unable_to_route": 0,
        }

    def get_system_instruction(self):
        """Build the system instruction for the manager agent."""
        return f"""
        [PERSONA]
        You are a Manager Agent for Contoso Corporation.
        You coordinate between specialist agents. You do NOT answer questions directly.

        [BOUNDARIES - CRITICAL]
        1. NEVER answer user questions directly. ALWAYS delegate to a specialist.
        2. You have three specialists: RefundAgent, ProductAgent, AccountAgent.
        3. Your only job is to identify which specialist should handle the request.

        [HANDOFF RULES]
        - Use delegate_to_refund when user asks about: refund, return money, reimbursement
        - Use delegate_to_product when user asks about: product features, specifications
        - Use delegate_to_account when user asks about: password, profile, account settings

        [RESPONSE FORMAT]
        After receiving the specialist's response, present it to the user exactly as given.
        Do not modify or summarize the specialist's answer.

        You are helping user: {self.user_name}
        """

    def delegate_to_refund(self, user_message):
        """Delegate a refund request to the RefundAgent."""
        print("[MANAGER] Delegating to RefundAgent")
        self.metrics["refund_agent_requests"] += 1
        return self.refund_agent.process_request(user_message)

    def delegate_to_product(self, user_message):
        """Delegate a product question to the ProductAgent."""
        print("[MANAGER] Delegating to ProductAgent")
        self.metrics["product_agent_requests"] += 1
        return self.product_agent.process_request(user_message)

    def delegate_to_account(self, user_message):
        """Delegate an account question to the AccountAgent."""
        print("[MANAGER] Delegating to AccountAgent")
        self.metrics["account_agent_requests"] += 1
        return self.account_agent.process_request(user_message)

    def process_message(self, user_message):
        """
        Process a user message by:
        1. Classifying the intent (which specialist is needed)
        2. Delegating to the appropriate specialist
        3. Returning the specialist's response
        """
        # Build delegation tools for the manager LLM
        delegation_tools = [
            {
                "type": "function",
                "function": {
                    "name": "delegate_to_refund",
                    "description": "Send request to Refund Agent for refunds or returns",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_message": {
                                "type": "string",
                                "description": "The user's original request",
                            }
                        },
                        "required": ["user_message"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delegate_to_product",
                    "description": "Send request to Product Agent for product questions",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_message": {
                                "type": "string",
                                "description": "The user's original request",
                            }
                        },
                        "required": ["user_message"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delegate_to_account",
                    "description": "Send request to Account Agent for account help",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_message": {
                                "type": "string",
                                "description": "The user's original request",
                            }
                        },
                        "required": ["user_message"],
                    },
                },
            },
        ]

        # Build system instruction and messages
        system_instruction = self.get_system_instruction()
        system_message = {"role": "system", "content": system_instruction}
        messages = [system_message, {"role": "user", "content": user_message}]

        # Call LLM to determine which specialist should handle the request
        try:
            response = self.openai_client.chat.completions.create(
                model=self.llm_deployment_name,
                messages=messages,
                tools=delegation_tools,
                tool_choice="auto",
            )
        except Exception as error:
            print(f"ERROR: ManagerAgent call failed: {error}")
            self.metrics["unable_to_route"] += 1
            return "I encountered an error processing your request."

        assistant_message = response.choices[0].message

        # Check which tool the manager wants to call
        if assistant_message.tool_calls:
            tool_call = assistant_message.tool_calls[0]
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            user_message_text = arguments.get("user_message", user_message)

            # Route to the appropriate specialist
            if tool_name == "delegate_to_refund":
                specialist_response = self.delegate_to_refund(user_message_text)
            elif tool_name == "delegate_to_product":
                specialist_response = self.delegate_to_product(user_message_text)
            elif tool_name == "delegate_to_account":
                specialist_response = self.delegate_to_account(user_message_text)
            else:
                specialist_response = (
                    "I cannot determine which specialist can help with your request."
                )
                self.metrics["unable_to_route"] += 1

            return specialist_response

        # No tool call - manager couldn't determine intent
        self.metrics["unable_to_route"] += 1
        return (
            "I'm not sure which specialist can help with that. "
            "Please ask about refunds, products, or account issues."
        )

    def get_metrics(self):
        """Return routing metrics for monitoring."""
        total = sum(
            [
                self.metrics["refund_agent_requests"],
                self.metrics["product_agent_requests"],
                self.metrics["account_agent_requests"],
                self.metrics["unable_to_route"],
            ]
        )
        return {
            "total_requests": total,
            "refund": self.metrics["refund_agent_requests"],
            "product": self.metrics["product_agent_requests"],
            "account": self.metrics["account_agent_requests"],
            "unable_to_route": self.metrics["unable_to_route"],
        }
