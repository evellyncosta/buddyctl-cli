"""
StackSpot-specific chain implementation.

Usa Judge Agent (remoto) para analisar respostas e decidir tool calls.
A chain executa tools MANUALMENTE baseada na decisão do Judge Agent.
"""

from typing import List, Dict, Any
from langchain_core.tools import BaseTool
import json
import logging

from .base import BaseChain, ChainProtocol
from ..chat_model import StackSpotChatModel


class StackSpotChain(BaseChain):
    """
    Chain específica para StackSpot com Judge Agent.

    Implementa two-stage pattern:
    1. Main Agent gera resposta (texto livre)
    2. Judge Agent analisa resposta (JSON estruturado) - REMOTO
    3. Chain executa tools MANUALMENTE baseado na decisão
    4. Main Agent refina resposta com resultados

    Diferença de JudgeAgentExecutor:
    - JudgeAgentExecutor: Executor imperativo (Python)
    - StackSpotChain: Workflow declarativo (LCEL)

    A chain oferece:
    - Composição declarativa via LCEL
    - Reusabilidade de steps
    - Testabilidade de stages
    - Melhor integração com LangChain ecosystem
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
        Initialize StackSpot Chain.

        Args:
            main_agent_id: StackSpot agent ID for main agent
            judge_agent_id: StackSpot agent ID for judge agent
            tools: Available tools
            max_iterations: Max judge-execute cycles
            refine_with_results: Refine response with tool results
        """
        super().__init__(tools)

        self.main_agent_id = main_agent_id
        self.judge_agent_id = judge_agent_id
        self.max_iterations = max_iterations
        self.refine_with_results = refine_with_results
        self.logger = logging.getLogger(__name__)

        # Create models
        self.main_model = StackSpotChatModel(
            agent_id=main_agent_id,
            streaming=False
        )

        self.judge_model = StackSpotChatModel(
            agent_id=judge_agent_id,
            streaming=False
        )

    def invoke(self, user_input: str) -> Dict[str, Any]:
        """
        Execute StackSpot chain workflow.

        Flow:
        1. Main Agent generates plain text response
        2. Judge Agent analyzes response (remote) → JSON decision
        3. Chain executes tools MANUALLY based on decision
        4. Main Agent refines response with tool results

        Args:
            user_input: User request

        Returns:
            {
                "output": Final response,
                "tool_calls_made": Tools executed,
                "iterations": Number of judge cycles
            }
        """
        self.logger.debug("="*60)
        self.logger.debug("StackSpotChain: Starting workflow")
        self.logger.debug(f"Main Agent: {self.main_agent_id}")
        self.logger.debug(f"Judge Agent: {self.judge_agent_id}")
        self.logger.debug(f"User Input: {user_input}")
        self.logger.debug("="*60)

        # Stage 1: Main Agent generates response
        main_response = self._call_main_agent(user_input)

        self.logger.debug(f"Stage 1 - Main Agent Response:\n{main_response[:500]}...")

        tool_calls_made = []
        iteration = 0

        # Stage 2-3: Judge-Execute loop
        for iteration in range(self.max_iterations):
            self.logger.debug(f"Stage 2 - Judge Iteration {iteration + 1}/{self.max_iterations}")

            # Call Judge Agent (remote)
            decision = self._call_judge_agent(user_input, main_response)

            self.logger.debug(f"Judge Decision - Needs Tools: {decision['needs_tools']}")
            self.logger.debug(f"Judge Reasoning: {decision['reasoning']}")

            if not decision["needs_tools"]:
                self.logger.debug("No tools needed. Returning response.")
                break

            # Execute tools MANUALLY in the chain
            self.logger.debug(f"Stage 3 - Executing {len(decision['tool_calls'])} tool(s)")
            tool_results = self._execute_tools(decision["tool_calls"])
            tool_calls_made.extend(decision["tool_calls"])


        return {
            "output": main_response,
            "tool_calls_made": tool_calls_made,
            "iterations": iteration + 1
        }

    def _call_main_agent(self, user_input: str) -> str:
        """Stage 1: Call Main Agent."""
        response = self.main_model.invoke(user_input)
        return response.content if hasattr(response, 'content') else str(response)

    def _call_judge_agent(
        self,
        user_input: str,
        assistant_response: str
    ) -> Dict[str, Any]:
        """
        Stage 2: Call Judge Agent (REMOTO) to analyze response.

        Judge Agent retorna JSON estruturado:
        {
            "needs_tools": true/false,
            "tool_calls": [{"name": "tool", "args": {...}}],
            "reasoning": "Why tools are/aren't needed"
        }
        """
        judge_prompt = self._build_judge_prompt(user_input, assistant_response)

        response = self.judge_model.invoke(judge_prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)

        # Extract JSON from markdown code blocks if present
        json_text = self._extract_json_from_markdown(response_text)

        # Parse JSON decision
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse judge response: {e}")
            self.logger.debug(f"Raw response text: {response_text[:500]}")
            return {
                "needs_tools": False,
                "tool_calls": [],
                "reasoning": f"Failed to parse: {e}"
            }

    def _extract_json_from_markdown(self, text: str) -> str:
        """
        Extract JSON content from markdown code blocks.

        Handles formats like:
        ```json
        {...}
        ```

        or just plain JSON.
        """
        import re

        # Try to find JSON in markdown code blocks (```json ... ``` or ``` ... ```)
        markdown_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        match = re.search(markdown_pattern, text, re.DOTALL)

        if match:
            return match.group(1).strip()

        # No markdown blocks found, return original text
        return text.strip()

    def _build_judge_prompt(self, user_input: str, assistant_response: str) -> str:
        """Build prompt for Judge Agent."""
        tools_list = "\n".join([
            f"- {name}: {tool.description}"
            for name, tool in self.tools.items()
        ])

        return f"""Analyze the assistant's response and decide if tools should be executed.

User Request:
{user_input}

Assistant Response:
{assistant_response}

Available Tools:
{tools_list}
"""

    def _refine_with_results(
        self,
        user_input: str,
        original_response: str,
        tool_results: Dict[str, str]
    ) -> str:
        """Stage 4: Refine response with tool results."""
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

Provide a final response incorporating the tool results."""

        response = self.main_model.invoke(refine_prompt)
        return response.content if hasattr(response, 'content') else str(response)


# Export
__all__ = ["StackSpotChain"]
