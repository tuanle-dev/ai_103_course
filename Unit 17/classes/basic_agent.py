class BasicAgent:
    """A basic agent that processes user messages and Azure AI Service responses to generate a reply using an LLM model. This agent does not have memory capabilities and treats each interaction independently."""

    def __init__(self, llm_model_client, llm_model_deployment_name):
        self.llm_model_client = llm_model_client
        self.llm_model_deployment_name = llm_model_deployment_name

    def process_message(
        self, user_message, system_instruction, azure_ai_service_response
    ):
        messages = [{"role": "system", "content": system_instruction}]

        messages.append(
            {
                "role": "system",
                "content": f"Azure AI Service response: {azure_ai_service_response}",
            }
        )

        messages.append({"role": "user", "content": user_message})

        try:
            response = self.llm_model_client.chat.completions.create(
                model=self.llm_model_deployment_name, messages=messages
            )
            assistant_reply = response.choices[0].message.content
        except Exception as error:
            print(f"ERROR: LLM call failed: {error}")
            return f"I encountered an error: {error}"

        messages.append({"role": "assistant", "content": assistant_reply})

        return assistant_reply
