"""Provider adapters for different LLM services."""

from .stackspot import StackSpotAdapter
from .google import GoogleAdapter

__all__ = ["StackSpotAdapter", "GoogleAdapter"]
