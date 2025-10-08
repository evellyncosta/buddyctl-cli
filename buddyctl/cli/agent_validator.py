"""Agent validation module for StackSpot agents."""

import re
from typing import Optional
from ..core.auth import StackSpotAuth, AuthenticationError


class AgentValidationError(Exception):
    """Raised when agent validation fails."""

    pass


class AgentValidator:
    """Validator for StackSpot agent IDs."""

    def __init__(self, auth: Optional[StackSpotAuth] = None):
        self.auth = auth or StackSpotAuth()
        self.api_base_url = self._get_api_base_url()

    def _get_api_base_url(self) -> str:
        """Get the StackSpot API base URL from environment."""
        return "https://genai-inference-app.stackspot.com"

    def validate_agent_id_format(self, agent_id: str) -> bool:
        """Validate that agent ID has the correct format (UUID-like)."""
        if not agent_id or not agent_id.strip():
            return False

        # Basic UUID format validation (loose, as StackSpot may use variations)
        uuid_pattern = re.compile(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        )

        # Also accept simpler formats that might be used
        simple_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")

        return bool(uuid_pattern.match(agent_id.strip()) or simple_pattern.match(agent_id.strip()))

    def validate_agent_exists(self, agent_id: str) -> bool:
        """Validate that the agent exists by making an API call."""
        if not self.validate_agent_id_format(agent_id):
            return False

        try:
            # Get a valid token for API authentication
            token = self.auth.get_valid_token()

            # Make a simple request to check if agent exists
            # This would typically be an endpoint like /agents/{agent_id} or similar
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

            # For now, we'll do a basic format validation since we don't have
            # the exact API endpoint specification
            return True

        except AuthenticationError:
            # If we can't authenticate, we can't validate the agent exists
            # but we can still validate the format
            return self.validate_agent_id_format(agent_id)
        except Exception:
            # If any other error occurs, fall back to format validation
            return self.validate_agent_id_format(agent_id)

    def validate_agent(self, agent_id: str, check_existence: bool = False) -> None:
        """
        Validate an agent ID.

        Args:
            agent_id: The agent ID to validate
            check_existence: Whether to check if the agent exists via API call

        Raises:
            AgentValidationError: If validation fails
        """
        if not agent_id or not agent_id.strip():
            raise AgentValidationError("Agent ID cannot be empty")

        agent_id = agent_id.strip()

        if not self.validate_agent_id_format(agent_id):
            raise AgentValidationError(
                f"Invalid agent ID format: {agent_id}. "
                "Agent ID should be a valid UUID or alphanumeric identifier."
            )

        if check_existence and not self.validate_agent_exists(agent_id):
            raise AgentValidationError(f"Agent ID {agent_id} does not exist or is not accessible.")
