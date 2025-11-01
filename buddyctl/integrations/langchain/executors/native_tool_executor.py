# Copyright 2024 Evellyn
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Native Tool Executor for LLMs with function calling support.

This executor is designed for providers that support native function calling
(OpenAI, Google Gemini, Anthropic Claude). The LLM autonomously decides when
to call tools, and the executor handles the invocation and result formatting.
"""

from typing import List, Dict, Any
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


class NativeToolExecutor:
    """
    Executor for LLMs with native function calling support.

    Usage:
        >>> from langchain_openai import ChatOpenAI
        >>> from buddyctl.integrations.langchain.tools import BASIC_TOOLS
        >>>
        >>> # Create model with tools
        >>> model = ChatOpenAI(model="gpt-4")
        >>> model_with_tools = model.bind_tools(BASIC_TOOLS)
        >>>
        >>> # Create executor
        >>> executor = NativeToolExecutor(model_with_tools, BASIC_TOOLS)
        >>>
        >>> # Execute user request (LLM decides which tools to call)
        >>> result = executor.invoke("Modify the authenticate function in auth.py")
        >>> print(result["output"])

    Flow:
        1. User sends request
        2. LLM analyzes and decides: "I need to call search_replace_in_file"
        3. LLM returns tool_calls in response
        4. Executor invokes tools automatically
        5. Tools validate + apply + return results
        6. Executor formats final response
    """

    def __init__(self, model: BaseChatModel, tools: List[BaseTool]):
        """
        Initialize executor with model and tools.

        Args:
            model: LangChain chat model with tools already bound via bind_tools()
            tools: List of available tools (must match tools bound to model)
        """
        self.model = model
        self.tools_dict = {tool.name: tool for tool in tools}
        self.logger = logging.getLogger(__name__)

        self.logger.debug(f"NativeToolExecutor initialized with {len(tools)} tools")
        self.logger.debug(f"Available tools: {list(self.tools_dict.keys())}")

    def invoke(self, user_input: str, max_iterations: int = 5) -> Dict[str, Any]:
        """
        Execute user request with LLM-driven tool calling.

        The LLM decides autonomously when to call tools. The executor handles
        the tool invocation loop until the LLM provides a final answer or
        max_iterations is reached.

        Args:
            user_input: User's request/question
            max_iterations: Maximum number of LLM->tool roundtrips (default: 5)

        Returns:
            {
                "output": str,              # Final response from LLM
                "tool_calls_made": List[Dict],  # List of tools called with args
                "iterations": int           # Number of LLM->tool roundtrips
            }

        Example:
            >>> result = executor.invoke("Fix the bug in calculate_total")
            >>> print(result["output"])
            "Successfully fixed the bug in calculate_total function."
            >>> print(result["tool_calls_made"])
            [{"name": "search_replace_in_file", "args": {...}}]
            >>> print(result["iterations"])
            2
        """
        self.logger.info(f"NativeToolExecutor.invoke() started")
        self.logger.debug(f"User input: {user_input[:100]}...")

        messages = [HumanMessage(content=user_input)]
        tool_calls_made = []
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            self.logger.debug(f"--- Iteration {iteration}/{max_iterations} ---")

            # 1. Call LLM
            self.logger.debug("Calling LLM...")
            response = self.model.invoke(messages)

            # 2. Check if LLM wants to call tools
            if not response.tool_calls:
                # No tool calls - LLM provided final answer
                self.logger.info(f"LLM provided final answer (no tool calls)")
                return {
                    "output": response.content,
                    "tool_calls_made": tool_calls_made,
                    "iterations": iteration
                }

            # 3. LLM wants to call tools - execute them
            self.logger.info(f"LLM requested {len(response.tool_calls)} tool call(s)")
            messages.append(response)  # Add LLM's response with tool_calls

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call["id"]

                self.logger.info(f"Executing tool: {tool_name}({tool_args})")

                # Get tool and invoke
                tool = self.tools_dict.get(tool_name)
                if not tool:
                    error_msg = f"Error: Tool '{tool_name}' not found"
                    self.logger.error(error_msg)
                    messages.append(ToolMessage(
                        content=error_msg,
                        tool_call_id=tool_call_id
                    ))
                    continue

                # Invoke tool
                try:
                    result = tool.invoke(tool_args)
                    self.logger.debug(f"Tool result: {result[:200]}...")

                    # Record tool call
                    tool_calls_made.append({
                        "name": tool_name,
                        "args": tool_args,
                        "result": result
                    })

                    # Add tool result to messages
                    messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call_id
                    ))

                except Exception as e:
                    error_msg = f"Error executing tool {tool_name}: {str(e)}"
                    self.logger.error(error_msg)
                    messages.append(ToolMessage(
                        content=error_msg,
                        tool_call_id=tool_call_id
                    ))

            # Loop continues - LLM will see tool results and decide next action

        # Max iterations reached
        self.logger.warning(f"Max iterations ({max_iterations}) reached")
        return {
            "output": f"Max iterations reached ({max_iterations}). Last tools called: {[tc['name'] for tc in tool_calls_made]}",
            "tool_calls_made": tool_calls_made,
            "iterations": max_iterations,
            "error": "max_iterations_reached"
        }


__all__ = ["NativeToolExecutor"]
