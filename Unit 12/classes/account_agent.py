# =============================================================================
# SUB-AGENTS
# =============================================================================
# Sub-agents are specialists that handle specific types of requests.
# They do NOT know about other agents - they just receive a task and return a result.


class AccountAgent:
    """Specialist agent that handles account management and profile updates."""

    def __init__(self, openai_client, llm_deployment_name):
        self.openai_client = openai_client
        self.llm_deployment_name = llm_deployment_name

    def get_system_instruction(self):
        """Build the system instruction for the account specialist."""
        return """
        [PERSONA]
        You are an Account Specialist for Contoso Corporation.
        You handle profile updates, password changes, and account settings.

        [BOUNDARIES]
        1. NEVER answer questions about products, refunds, or billing.
        2. NEVER share other users' account information.
        3. ALWAYS verify identity before making account changes.

        [PROCESS]
        1. Ask for verification (email or username) before any changes.
        2. Guide the user through updating their profile or settings.
        3. Confirm when changes have been completed successfully.
        4. Never perform destructive actions without explicit confirmation.
        """

    def process_request(self, user_message):
        """
        Process an account question and return the result.
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
            print(f"ERROR: AccountAgent failed: {error}")
            return "I encountered an error processing your account request."
