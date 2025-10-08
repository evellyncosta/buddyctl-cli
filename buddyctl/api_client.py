"""API client for StackSpot integration with agent support."""

import os
from typing import Optional
from .auth import StackSpotAuth
from .config import BuddyConfig


class APIClient:
    """API client for StackSpot with automatic agent ID path building."""
    
    def __init__(self, auth: Optional[StackSpotAuth] = None, config: Optional[BuddyConfig] = None):
        self.auth = auth or StackSpotAuth()
        self.config = config or BuddyConfig()
        self.base_url = self._get_api_base_url()
    
    def _get_api_base_url(self) -> str:
        """Get the StackSpot API base URL from environment."""
        return os.getenv("STACKSPOT_API_URL", "https://genai-inference-app.stackspot.com")
    
    def get_default_agent_id(self) -> Optional[str]:
        """Get the configured default agent ID."""
        return self.config.get_default_agent_id()
    
    def build_agent_url(self, endpoint: str, agent_id: Optional[str] = None) -> str:
        """
        Build an API URL with agent ID in the path.
        
        Args:
            endpoint: The API endpoint (e.g., '/conversations', '/knowledge-sources')
            agent_id: Optional agent ID override. If not provided, uses default.
            
        Returns:
            Complete URL with agent ID in path
            
        Raises:
            ValueError: If no agent ID is available (neither provided nor configured)
        """
        # Use provided agent_id or fall back to default
        effective_agent_id = agent_id or self.get_default_agent_id()
        
        if not effective_agent_id:
            raise ValueError(
                "No agent ID available. Either provide an agent_id parameter or "
                "configure a default agent using 'buddyctl agent-default <id>'"
            )
        
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        
        # Build URL: {base_url}/agents/{agent_id}{endpoint}
        return f"{self.base_url}/agents/{effective_agent_id}{endpoint}"
    
    def build_url(self, endpoint: str) -> str:
        """
        Build a regular API URL without agent ID.
        
        Args:
            endpoint: The API endpoint
            
        Returns:
            Complete URL
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
            
        return f"{self.base_url}{endpoint}"
    
    def get_auth_headers(self) -> dict:
        """Get authentication headers for API requests."""
        token = self.auth.get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }