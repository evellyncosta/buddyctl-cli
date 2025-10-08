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
        return "🤖 Default Agent: Not configured"


def display_banner(auth: "StackSpotAuth" = None, config: Optional["BuddyConfig"] = None) -> None:
    """Display the buddyctl banner with authentication and agent status to the console."""
    print(get_banner())

    if auth:
        print(get_auth_status_display(auth))

    if config:
        print(get_agent_status_display(config))

    if auth or config:
        print()  # Add extra line for spacing
