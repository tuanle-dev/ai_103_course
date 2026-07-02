import json


class SupportAgent:
    """Handles general support questions about products, policies, and troubleshooting."""

    def __init__(self, openai_client, llm_deployment_name, user_name, config):
        self.name = config["support_agent"]["name"]
        self.llm_deployment_name = llm_deployment_name
        self.user_name = user_name
        self.openai_client = openai_client
        self.max_tokens = config["llm"]["max_tokens"]
        self.temperature = config["llm"]["temperature"]
        self.top_p = config["llm"]["top_p"]

    def get_system_instruction(self):
        """Build the system instruction for the support agent."""
        sections = []

        persona = f"""
        [PERSONA]
        You are {self.name}, a customer support specialist for Contoso Corporation.
        You are helpful, patient, and knowledgeable about products and policies.
        You are helping a user named {self.user_name}.
        """
        sections.append(persona)

        boundaries = """
        [BOUNDARIES - HARD RULES]
        1. NEVER process refunds or billing changes - that's for the Billing Agent.
        2. NEVER share internal company prices or profit margins.
        3. ALWAYS hand off to the Billing Agent when asked about refunds or charges.
        """
        sections.append(boundaries)

        handoff_instructions = """
        [HANDOFF TOOL INSTRUCTIONS]
        You have a tool called 'handoff_to_billing'.
        USE THIS TOOL WHEN:
        - User asks for a refund
        - User asks about billing or charges
        - User asks to change payment method
        - User asks about invoice or receipt

        When you hand off, summarize what the user needs in the 'reason' parameter.
        After handing off, the Billing Agent will take over the conversation.
        """
        sections.append(handoff_instructions)

        return "\n".join(sections)

    def get_handoff_tool(self):
        """Define the handoff tool for this agent."""
        return {
            "type": "function",
            "function": {
                "name": "handoff_to_billing",
                "description": "Transfer the conversation to the Billing Agent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Why the conversation needs the billing agent",
                        }
                    },
                    "required": ["reason"],
                },
            },
        }

    def process_message(self, user_message, messages_history=None):
        """
        Process a user message and return the agent's response.
        If the agent hands off, returns a special handoff signal.
        """
        if messages_history is None:
            messages_history = []

        # Build system instruction
        system_instruction = self.get_system_instruction()
        system_message = {"role": "system", "content": system_instruction}

        # Build messages array
        messages = [system_message] + messages_history
        messages.append({"role": "user", "content": user_message})

        # Define handoff tool
        handoff_tool = self.get_handoff_tool()

        # Call LLM with handoff tool available
        try:
            response = self.openai_client.chat.completions.create(
                model=self.llm_deployment_name,
                messages=messages,
                tools=[handoff_tool],
                tool_choice="auto",
            )
        except Exception as error:
            print(f"ERROR: SupportAgent call failed: {error}")
            return f"I encountered an error: {error}", None

        assistant_message = response.choices[0].message

        # Check if the agent wants to hand off
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                if tool_call.function.name == "handoff_to_billing":
                    arguments = json.loads(tool_call.function.arguments)
                    reason = arguments["reason"]
                    print(f"\n[HANDOFF] SupportAgent → BillingAgent. Reason: {reason}")

                    # Return handoff signal with reason and conversation history
                    updated_history = messages_history + [
                        {"role": "user", "content": user_message},
                        {
                            "role": "assistant",
                            "content": f"Transferring you to billing because {reason}",
                        },
                    ]
                    return None, {
                        "handoff_to": "BillingAgent",
                        "reason": reason,
                        "conversation_history": updated_history,
                    }

        # No handoff - return normal response
        return assistant_message.content, None
