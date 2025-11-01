"""ASCII banner generation for buddyctl CLI."""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .auth import StackSpotAuth
    from .config import BuddyConfig


def get_banner() -> str:
    """Generate and return the buddyctl ASCII banner."""
    banner = """
██████╗ ██╗   ██╗██████╗ ██████╗ ██╗   ██╗ ██████╗████████╗██╗     
██╔══██╗██║   ██║██╔══██╗██╔══██╗╚██╗ ██╔╝██╔════╝╚══██╔══╝██║     
██████╔╝██║   ██║██║  ██║██║  ██║ ╚████╔╝ ██║        ██║   ██║     
██╔══██╗██║   ██║██║  ██║██║  ██║  ╚██╔╝  ██║        ██║   ██║     
██████╔╝╚██████╔╝██████╔╝██████╔╝   ██║   ╚██████╗   ██║   ███████╗
╚═════╝  ╚═════╝ ╚═════╝ ╚═════╝    ╚═╝    ╚═════╝   ╚═╝   ╚══════╝
"""
    return banner


def get_auth_status_display(auth: "StackSpotAuth") -> str:
    """Generate authentication status display."""
    status = auth.get_auth_status()

    if status["authenticated"]:
        return f"✅ Authentication: {status['status']} (Realm: {status['realm']})"
    else:
        realm_info = f" (Realm: {status['realm']})" if status["realm"] else ""
        return f"❌ Authentication: {status['status']}{realm_info}"


def get_agent_status_display(config: "BuddyConfig") -> str:
    """Generate default agent status display."""
    status = config.get_config_status()

    if status["has_default_agent"]:
        return f"🤖 Default Agent: {status['default_agent_id']}"
    else:
        return "⚠️  Default Agent: Not configured"


def get_provider_status_display(config: "BuddyConfig") -> str:
    """Generate LLM provider status display."""
    from ..core.provider_validator import ProviderValidator
    from ..core.provider_registry import ProviderRegistry

    status = config.get_config_status()
    current_provider = status.get("current_provider", "stackspot")

    # Get provider info
    provider_info = ProviderRegistry.get_provider(current_provider)
    if not provider_info:
        return f"🔮 LLM Provider: {current_provider} (unknown)"

    # Validate credentials
    validator = ProviderValidator(config)
    provider_status = validator.get_provider_status(current_provider)

    if provider_status["implemented"]:
        if provider_status["has_credentials"]:
            return f"🔮 LLM Provider: {provider_info.display_name}"
        else:
            missing = ", ".join(provider_status["missing_credentials"])
            return f"⚠️  LLM Provider: {provider_info.display_name} (missing: {missing})"
    else:
        return f"⚠️  LLM Provider: {provider_info.display_name} (not implemented)"


def display_banner(auth: "StackSpotAuth" = None, config: Optional["BuddyConfig"] = None) -> None:
    """Display the buddyctl banner with authentication, provider and agent status to the console."""
    print(get_banner())

    # Get current provider to decide what to show
    current_provider = config.get_current_provider() if config else "stackspot"

    # Show authentication only for StackSpot provider
    if auth and current_provider == "stackspot":
        print(get_auth_status_display(auth))

    if config:
        print(get_provider_status_display(config))

        # Show default agent only for StackSpot provider (other providers don't use agent_id)
        if current_provider == "stackspot":
            print(get_agent_status_display(config))

    if auth or config:
        print()  # Add extra line for spacing
