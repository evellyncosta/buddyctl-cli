"""
Integration with StackSpot Judge Agent for two-stage tool calling.

This module implements Feature 18: Judge Agent Integration.
It orchestrates the two-stage pattern:
1. Main Agent generates plain text response
2. Judge Agent (StackSpot remote) analyzes and decides tool execution
3. Tools executed locally
4. Optional refinement with results

Architecture defined in Feature 17: Unified Tool Calling Abstraction.
"""

from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import json
import logging


class ToolCallDecision(BaseModel):
    """
    Decision from StackSpot Judge Agent.

    The Judge Agent analyzes a plain text response and decides whether
    tools should be executed based on content analysis.
    """

    needs_tools: bool = Field(
        description="Whether tools should be executed based on response content"
    )

    tool_calls: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Tools to execute: [{'name': 'tool_name', 'args': {...}}]"
    )

    reasoning: str = Field(
        description="Why tools are/aren't needed (from Judge Agent analysis)"
    )


class JudgeAgentExecutor:
    """
    Two-stage tool calling executor using StackSpot Judge Agent.

    This executor implements the architecture defined in Feature 17,
    specifically for the StackSpot provider which doesn't have native
    tool calling support.

    Flow:
    1. Main Agent (StackSpot) generates plain text response
    2. Judge Agent (StackSpot remote) analyzes content
    3. Tools executed locally if needed
    4. Optional refinement stage with tool results

    Example:
        >>> from buddyctl.integrations.langchain.tools import read_file, apply_diff
        >>>
        >>> executor = JudgeAgentExecutor(
        ...     main_agent_id="01K48SKQWX4D7A3AYF0P02X6GJ",
        ...     judge_agent_id="01K48SKQWX4D7A3AYF0P02X6GK",
        ...     tools=[read_file, apply_diff]
        ... )
        >>>
        >>> result = executor.invoke("Read calculator.py and modify it")
        >>> print(result["output"])
    """

    def __init__(
        self,
        main_agent_id: str,
        judge_agent_id: str,
        tools: List[BaseTool],
        max_iterations: int = 3,
        refine_with_results: bool = True
    ):
        """
        Initialize JudgeAgentExecutor.

        Args:
            main_agent_id: StackSpot agent ID for main agent
            judge_agent_id: StackSpot agent ID for judge agent
            tools: List of available tools (read_file, apply_diff, etc.)
            max_iterations: Max judge-execute cycles (default: 3)
            refine_with_results: Refine response with tool results (default: True)

        Raises:
            ValueError: If current provider is not StackSpot
        """
        self.main_agent_id = main_agent_id
        self.judge_agent_id = judge_agent_id
        self.tools = {tool.name: tool for tool in tools}
        self.max_iterations = max_iterations
        self.refine_with_results = refine_with_results
        self.logger = logging.getLogger(__name__)

        # Get StackSpot provider
        from ...core.providers import get_current_provider

        self.provider = get_current_provider()

        # Validate provider
        if not hasattr(self.provider, 'name') or self.provider.name != "stackspot":
            raise ValueError(
                f"JudgeAgentExecutor only works with StackSpot provider. "
                f"Current provider: {getattr(self.provider, 'name', 'unknown')}"
            )

    def invoke(self, user_input: str) -> Dict[str, Any]:
        """
        Execute two-stage tool calling pattern.

        This is the main interface method that implements the complete
        two-stage pattern: Main → Judge → Tools → Refine.

        Args:
            user_input: User request (e.g., "Read calculator.py and modify it")

        Returns:
            Dictionary with:
                - output (str): Final response text
                - tool_calls_made (List[Dict]): Tools that were executed
                - iterations (int): Number of judge-execute cycles

        Example:
            >>> result = executor.invoke("Add comments to calculator.py")
            >>> print(result["output"])
            >>> print(f"Tools executed: {len(result['tool_calls_made'])}")
        """
        self.logger.debug("="*60)
        self.logger.debug("JudgeAgentExecutor: Starting two-stage pattern")
        self.logger.debug(f"Main Agent: {self.main_agent_id}")
        self.logger.debug(f"Judge Agent: {self.judge_agent_id}")
        self.logger.debug(f"User Input: {user_input}")
        self.logger.debug("="*60)

        # Stage 1: Main Agent generates plain text response
        main_response = self._call_main_agent(user_input)

        self.logger.debug("STAGE 1 - Main Agent Response:")
        self.logger.debug(f"{main_response[:500]}...")

        tool_calls_made = []
        iteration = 0

        # Stage 2: Judge-Execute loop
        for iteration in range(self.max_iterations):
            self.logger.debug(f"STAGE 2 - Judge Iteration {iteration + 1}/{self.max_iterations}")

            # Call Judge Agent (StackSpot remote)
            decision = self._call_judge_agent(user_input, main_response)

            self.logger.debug(f"Judge Decision - Needs Tools: {decision.needs_tools}")
            self.logger.debug(f"Judge Reasoning: {decision.reasoning}")
            if decision.needs_tools:
                self.logger.debug(f"Tool Calls Requested: {len(decision.tool_calls)}")
                for idx, call in enumerate(decision.tool_calls):
                    self.logger.debug(f"  [{idx+1}] {call.get('name')}: {call.get('args')}")

            if not decision.needs_tools:
                # No tools needed, return response
                self.logger.debug("No tools needed. Returning response.")
                break

            # Stage 3: Execute tools locally
            self.logger.debug(f"STAGE 3 - Executing {len(decision.tool_calls)} tool(s)")
            tool_results = self._execute_tools(decision.tool_calls)
            tool_calls_made.extend(decision.tool_calls)

            for tool_name, result in tool_results.items():
                self.logger.debug(f"Tool {tool_name} result: {result[:200]}...")

            # Stage 4: Refine response with results (optional)
            if self.refine_with_results:
                self.logger.debug("STAGE 4 - Refining response with tool results")
                main_response = self._refine_with_results(
                    user_input,
                    main_response,
                    tool_results
                )
                self.logger.debug(f"Refined response: {main_response[:500]}...")

        return {
            "output": main_response,
            "tool_calls_made": tool_calls_made,
            "iterations": iteration + 1
        }

    def _call_main_agent(self, user_input: str) -> str:
        """
        Stage 1: Call Main Agent (StackSpot) to generate plain text response.

        The Main Agent uses the prompt from .doc/prompts/main_agent.md
        (configured in StackSpot dashboard).

        Args:
            user_input: User's request

        Returns:
            Plain text response from Main Agent
        """
        from ...core.logging import log_agent_request, log_agent_response

        # Log request
        log_agent_request(self.logger, "Main Agent", user_input)

        # Get StackSpot API client from provider
        # Note: Assuming provider has a method to get chat model
        from .chat_model import StackSpotChatModel

        # Create chat model for main agent
        main_model = StackSpotChatModel(
            agent_id=self.main_agent_id,
            streaming=False  # Non-streaming for judge pattern
        )

        # Invoke agent
        response = main_model.invoke(user_input)

        response_text = response.content if hasattr(response, 'content') else str(response)

        # Log response with distinctive markers
        log_agent_response(self.logger, "Main Agent", response_text)

        return response_text

    def _call_judge_agent(
        self,
        user_input: str,
        assistant_response: str
    ) -> ToolCallDecision:
        """
        Stage 2: Call Judge Agent (StackSpot remote) to analyze content.

        Judge Agent receives:
        - Original user request
        - Assistant's plain text response
        - List of available tools

        Returns:
            Decision object with needs_tools, tool_calls, reasoning
        """
        from ...core.logging import log_agent_request, log_agent_response

        # Build context for Judge Agent
        judge_prompt = self._build_judge_prompt(user_input, assistant_response)

        # Log request
        log_agent_request(self.logger, "Judge Agent", judge_prompt)

        # Create chat model for judge agent
        from .chat_model import StackSpotChatModel

        judge_model = StackSpotChatModel(
            agent_id=self.judge_agent_id,
            streaming=False  # Non-streaming for structured output
        )

        # Invoke judge agent
        response = judge_model.invoke(judge_prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)

        # Log response with distinctive markers
        log_agent_response(self.logger, "Judge Agent", response_text)

        # Parse JSON decision from Judge Agent
        try:
            decision_dict = json.loads(response_text)
            return ToolCallDecision(**decision_dict)
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: no tools if parsing fails
            self.logger.warning(f"Failed to parse judge response: {e}")
            self.logger.debug(f"Raw response: {response_text[:500]}...")

            return ToolCallDecision(
                needs_tools=False,
                tool_calls=[],
                reasoning=f"Failed to parse judge response: {e}"
            )

    def _build_judge_prompt(
        self,
        user_input: str,
        assistant_response: str
    ) -> str:
        """
        Build prompt for Judge Agent with context.

        Note: The Judge Agent on StackSpot already has its system prompt
        configured (from .doc/prompts/judge_agent.md). We just need to
        provide the context for this specific request.

        Args:
            user_input: Original user request
            assistant_response: Plain text response from Main Agent

        Returns:
            Formatted prompt for Judge Agent
        """
        # List available tools
        tools_list = "\n".join([
            f"- {name}: {tool.description}"
            for name, tool in self.tools.items()
        ])

        prompt = f"""Analyze the assistant's response and decide if tools should be executed.

User Request:
{user_input}

Assistant Response (PLAIN TEXT):
{assistant_response}

Available Tools:
{tools_list}

Task: Return JSON with your decision:
{{
  "needs_tools": true/false,
  "tool_calls": [{{"name": "tool_name", "args": {{"param": "value"}}}}],
  "reasoning": "Why tools are/aren't needed based on response content"
}}

Return JSON only:"""

        return prompt

    def _execute_tools(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Stage 3: Execute tools locally and return results.

        Tools are executed on the local machine, not on StackSpot.
        This allows file operations, diffs, etc.

        Args:
            tool_calls: List of tool calls from Judge Agent

        Returns:
            Dictionary mapping tool names to their results
        """
        results = {}

        for call in tool_calls:
            tool_name = call.get("name")
            tool_args = call.get("args", {})

            if tool_name not in self.tools:
                results[tool_name] = f"Error: Tool '{tool_name}' not found"
                continue

            try:
                tool = self.tools[tool_name]
                result = tool.invoke(tool_args)
                results[tool_name] = str(result)
            except Exception as e:
                results[tool_name] = f"Error executing {tool_name}: {e}"

        return results

    def _refine_with_results(
        self,
        user_input: str,
        original_response: str,
        tool_results: Dict[str, str]
    ) -> str:
        """
        Stage 4: Call Main Agent again with tool results to refine response.

        This stage is optional but recommended. It allows the Main Agent
        to incorporate actual tool results instead of speculation.

        Args:
            user_input: Original user request
            original_response: Previous response from Main Agent
            tool_results: Results from tool execution

        Returns:
            Refined response incorporating tool results
        """
        from ...core.logging import log_agent_request, log_agent_response

        # Format tool results nicely
        results_text = "\n".join([
            f"Tool: {tool_name}\nResult: {result}\n"
            for tool_name, result in tool_results.items()
        ])

        refine_prompt = f"""Original Request:
{user_input}

Your Previous Response:
{original_response}

Tool Execution Results:
{results_text}
"""

        # Log refinement request
        log_agent_request(self.logger, "Main Agent (Refinement)", refine_prompt)

        # Create chat model for refinement
        from .chat_model import StackSpotChatModel

        main_model = StackSpotChatModel(
            agent_id=self.main_agent_id,
            streaming=False
        )

        response = main_model.invoke(refine_prompt)

        response_text = response.content if hasattr(response, 'content') else str(response)

        # Log refined response
        log_agent_response(self.logger, "Main Agent (Refinement)", response_text)

        return response_text


# Export public API
__all__ = ["JudgeAgentExecutor", "ToolCallDecision"]
