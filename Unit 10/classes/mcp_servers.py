# =============================================================================
# MCP CLIENT
# =============================================================================
import time
import requests
import json


class MCPClient:
    """
    A client for communicating with Model Context Protocol (MCP) servers, with built-in retry logic.
    """

    def __init__(
        self,
        server_url,
        api_key,
        openai_client,
        llm_deployment_name,
        config,
    ):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.openai_client = openai_client
        self.tool_call_timeout_seconds = config["mcp"]["tool_call_timeout_seconds"]
        self.max_retries = config["mcp"]["max_retries"]
        self.backoff_seconds = config["mcp"]["backoff_seconds"]
        self.max_tool_response_length = config["mcp"]["max_tool_response_length"]
        self.llm_deployment_name = llm_deployment_name
        self.max_tokens = config["llm"]["max_tokens"]
        self.temperature = config["llm"]["temperature"]
        self.top_p = config["llm"]["top_p"]

    def list_tools(self):
        """
        PHASE 1 of MCP handshake: Ask the server what tools it provides.
        """
        print(f"\n[MCP] Phase 1: Discovering tools from {self.server_url}...")

        try:

            # This MCP Server expects a JSON-RPC 2.0 request to list tools, to execute the tools
            # and responds with Server-Sent Events (SSE) containing the results.
            # The exact format can vary by implementation, so always check the server's documentation.

            # What is JSON-RPC 2.0?
            # It's a standard protocol for remote procedure calls encoded in JSON. It typically includes:
            # - A "jsonrpc" field indicating the version (e.g., "2.0")
            # - A "method" field specifying the method to call (e.g., "tools/list")
            # - A "params" field containing any parameters for the method (can be empty)
            # - An "id" field to match requests and responses

            # Is JSON-RPC 2.0 common for MCP Servers?
            # Many MCP servers use JSON-RPC 2.0 for communication, but the exact implementation can vary.
            # Always check the server's documentation for the expected request and response formats.

            # What is SSE (Server-Sent Events)?
            # It's a way for servers to push real-time updates to clients over HTTP.
            # The server sends a stream of events, and each event can contain data.
            # In this case, we expect the MCP server to send an event with the tools list in JSON format.

            # Is SSE common for MCP Servers?
            # Many MCP servers use SSE to send responses, especially for streaming tool outputs,
            # but the exact implementation can vary.

            # 1. Prepare your headers with authentication (e.g., API key in Authorization header)
            if self.api_key is not None and self.api_key != "":
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "x-api-key": self.api_key,
                }
            else:
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                }

            # 2. MCP requires a JSON-RPC 2.0 handshake payload to list tools.
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/list",  # MCP method for listing tools
                "params": {},
                "id": 1,  # An arbitrary request ID
            }

            response = requests.post(
                self.server_url, headers=headers, json=payload, timeout=10
            )

            response.raise_for_status()

            ## Format of the response from this MCP Server is expected to be SSE with a JSON payload like:
            # event: message
            # data: {
            #     "result": {
            #         "tools": [
            #             {
            #                 "name": "tool_name",
            #                 "description": "Description of what the tool does",
            #                 "inputSchema": {
            #                     "type": "",
            #                     "properties": {
            #                         "input1": {
            #                             "type": "string",
            #                             "description": "Description of input1",
            #                         },
            #                         "input2": {
            #                             "type": "integer",
            #                             "description": "Description of input2",
            #                         },
            #                     },
            #                     "required": ["input1"],
            #                     "additionalProperties": false,
            #                     "$schema": "http://json-schema.org/draft-07/schema#",
            #                 },
            #                 "annotations": {
            #                     "readOnlyHint": true,
            #                     "destructiveHint": false,
            #                     "idempotentHint": true,
            #                     "openWorldHint": false,
            #                 },
            #                 "execution": {"taskSupport": "forbidden"},
            #             },
            #         ]
            #     },
            #     "jsonrpc": "2.0",
            #     "id": 1,
            # }

            # Find the line starting with 'data: '
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    json_data = line[len("data: ") :].strip()
                    # Remove BOM if present
                    json_data = json_data.lstrip("\ufeff")
                    data = json.loads(json_data)
                    break
            else:
                raise ValueError("No JSON data found in SSE response")

            tools = data["result"]["tools"]

            if not tools:
                print("[MCP] WARNING: No tools discovered from MCP server")
            else:
                print(f"[MCP] Discovered {len(tools)} tool(s):")
                for tool in tools:
                    desc = tool["description"]
                    print(f"  - {tool['name']}: {desc[:60]}")

            # Cache the tools for future calls
            self.tools = tools

            # Convert to OpenAI tool format for LLM calls
            self.convert_to_openai_tools()

        except requests.exceptions.Timeout:
            timeout_msg = f"timed out after {self.tool_call_timeout_seconds}s"
            print(f"[MCP] ERROR: Tool discovery {timeout_msg}")
            return []
        except requests.exceptions.RequestException as error:
            print(f"[MCP] ERROR: Tool discovery failed: {error}")
            return []

    def convert_to_openai_tools(self):
        """
        Convert MCP tool definitions to OpenAI's tool calling format.
        This allows the agent to use MCP tools through the standard
        OpenAI tool calling interface.
        """

        # Format the openai needs the tools in is as follows:
        # {
        #     "type": "function",
        #     "function": {
        #         "name": "tool_name",
        #         "description": "What the tool does",
        #         "parameters": {
        #             "type": "object",
        #             "properties": {
        #                 "input1": {
        #                     "type": "string",
        #                     "description": "Description of input1",
        #                 },
        #                 "input2": {
        #                     "type": "integer",
        #                     "description": "Description of input2",
        #                 },
        #             },
        #             "required": ["input1"],
        #         },
        #     },
        # }

        # What about annotations like readOnlyHint, destructiveHint, idempotentHint, openWorldHint?
        # These annotations provide important context about how the tool behaves and should be used.
        # However, OpenAI's current tool calling format does not have a standard way to include these hints.
        # As a workaround, we could include these hints in the tool's description field when converting the tools.

        # What about execution/taskSupport values like "forbidden", "allowed", "required"?
        # Similar to the annotations, the execution/taskSupport information is important for understanding how the tool
        # should be used, but there is no standard way to include this in OpenAI's tool format.
        # We could also include this information in the tool's description during conversion.

        mcp_tools = self.tools

        openai_tools = []
        for tool in mcp_tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["inputSchema"],
                },
            }
            openai_tools.append(openai_tool)

        self.tools = openai_tools  # Store converted tools for use in LLM calls

    def call_tool(self, tool_name, arguments):
        """
        PHASE 2 of MCP handshake: Ask the server to execute a specific tool.
        """
        print(f"\n[MCP] Phase 2: Calling tool '{tool_name}' with: {arguments}")

        # Use the same endpoint and headers as list_tools
        if self.api_key is not None and self.api_key != "":
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "x-api-key": self.api_key,
            }
        else:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }

        # JSON-RPC 2.0 payload for tool call
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 2,  # Arbitrary request ID
        }

        try:
            response = requests.post(
                self.server_url,
                headers=headers,
                json=payload,
                timeout=self.tool_call_timeout_seconds,
            )
            response.raise_for_status()

            ## Format of the response from this MCP Server is expected to be SSE with a JSON payload like:
            # event: message
            # data: {
            # "result": {
            #     "content": [
            #         {
            #             "type": "text",
            #             "text": "A long string from first result",
            #             "_meta": {"searchTime": 123.4},
            #         },
            #         {
            #             "type": "text",
            #             "text": "A long string from second result",
            #             "_meta": {"searchTime": 123.4},
            #         },
            #     ]
            # },
            #     "jsonrpc": "2.0",
            #     "id": 1,
            # }

            # Find the line starting with 'data: '
            for line in response.text.splitlines():
                if line.startswith("data: "):
                    json_data = line[len("data: ") :]
                    data = json.loads(json_data)
                    break
            else:
                raise ValueError("No JSON data found in SSE response")

            # Get the content
            content = data["result"]["content"]

            # Get the text from each returned result as a list
            text_results = [item["text"] for item in content if item["type"] == "text"]

            # Divide the max tool response length by the length of the text results to get a modified max length for each result to prevent overwhelming the LLM with too much tool output
            modified_max_tool_response_length = (
                self.max_tool_response_length // len(text_results)
                if text_results
                else self.max_tool_response_length
            )

            # Truncate each text results if it exceeds max length to prevent overwhelming the LLM
            text_results_truncated = [
                text[:modified_max_tool_response_length] for text in text_results
            ]

            # Join the truncated text results back into a single string to return as the tool result
            tool_result = "\n".join(text_results_truncated)

            return tool_result

        except requests.exceptions.Timeout:
            return (
                f"ERROR: MCP tool call to '{tool_name}' timed out after "
                f"{self.tool_call_timeout_seconds} seconds."
            )
        except requests.exceptions.RequestException as error:
            return f"ERROR: MCP tool call failed: {error}"
        except Exception as error:
            return f"ERROR: MCP tool call parsing failed: {error}"

    def execute_tool_with_retry(self, tool_name, tool_arguments):
        """
        Execute an MCP tool with automatic retry logic using exponential backoff.
        If the tool fails (returns an error starting with "ERROR:"), retry up to
        self.max_retries times. Each retry waits longer (backoff_seconds * 2^attempt).
        """
        last_error = None
        for attempt in range(self.max_retries):
            result = self.call_tool(tool_name, tool_arguments)
            if not result.startswith("ERROR:"):
                if attempt > 0:
                    print(f"[MCP] Retry {attempt} succeeded.")
                return result
            last_error = result
            wait_time = self.backoff_seconds * (2**attempt)
            if attempt < self.max_retries - 1:
                print(
                    f"[MCP] Attempt {attempt + 1} failed. Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
        return (
            f"ERROR: All {self.max_retries} attempts failed. Last error: {last_error}"
        )

    def call_llm_with_possible_tools(
        self,
        messages,
    ):

        print("\n" + "=" * 60)
        print("\n[MCP] Retrieving and caching available tools from MCP server...")
        # Ensure we have the latest tools from the MCP server before making the LLM call
        self.list_tools()

        print(
            f"\n[LLM CALL] Sending to {self.llm_deployment_name} with MCP tools available..."
        )

        start_time = time.time()
        response = self.openai_client.chat.completions.create(
            model=self.llm_deployment_name,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            tools=self.tools,
            tool_choice="auto",  # options: "none", "auto", or "all"
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
                model=self.llm_deployment_name,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
            )

            print("[TOOL CALLING] LLM generated final answer using tool results.")

            return second_response
        print("[TOOL CALLING] LLM responded directly without calling any tools.")

        return response
