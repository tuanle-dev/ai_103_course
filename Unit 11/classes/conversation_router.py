import json
from datetime import datetime


class ConversationRouter:
    """
    Routes messages to the appropriate agent and manages handoffs between agents.
    Maintains conversation history across handoffs.
    """

    def __init__(self, content_safety, support_agent, billing_agent, user_name):
        self.content_safety = content_safety
        self.support_agent = support_agent
        self.billing_agent = billing_agent
        self.current_agent = "SupportAgent"  # Start with support agent
        self.conversation_history = []  # Stores messages from the entire conversation
        self.user_name = user_name

    def process_message(self, user_message):
        """
        Process a user message using the currently active agent.
        If a handoff occurs, switch agents and continue the conversation.
        """
        # Content Safety input filter (from Unit 3)
        if not self.content_safety.is_text_safe(user_message):
            return "I cannot process that request due to content safety concerns."

        print(f"\n[ROUTER] Current agent: {self.current_agent}")
        print(f"[ROUTER] User message: {user_message[:100]}...")

        # Route to the correct agent
        if self.current_agent == "SupportAgent":
            response, handoff = self.support_agent.process_message(
                user_message, self.conversation_history
            )
        else:
            response, handoff = self.billing_agent.process_message(
                user_message, self.conversation_history
            )

        # Handle handoff if requested
        if handoff:
            # Switch to the requested agent
            self.current_agent = handoff["handoff_to"]
            self.conversation_history = handoff["conversation_history"]
            print(f"[ROUTER] Handoff complete. New agent: {self.current_agent}")

            # Process the same message with the new agent
            return self.process_message(user_message)

        # No handoff - store the conversation and return response
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": response})

        return response
