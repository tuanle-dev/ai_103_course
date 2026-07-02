# =============================================================================
# LLM CALLS AGENT
# =============================================================================
# This class encapsulates LLM-related helper methods, following the style of RefundAgent.


class LLMAgent:
    """Agent that handles LLM-based tasks (weather, exchange rate, sentiment, etc)."""

    def __init__(self, openai_client, llm_deployment_name, config):
        self.openai_client = openai_client
        self.llm_deployment_name = llm_deployment_name
        self.max_tokens = config["llm"]["max_tokens"]
        self.temperature = config["llm"]["temperature"]
        self.top_p = config["llm"]["top_p"]

    async def call_llm(self, prompt: str) -> str:
        """
        Helper function to call LLM with proper authentication.
        Uses asyncio.to_thread to avoid blocking the event loop (for sync OpenAI client).
        """
        import asyncio

        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.llm_deployment_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"   ✗ LLM call failed: {e}")
            raise

    async def get_weather(self, city: str) -> str:
        """Use LLM to fetch weather information for a city."""
        print(f"[LLM TASK] Getting weather for {city}...")

        prompt = f"""
        You are a weather assistant. Provide current weather information for {city}.
        Include temperature in Fahrenheit, conditions (sunny/cloudy/rainy), and humidity percentage.
        Keep response under 50 words.
        """

        try:
            result = await self.call_llm(prompt)
            print(f"[LLM TASK] ✓ Completed: {result[:60]}...")
            return f"Weather in {city}: {result}"
        except Exception as e:
            error_msg = f"Error getting weather: {str(e)}"
            print(f"[LLM TASK] ✗ Failed: {error_msg}")
            return error_msg

    async def get_exchange_rate(self, from_curr: str, to_curr: str) -> str:
        """Use LLM to fetch exchange rate information."""
        print(f"[LLM TASK] Getting exchange rate {from_curr}→{to_curr}...")

        prompt = f"""
        You are a financial assistant. Provide the current exchange rate from {from_curr} to {to_curr}.
        Give the rate as a number (e.g., 1 USD = 0.85 EUR).
        Keep response under 30 words.
        """

        try:
            result = await self.call_llm(prompt)
            print(f"[LLM TASK] ✓ Completed: {result}")
            return f"Exchange rate: {result}"
        except Exception as e:
            error_msg = f"Error getting exchange rate: {str(e)}"
            print(f"[LLM TASK] ✗ Failed: {error_msg}")
            return error_msg

    async def analyze_sentiment(self, text: str) -> str:
        """Use LLM to analyze sentiment of text."""
        print(f"[LLM TASK] Analyzing sentiment of: '{text[:50]}...'")

        prompt = f"""
        Analyze the sentiment of this text: "{text}"
        
        Respond with ONLY JSON in this format:
        {{"sentiment": "positive/negative/neutral", "confidence": 0.0-1.0, "explanation": "brief explanation"}}
        """

        try:
            result = await self.call_llm(prompt)
            print(f"[LLM TASK] ✓ Completed sentiment analysis")
            return f"Sentiment analysis result: {result}"
        except Exception as e:
            error_msg = f"Error analyzing sentiment: {str(e)}"
            print(f"[LLM TASK] ✗ Failed: {error_msg}")
            return error_msg

    async def generate_response_to_sentiment(
        self, sentiment_analysis: str, user_text: str
    ) -> str:
        """Use LLM to generate a response based on sentiment analysis."""
        print(f"[LLM TASK] Generating response based on sentiment...")

        prompt = f"""
        User said: "{user_text}"
        Sentiment analysis: {sentiment_analysis}
        
        Generate an appropriate, empathetic response to the user.
        Match your tone to their sentiment (positive/negative/neutral).
        Keep response under 100 words.
        """

        try:
            result = await self.call_llm(prompt)
            print(f"[LLM TASK] ✓ Completed response generation")
            return f"Generated response: {result}"
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            print(f"[LLM TASK] ✗ Failed: {error_msg}")
            return error_msg
