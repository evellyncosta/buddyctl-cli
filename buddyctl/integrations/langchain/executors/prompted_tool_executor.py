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
Prompted Tool Executor - NativeToolExecutor with System Prompts.

Adds prompt injection from local templates for providers without
pre-configured agents (OpenAI, Gemini, Claude).
"""

from typing import List, Dict, Any
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from .native_tool_executor import NativeToolExecutor
from ..prompts.loader import PromptLoader


class PromptedToolExecutor(NativeToolExecutor):
    """
    Tool executor with system prompt injection from local templates.

    Extends NativeToolExecutor to add:
    - System prompt loading from local templates
    - Prompt caching for performance
    - Zero-configuration operation

    Used by: OpenAI, Gemini, Claude (providers needing agent instructions)

    Example:
        >>> from langchain_openai import ChatOpenAI
        >>> from buddyctl.integrations.langchain.tools import BASIC_TOOLS
        >>>
        >>> model = ChatOpenAI(model="gpt-4")
        >>> model_with_tools = model.bind_tools(BASIC_TOOLS)
        >>>
        >>> executor = PromptedToolExecutor(
        ...     model=model_with_tools,
        ...     tools=BASIC_TOOLS,
        ...     prompt_name="code_agent"
        ... )
        >>>
        >>> result = executor.invoke("Add logging to @calculator.py")
        >>> print(result["output"])
    """

    def __init__(
        self,
        model: BaseChatModel,
        tools: List[BaseTool],
        prompt_name: str = "code_agent"
    ):
        """
        Initialize prompted executor.

        Args:
            model: LangChain chat model with tools bound
            tools: List of available tools
            prompt_name: Name of prompt template to load (default: "code_agent")
        """
        super().__init__(model, tools)

        self.prompt_name = prompt_name
        self.prompt_loader = PromptLoader()
        self.logger = logging.getLogger(__name__)

        # Load system prompt from local template
        self.system_prompt = self._load_system_prompt()
        self.logger.info(
            f"Loaded system prompt: {prompt_name} ({len(self.system_prompt)} chars)"
        )

    def _load_system_prompt(self) -> str:
        """
        Load system prompt from local template.

        Returns:
            System prompt text

        Raises:
            FileNotFoundError: If template not found
        """
        try:
            return self.prompt_loader.load_prompt(
                name=self.prompt_name,
                fallback=self._get_minimal_fallback()
            )
        except Exception as e:
            self.logger.error(f"Failed to load prompt '{self.prompt_name}': {e}")
            self.logger.warning("Using minimal fallback prompt")
            return self._get_minimal_fallback()

    def _get_minimal_fallback(self) -> str:
        """
        Get minimal fallback prompt (emergency only).

        Used when template file is missing or corrupted.
        """
        return """You are a coding assistant that helps modify code files.

Available tools:
- read_file: Read file contents
- search_replace_in_file: Replace exact text in files (SEARCH must match EXACTLY)
- create_new_file: Create new files

CRITICAL: When using search_replace_in_file, the SEARCH text must match the file EXACTLY (including whitespace).
Always read files first to ensure you have the exact text."""

    def invoke(self, user_input: str, max_iterations: int = 5) -> Dict[str, Any]:
        """
        Execute user request with system prompt injection.

        Overrides NativeToolExecutor.invoke() to inject system message.

        Args:
            user_input: User's request
            max_iterations: Maximum LLM->tool roundtrips

        Returns:
            {
                "output": str,                  # Final response
                "tool_calls_made": List[Dict],  # Tools executed
                "iterations": int,              # Number of roundtrips
                "prompt_used": str              # Prompt name (for debugging)
            }

        Example:
            >>> result = executor.invoke("Add comments to calculator.py")
            >>> print(result["output"])
            >>> print(f"Used prompt: {result['prompt_used']}")
        """
        self.logger.info(
            f"PromptedToolExecutor.invoke() started with prompt: {self.prompt_name}"
        )
        self.logger.debug(f"User input: {user_input[:100]}...")

        # Create messages with system prompt
        messages = [
            SystemMessage(content=self.system_prompt),  # ← SYSTEM PROMPT INJECTED
            HumanMessage(content=user_input)
        ]

        tool_calls_made = []
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            self.logger.debug(f"--- Iteration {iteration}/{max_iterations} ---")

            # Call LLM with system prompt
            self.logger.debug("Calling LLM with system prompt...")
            response = self.model.invoke(messages)

            # Check if LLM wants to call tools
            if not response.tool_calls:
                # No tool calls - LLM provided final answer
                self.logger.info("LLM provided final answer (no tool calls)")
                return {
                    "output": response.content,
                    "tool_calls_made": tool_calls_made,
                    "iterations": iteration,
                    "prompt_used": self.prompt_name
                }

            # LLM wants to call tools - execute them
            self.logger.info(f"LLM requested {len(response.tool_calls)} tool call(s)")
            messages.append(response)  # Add LLM's response

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call["id"]

                self.logger.info(f"Executing tool: {tool_name}")
                self.logger.debug(f"Tool args: {tool_args}")

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
            "output": (
                f"Max iterations reached ({max_iterations}). "
                f"Last tools called: {[tc['name'] for tc in tool_calls_made[-3:]]}"
            ),
            "tool_calls_made": tool_calls_made,
            "iterations": max_iterations,
            "prompt_used": self.prompt_name,
            "error": "max_iterations_reached"
        }


__all__ = ["PromptedToolExecutor"]
