"""LLM Provider Registry and Validation."""

import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ProviderInfo:
    """Information about an LLM provider."""

    name: str
    display_name: str
    implemented: bool
    enabled: bool
    requires_credentials: List[str]
    description: str


class ProviderValidationError(Exception):
    """Raised when provider validation fails."""

    pass


class ProviderRegistry:
    """Registry for managing LLM providers."""

    # Provider definitions
    PROVIDERS: Dict[str, ProviderInfo] = {
        "stackspot": ProviderInfo(
            name="stackspot",
            display_name="StackSpot AI",
            implemented=True,
            enabled=True,
            requires_credentials=["STACKSPOT_CLIENT_ID", "STACKSPOT_CLIENT_SECRET", "STACKSPOT_REALM"],
            description="StackSpot AI platform"
        ),
        "openai": ProviderInfo(
            name="openai",
            display_name="OpenAI GPT-4",
            implemented=False,
            enabled=False,
            requires_credentials=["OPENAI_API_KEY"],
            description="OpenAI's GPT-4 model"
        ),
        "anthropic": ProviderInfo(
            name="anthropic",
            display_name="Anthropic Claude",
            implemented=False,
            enabled=False,
            requires_credentials=["ANTHROPIC_API_KEY"],
            description="Anthropic's Claude model"
        ),
        "google": ProviderInfo(
            name="google",
            display_name="Google Gemini",
            implemented=True,
            enabled=True,
            requires_credentials=["GOOGLE_API_KEY"],
            description="Google's Gemini model"
        ),
        "ollama": ProviderInfo(
            name="ollama",
            display_name="Ollama (local)",
            implemented=False,
            enabled=False,
            requires_credentials=[],
            description="Local Ollama instance"
        )
    }

    @classmethod
    def get_provider(cls, name: str) -> Optional[ProviderInfo]:
        """Get provider info by name."""
        return cls.PROVIDERS.get(name.lower())

    @classmethod
    def get_all_providers(cls) -> Dict[str, ProviderInfo]:
        """Get all registered providers."""
        return cls.PROVIDERS.copy()

    @classmethod
    def get_available_providers(cls) -> Dict[str, ProviderInfo]:
        """Get only implemented providers."""
        return {
            name: info
            for name, info in cls.PROVIDERS.items()
            if info.implemented
        }

    @classmethod
    def validate_provider(cls, provider_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a provider can be used.

        Returns:
            Tuple of (is_valid, error_message)
        """
        provider = cls.get_provider(provider_name)

        # Check if provider exists
        if not provider:
            available = ", ".join(cls.PROVIDERS.keys())
            return False, f"Provider '{provider_name}' not found. Available: {available}"

        # Check if implemented
        if not provider.implemented:
            return False, f"{provider.display_name} is not implemented yet. Please choose an implemented provider."

        # Check if enabled
        if not provider.enabled:
            return False, f"{provider.display_name} is disabled."

        return True, None

    @classmethod
    def check_credentials(cls, provider_name: str) -> Tuple[bool, List[str]]:
        """
        Check if required credentials are present in environment.

        Returns:
            Tuple of (all_present, missing_credentials)
        """
        provider = cls.get_provider(provider_name)

        if not provider:
            return False, []

        missing = []
        for cred in provider.requires_credentials:
            if not os.getenv(cred):
                missing.append(cred)

        return len(missing) == 0, missing

    @classmethod
    def get_provider_display_info(cls, provider_name: str, is_current: bool = False) -> str:
        """Get formatted display string for a provider."""
        provider = cls.get_provider(provider_name)

        if not provider:
            return f"{provider_name} (unknown)"

        status = []

        if is_current:
            status.append("current")

        if provider.implemented:
            status.append("✓")
        else:
            status.append("not implemented yet")

        status_str = f" ({', '.join(status)})" if status else ""

        return f"{provider.display_name}{status_str}"
