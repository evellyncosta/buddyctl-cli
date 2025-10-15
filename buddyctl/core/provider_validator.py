"""Provider validation and selection logic."""

from typing import Optional, List, Tuple
from .provider_registry import ProviderRegistry, ProviderValidationError
from .config import BuddyConfig, ConfigurationError


class ProviderValidator:
    """Validates and manages provider selection."""

    def __init__(self, config: BuddyConfig):
        self.config = config
        self.registry = ProviderRegistry()

    def validate_and_set_provider(self, provider_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate and set a provider as current.

        Returns:
            Tuple of (success, error_message)
        """
        # Validate provider
        is_valid, error_msg = self.registry.validate_provider(provider_name)

        if not is_valid:
            return False, error_msg

        # Check credentials
        has_creds, missing = self.registry.check_credentials(provider_name)

        if not has_creds:
            warning_msg = f"Warning: Missing credentials for {provider_name}: {', '.join(missing)}"
            # We'll still allow setting the provider, but warn the user
            # They can set credentials later
            return True, warning_msg

        # Set the provider
        try:
            self.config.set_current_provider(provider_name)
            return True, None
        except ConfigurationError as e:
            return False, str(e)

    def get_provider_status(self, provider_name: str) -> dict:
        """Get detailed status of a provider."""
        provider = self.registry.get_provider(provider_name)

        if not provider:
            return {
                "exists": False,
                "implemented": False,
                "enabled": False,
                "has_credentials": False,
                "missing_credentials": []
            }

        has_creds, missing = self.registry.check_credentials(provider_name)

        return {
            "exists": True,
            "name": provider.name,
            "display_name": provider.display_name,
            "implemented": provider.implemented,
            "enabled": provider.enabled,
            "has_credentials": has_creds,
            "missing_credentials": missing,
            "description": provider.description,
            "required_credentials": provider.requires_credentials
        }

    def list_providers(self, include_unimplemented: bool = True) -> List[dict]:
        """
        List all providers with their status.

        Args:
            include_unimplemented: If False, only show implemented providers

        Returns:
            List of provider status dictionaries
        """
        current_provider = self.config.get_current_provider()
        providers = []

        for name, info in self.registry.get_all_providers().items():
            if not include_unimplemented and not info.implemented:
                continue

            status = self.get_provider_status(name)
            status["is_current"] = (name == current_provider)
            providers.append(status)

        # Sort: current first, then implemented, then by name
        providers.sort(
            key=lambda p: (not p["is_current"], not p["implemented"], p["name"])
        )

        return providers
