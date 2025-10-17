"""
Base protocol for provider-specific chains.

Chains são workflows LCEL que orquestram:
- Múltiplas chamadas LLM
- Tool execution
- Response refinement

Cada provider tem suas próprias chains otimizadas.
"""

from typing import Protocol, Dict, Any, List, runtime_checkable
from langchain_core.tools import BaseTool


@runtime_checkable
class ChainProtocol(Protocol):
    """
    Interface comum para chains provider-specific.

    Chains implementam workflows compostos (LCEL) adaptados
    às capacidades de cada provider.
    """

    def invoke(self, user_input: str) -> Dict[str, Any]:
        """
        Execute chain workflow.

        Args:
            user_input: User request

        Returns:
            {
                "output": str,              # Final response
                "tool_calls_made": List,    # Tools executed
                "iterations": int           # Number of cycles
            }
        """
        ...


class BaseChain:
    """
    Base implementation for provider chains.

    Provides common functionality like tool execution and result formatting.
    """

    def __init__(self, tools: List[BaseTool]):
        self.tools = {tool.name: tool for tool in tools}

    def _execute_tools(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Execute tools locally and return results.

        Common implementation shared by all provider chains.
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
