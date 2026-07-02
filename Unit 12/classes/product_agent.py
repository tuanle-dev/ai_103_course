# =============================================================================
# SUB-AGENTS
# =============================================================================
# Sub-agents are specialists that handle specific types of requests.
# They do NOT know about other agents - they just receive a task and return a result.


class ProductAgent:
    """Specialist agent that handles product questions and recommendations."""

    def __init__(self, openai_client, llm_deployment_name):
        self.openai_client = openai_client
        self.llm_deployment_name = llm_deployment_name

    def get_system_instruction(self):
        """Build the system instruction for the product specialist."""
        return """
        [PERSONA]
        You are a Product Specialist for Contoso Corporation.
        You know about product features, specifications, and comparisons.

        [BOUNDARIES]
        1. NEVER answer questions about refunds, billing, or account issues.
        2. NEVER share internal pricing or discount strategies.
        3. ALWAYS recommend products based on user needs, not just selling.

        [PROCESS]
        1. Understand what product information the user needs.
        2. Provide accurate product specifications and features.
        3. If asked to compare products, list pros and cons for each.
        4. Recommend the best product based on user requirements.
        """

    def process_request(self, user_message):
        """
        Process a product question and return the result.
        Returns a string response to send back to the manager.
        """
        system_message = {"role": "system", "content": self.get_system_instruction()}
        messages = [system_message, {"role": "user", "content": user_message}]

        try:
            response = self.openai_client.chat.completions.create(
                model=self.llm_deployment_name, messages=messages
            )
            return response.choices[0].message.content
        except Exception as error:
            print(f"ERROR: ProductAgent failed: {error}")
            return "I encountered an error processing your product question."
