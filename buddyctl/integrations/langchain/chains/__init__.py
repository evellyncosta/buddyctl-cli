"""
Provider-specific chains module.

Each provider has its own optimized chain implementation:
- StackSpot: Uses Judge Agent (remote) for tool calling decisions
- OpenAI: Uses native function calling (future)
- Anthropic: Uses native tool use (future)
"""

from .base import ChainProtocol, BaseChain

__all__ = ["ChainProtocol", "BaseChain"]
