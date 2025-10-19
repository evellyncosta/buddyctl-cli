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
        import logging
        logger = logging.getLogger(__name__)

        logger.debug(f"_execute_tools called with {len(tool_calls)} tool call(s)")
        logger.debug(f"Available tools: {list(self.tools.keys())}")

        results = {}

        for idx, call in enumerate(tool_calls):
            tool_name = call.get("name")
            tool_args = call.get("args", {})

            logger.debug(f"Tool call [{idx+1}]: name={tool_name}, args={tool_args}")

            if tool_name not in self.tools:
                error_msg = f"Error: Tool '{tool_name}' not found"
                logger.error(error_msg)
                results[tool_name] = error_msg
                continue

            try:
                tool = self.tools[tool_name]
                logger.debug(f"Invoking tool: {tool_name}")
                result = tool.invoke(tool_args)
                logger.debug(f"Tool {tool_name} result: {result[:200] if len(str(result)) > 200 else result}")
                results[tool_name] = str(result)
            except Exception as e:
                error_msg = f"Error executing {tool_name}: {e}"
                logger.error(error_msg)
                results[tool_name] = error_msg

        logger.debug(f"_execute_tools completed. Results: {list(results.keys())}")
        return results
