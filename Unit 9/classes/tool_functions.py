# =============================================================================
# TOOL FUNCTIONS CLASS
# =============================================================================

import time
import json
import requests


class ToolFunctions:
    def __init__(
        self,
        weather_endpoint,
        weather_api_key,
        exchange_rate_endpoint,
        exchange_rate_api_key,
        tool_call_timeout_seconds,
        max_retries,
        backoff_seconds,
        openai_client,
    ):
        self.weather_endpoint = weather_endpoint
        self.weather_api_key = weather_api_key
        self.exchange_rate_endpoint = exchange_rate_endpoint
        self.exchange_rate_api_key = exchange_rate_api_key
        self.tool_call_timeout_seconds = tool_call_timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.openai_client = openai_client

    @staticmethod
    def get_available_tools():
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_current_weather",
                    "description": "Get the current weather for a specific city",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "The city name (e.g., Seattle, London, Tokyo)",
                            },
                            "unit": {
                                "type": "string",
                                "enum": ["celsius", "fahrenheit"],
                                "description": "Temperature unit - celsius or fahrenheit",
                            },
                        },
                        "required": ["city"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_exchange_rate",
                    "description": "Get the current exchange rate between two currencies",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "from_currency": {
                                "type": "string",
                                "description": "Source currency code (e.g., USD, EUR, JPY)",
                            },
                            "to_currency": {
                                "type": "string",
                                "description": "Target currency code (e.g., USD, EUR, JPY)",
                            },
                        },
                        "required": ["from_currency", "to_currency"],
                    },
                },
            },
        ]
        return tools

    def call_weather_api(self, city, unit):
        params = {
            "q": city,
            "appid": self.weather_api_key,
        }
        try:
            response = requests.get(
                self.weather_endpoint,
                params=params,
                timeout=self.tool_call_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            temp = data["main"]["temp"]
            description = data["weather"][0]["description"]
            humidity = data["main"]["humidity"]
            city_name = data["name"]
            country = data["sys"]["country"]
            unit_symbol = "°C" if unit == "celsius" else "°F"
            if unit == "celsius":
                # convert from Kelvin to Celsius
                temp = temp - 273.15
            return (
                f"Weather in {city_name}, {country}: {temp}{unit_symbol}, "
                f"{description}. Humidity: {humidity}%"
            )
        except requests.exceptions.Timeout:
            return (
                f"ERROR: Weather API request timed out after "
                f"{self.tool_call_timeout_seconds} seconds."
            )
        except requests.exceptions.RequestException as error:
            return f"ERROR: Weather API request failed: {error}"

    def call_exchange_rate_api(self, from_currency, to_currency):
        url = f"{self.exchange_rate_endpoint}/{self.exchange_rate_api_key}/latest/{from_currency}"
        try:
            response = requests.get(url, timeout=self.tool_call_timeout_seconds)
            response.raise_for_status()
            data = response.json()
            if data.get("result") != "success":
                return (
                    f"ERROR: Exchange rate API error: "
                    f"{data.get('error-type', 'Unknown error')}"
                )
            rate = data["conversion_rates"].get(to_currency.upper())
            if rate is None:
                return (
                    f"ERROR: Currency '{to_currency}' not found. "
                    "Available currencies vary by API."
                )
            return (
                f"Exchange rate: 1 {from_currency.upper()} = "
                f"{rate} {to_currency.upper()}"
            )
        except requests.exceptions.Timeout:
            return (
                f"ERROR: Exchange rate API request timed out after "
                f"{self.tool_call_timeout_seconds} seconds."
            )
        except requests.exceptions.RequestException as error:
            return f"ERROR: Exchange rate API request failed: {error}"

    def execute_tool(self, tool_name, tool_arguments):
        print(
            f"\n[TOOL EXECUTION] Calling '{tool_name}' with arguments: {tool_arguments}"
        )
        if tool_name == "get_current_weather":
            city = tool_arguments.get("city")
            unit = tool_arguments.get("unit", "celsius")
            return self.call_weather_api(city, unit)
        if tool_name == "get_exchange_rate":
            from_currency = tool_arguments.get("from_currency")
            to_currency = tool_arguments.get("to_currency")
            return self.call_exchange_rate_api(from_currency, to_currency)
        return f"ERROR: Unknown tool '{tool_name}'"

    def execute_tool_with_retry(self, tool_name, tool_arguments):
        last_error = None
        for attempt in range(self.max_retries):
            result = self.execute_tool(tool_name, tool_arguments)
            if not result.startswith("ERROR:"):
                if attempt > 0:
                    print(f"[TOOL EXECUTION] Retry {attempt} succeeded.")
                return result
            last_error = result
            wait_time = self.backoff_seconds * (2**attempt)
            if attempt < self.max_retries - 1:
                print(
                    f"[TOOL EXECUTION] Attempt {attempt + 1} failed. "
                    f"Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
        return (
            f"ERROR: All {self.max_retries} attempts failed. Last error: {last_error}"
        )

    def call_llm_with_possible_tools(
        self,
        model_deployment_name,
        messages,
        max_tokens,
        temperature,
        top_p,
        tools,
    ):
        print(
            f"\n[LLM CALL] Sending to {model_deployment_name} with tools available..."
        )
        start_time = time.time()
        response = self.openai_client.chat.completions.create(
            model=model_deployment_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            tools=tools,
            tool_choice="auto",  # options are: "none", "auto", or "all"
        )
        latency_ms = (time.time() - start_time) * 1000
        print(f"[LLM CALL] Completed in {latency_ms:.2f}ms")
        reply = response.choices[0].message
        if reply.tool_calls:
            tool_count = len(reply.tool_calls)
            print(f"\n[TOOL CALLING] LLM requested {tool_count} tool call(s)")
            messages.append(reply)
            for tool_call in reply.tool_calls:
                tool_name = tool_call.function.name
                tool_arguments = json.loads(tool_call.function.arguments)
                tool_call_id = tool_call.id
                tool_result = self.execute_tool_with_retry(tool_name, tool_arguments)
                tool_response = {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": tool_result,
                }
                messages.append(tool_response)
                preview = (
                    tool_result[:100] + "..." if len(tool_result) > 100 else tool_result
                )
                print(f"[TOOL CALLING] Tool '{tool_name}' returned: {preview}")
            print("\n[LLM CALL] Sending tool results back to LLM for final answer...")
            second_response = self.openai_client.chat.completions.create(
                model=model_deployment_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            print("[TOOL CALLING] LLM generated final answer using tool results.")
            return second_response
        print("[TOOL CALLING] LLM responded directly without calling any tools.")
        return response
