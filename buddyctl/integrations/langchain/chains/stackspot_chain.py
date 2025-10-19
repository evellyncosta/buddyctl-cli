"""
StackSpot Chain - Orquestrador simples do padrão two-stage.

Fluxo:
1. Main Agent → resposta em texto livre
2. Judge Agent → analisa e decide tools (JSON)
3. Executa tools localmente se necessário
"""

from typing import List, Dict, Any
from langchain_core.tools import BaseTool
import json
import logging
import re

from .base import BaseChain
from ..chat_model import StackSpotChatModel


class StackSpotChain(BaseChain):
    """
    Chain simples para StackSpot com Judge Agent pattern.

    Orquestra: Main Agent → Judge Agent → Tools
    """

    def __init__(
        self,
        main_agent_id: str,
        judge_agent_id: str,
        tools: List[BaseTool]
    ):
        """
        Initialize StackSpot Chain.

        Args:
            main_agent_id: StackSpot agent ID for main agent
            judge_agent_id: StackSpot agent ID for judge agent
            tools: Available tools
        """
        super().__init__(tools)

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
        Execute: Main Agent → Judge Agent → Tools

        Args:
            user_input: User request

        Returns:
            {"output": str, "tool_calls_made": List, "iterations": int}
        """
        self.logger.debug("="*60)
        self.logger.debug("StackSpotChain.invoke() started")

        # 1. Main Agent gera resposta
        self.logger.debug("Step 1: Calling Main Agent")
        response = self.main_model.invoke(user_input)
        main_response = response.content if hasattr(response, 'content') else str(response)
        self.logger.debug(f"Main Agent response length: {len(main_response)}")

        # 2. Judge Agent analisa
        self.logger.debug("Step 2: Calling Judge Agent")
        decision = self._analyze_with_judge(user_input, main_response)
        self.logger.debug(f"Judge decision: needs_tools={decision.get('needs_tools')}")
        self.logger.debug(f"Tool calls count: {len(decision.get('tool_calls', []))}")

        # 3. Executa tools se necessário
        if decision["needs_tools"]:
            self.logger.debug(f"Step 3: Executing {len(decision['tool_calls'])} tool(s)")
            tool_results = self._execute_tools(decision["tool_calls"])
            self.logger.debug(f"Tool execution results: {tool_results}")
        else:
            self.logger.debug("Step 3: No tools needed, skipping execution")

        self.logger.debug("StackSpotChain.invoke() completed")
        self.logger.debug("="*60)

        return {
            "output": main_response,
            "tool_calls_made": decision["tool_calls"] if decision["needs_tools"] else [],
            "iterations": 1
        }

    def _analyze_with_judge(self, user_input: str, assistant_response: str) -> Dict[str, Any]:
        """
        Chama Judge Agent para analisar resposta.

        Returns:
            {"needs_tools": bool, "tool_calls": List, "reasoning": str}
        """
        # Build prompt
        tools_list = "\n".join([
            f"- {name}: {tool.description}"
            for name, tool in self.tools.items()
        ])

        prompt = f"""Analyze the assistant's response and decide if tools should be executed.

User Request:
{user_input}

Assistant Response:
{assistant_response}

Available Tools:
{tools_list}"""

        # Call Judge Agent
        self.logger.debug("Invoking Judge Agent")
        response = self.judge_model.invoke(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)
        self.logger.debug(f"Judge raw response (first 500 chars): {response_text[:500]}")

        # Parse JSON (extract from markdown if needed)
        json_text = self._extract_json(response_text)
        self.logger.debug(f"Extracted JSON (first 300 chars): {json_text[:300]}")

        try:
            decision = json.loads(json_text)
            self.logger.debug(f"Parsed decision: {decision}")
            return decision
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse judge response: {e}")
            self.logger.debug(f"Failed JSON text: {json_text[:500]}")
            return {
                "needs_tools": False,
                "tool_calls": [],
                "reasoning": f"Parse error: {e}"
            }

    def _extract_json(self, text: str) -> str:
        """Extract JSON from markdown code blocks or plain text."""
        # Try markdown code blocks first
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        return match.group(1).strip() if match else text.strip()


__all__ = ["StackSpotChain"]
