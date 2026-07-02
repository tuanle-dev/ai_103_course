class AgentWithMemory:
    """An agent that maintains short-term redis_memory across conversation turns."""

    def __init__(
        self, llm_model_client, llm_model_deployment_name, redis_memory, cosmos_memory
    ):
        """
        Initialize the agent with a pre-instantiated redis_memory object.

        Args:
            redis_memory: An already instantiated RedisMemory instance
        """
        self.redis_memory = redis_memory
        self.cosmos_memory = cosmos_memory
        self.llm_model_client = llm_model_client
        self.llm_model_deployment_name = llm_model_deployment_name

    def _get_personalized_system_instruction(
        self, system_instruction, user_preferences
    ):
        """Augment system instruction with user preferences."""
        temp_unit = user_preferences["temp_unit"]
        unit_display = "Celsius (°C)" if temp_unit == "celsius" else "Fahrenheit (°F)"

        system_instruction_with_preferences = system_instruction + f"""
        [USER PREFERENCES - LEARNED FROM PAST SESSIONS]
        - Temperature unit preference: {unit_display}
        - Default address: {user_preferences['default_address']}
        - Past orders count: {len(user_preferences['past_orders'])}
        - Lanaguage preference: {user_preferences['language']}

        Use these preferences to personalize your responses. For example, report weather
        in the user's preferred temperature unit. Ask before changing preferences.

        The language preference is the language that I need returned to the user in. 
        Always respond in that language if specified. 
        You can safely ignore the language of the user message and respond in the language 
        specified in the preferences.
        """

        return system_instruction_with_preferences

    def _get_default_preferences(self):
        """Return a default preferences dictionary."""
        return {
            "temp_unit": "celsius",
            "default_address": None,
            "past_orders": [],
            "language": "English",
        }

    def process_message(self, session_id, user_id, user_message, system_instruction):
        """Process a user message with hybrid memory."""
        messages = self.redis_memory.load_conversation(session_id)
        state = self.redis_memory.load_state(session_id)

        user_prefs = self.cosmos_memory.get_user_profile(user_id)
        if user_prefs is None:
            user_prefs = self._get_default_preferences()
            self.cosmos_memory.save_user_profile(user_id, user_prefs)

        if not messages:
            # Start with system instruction if no prior messages
            system_instruction = self._get_personalized_system_instruction(
                system_instruction, user_prefs
            )
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

        return assistant_reply, state, user_prefs

    def update_state(self, session_id, state_updates):
        """Update session state."""
        current_state = self.redis_memory.load_state(session_id)
        current_state.update(state_updates)
        self.redis_memory.save_state(session_id, current_state)

    def clear_memory(self, session_id):
        """Clear all redis_memory for a session."""
        self.redis_memory.clear_session(session_id)

    def update_user_preference(self, user_id, key, value):
        """Update a user's long-term preference."""
        return self.cosmos_memory.update_preference(user_id, key, value)
