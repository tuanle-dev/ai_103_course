# =============================================================================
# SUB-AGENTS
# =============================================================================
# Sub-agents are specialists that handle specific types of requests.
# They do NOT know about other agents - they just receive a task and return a result.


class RefundAgent:
    """Specialist agent that handles refund requests and eligibility checks."""

    def __init__(self, openai_client, llm_deployment_name):
        self.openai_client = openai_client
        self.llm_deployment_name = llm_deployment_name

    def get_system_instruction(self):
        """Build the system instruction for the refund specialist."""
        return """
        [PERSONA]
        You are a Refund Specialist for Contoso Corporation.
        Your only job is to process refund requests and check refund eligibility.

        [BOUNDARIES]
        1. NEVER answer questions about products, shipping, or account issues.
        2. ALWAYS ask for the order number before processing a refund.
        3. ONLY process refunds under $1000. Over $1000 requires manager approval.

        [PROCESS]
        1. Ask the user for their order number.
        2. Check if the order is eligible for refund (within 30 days, not damaged).
        3. Tell the user the refund amount and estimated processing time.
        4. If over $1000, explain that manager approval is needed.
        """

    def process_request(self, user_message):
        """
        Process a refund request and return the result.
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
            print(f"ERROR: RefundAgent failed: {error}")
            return "I encountered an error processing your refund request."
