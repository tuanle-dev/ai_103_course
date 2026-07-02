import json


class BillingAgent:
    """Handles billing questions including refunds, charges, invoices, and payment methods."""

    def __init__(self, openai_client, llm_deployment_name, user_name, config):
        self.name = config["billing_agent"]["name"]
        self.llm_deployment_name = llm_deployment_name
        self.user_name = user_name
        self.openai_client = openai_client
        self.max_tokens = config["llm"]["max_tokens"]
        self.temperature = config["llm"]["temperature"]
        self.top_p = config["llm"]["top_p"]

    def get_system_instruction(self):
        """Build the system instruction for the billing agent."""
        sections = []

        persona = f"""
        [PERSONA]
        You are {self.name}, a billing specialist for Contoso Corporation.
        You handle refunds, charges, invoices, and payment methods.
        You are helping a user named {self.user_name}.
        """
        sections.append(persona)

        boundaries = """
        [BOUNDARIES - HARD RULES]
        1. NEVER help with product troubleshooting - that's for the Support Agent.
        2. NEVER process refunds over $1000 without manager approval.
        3. ALWAYS ask for order number before processing refunds.
        """
        sections.append(boundaries)

        handoff_instructions = """
        [HANDOFF TOOL INSTRUCTIONS]
        You have a tool called 'handoff_to_support'.
        USE THIS TOOL WHEN:
        - User asks about product problems
        - User asks about shipping or delivery
        - User asks about warranties or returns (not refunds)

        When you hand off, summarize what the user needs in the 'reason' parameter.
        """
        sections.append(handoff_instructions)

        return "\n".join(sections)

    def get_handoff_tool(self):
        """Define the handoff tool for this agent."""
        return {
            "type": "function",
            "function": {
                "name": "handoff_to_support",
                "description": "Transfer the conversation back to the Support Agent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Why the conversation needs the support agent",
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
            print(f"ERROR: BillingAgent call failed: {error}")
            return f"I encountered an error: {error}", None

        assistant_message = response.choices[0].message

        # Check if the agent wants to hand off
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                if tool_call.function.name == "handoff_to_support":
                    arguments = json.loads(tool_call.function.arguments)
                    reason = arguments["reason"]
                    print(f"\n[HANDOFF] BillingAgent → SupportAgent. Reason: {reason}")

                    # Return handoff signal with reason and conversation history
                    updated_history = messages_history + [
                        {"role": "user", "content": user_message},
                        {
                            "role": "assistant",
                            "content": f"Transferring you to support because {reason}",
                        },
                    ]
                    return None, {
                        "handoff_to": "SupportAgent",
                        "reason": reason,
                        "conversation_history": updated_history,
                    }

        # No handoff - return normal response
        return assistant_message.content, None
