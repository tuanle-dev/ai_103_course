class AgentWithMemory:
    """An agent that maintains short-term redis_memory across conversation turns."""

    def __init__(self, llm_model_client, llm_model_deployment_name, redis_memory):
        """
        Initialize the agent with a pre-instantiated redis_memory object.

        Args:
            redis_memory: An already instantiated RedisMemory instance
        """
        self.redis_memory = redis_memory
        self.llm_model_client = llm_model_client
        self.llm_model_deployment_name = llm_model_deployment_name

    def process_message(self, session_id, user_message, system_instruction):
        """Process a user message with session redis_memory."""
        messages = self.redis_memory.load_conversation(session_id)
        state = self.redis_memory.load_state(session_id)

        if not messages:
            # Start with system instruction if no prior messages
            messages = [{"role": "system", "content": system_instruction}]

        messages.append({"role": "user", "content": user_message})

        try:
            response = self.llm_model_client.chat.completions.create(
                model=self.llm_model_deployment_name, messages=messages
            )
            assistant_reply = response.choices[0].message.content
        except Exception as error:
            print(f"ERROR: LLM call failed: {error}")
            return f"I encountered an error: {error}", state

        messages.append({"role": "assistant", "content": assistant_reply})
        self.redis_memory.save_conversation(session_id, messages)
        self.redis_memory.refresh_ttl(session_id)

        return assistant_reply, state

    def update_state(self, session_id, state_updates):
        """Update session state."""
        current_state = self.redis_memory.load_state(session_id)
        current_state.update(state_updates)
        self.redis_memory.save_state(session_id, current_state)

    def clear_memory(self, session_id):
        """Clear all redis_memory for a session."""
        self.redis_memory.clear_session(session_id)
