"""OAuth2 authentication module for StackSpot integration."""

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Any
import httpx


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class TokenExpiredError(Exception):
    """Raised when token is expired and cannot be refreshed."""

    pass


class StackSpotAuth:
    """OAuth2 authentication handler for StackSpot."""

    def __init__(self):
        self.credentials_path = Path.home() / ".buddyctl" / "credentials.json"
        self.client_id = os.getenv("STACKSPOT_CLIENT_ID")
        self.client_secret = os.getenv("STACKSPOT_CLIENT_SECRET")
        self.realm = os.getenv("STACKSPOT_REALM")
        self.auth_url = os.getenv("STACKSPOT_AUTH_URL", "https://idm.stackspot.com")

        # Token cache and synchronization
        self._token_cache: Optional[Dict[str, Any]] = None
        self._cache_lock = threading.Lock()
        self._token_buffer = int(os.getenv("STACKSPOT_TOKEN_BUFFER", "300"))  # 5 min default
        self._logger = logging.getLogger(__name__)

    def _ensure_credentials_dir(self) -> None:
        """Ensure the credentials directory exists with proper permissions."""
        credentials_dir = self.credentials_path.parent
        credentials_dir.mkdir(mode=0o700, exist_ok=True)

    def _get_token_endpoint(self) -> str:
        """Get the OAuth2 token endpoint URL."""
        return f"{self.auth_url}/{self.realm}/oidc/oauth/token"

    def _validate_config(self) -> None:
        """Validate that all required configuration is present."""
        if not all([self.client_id, self.client_secret, self.realm]):
            raise AuthenticationError(
                "Missing required configuration. Please ensure STACKSPOT_CLIENT_ID, "
                "STACKSPOT_CLIENT_SECRET, and STACKSPOT_REALM are set."
            )

    def _request_access_token(self) -> Dict[str, Any]:
        """Request a new access token using client credentials flow."""
        self._validate_config()

        token_url = self._get_token_endpoint()

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            with httpx.Client() as client:
                response = client.post(token_url, data=data, headers=headers)
                response.raise_for_status()

            token_data = response.json()

            # Calculate expiration timestamp
            expires_in = token_data.get("expires_in", 3600)
            expires_at = time.time() + expires_in

            credentials = {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "expires_at": expires_at,
                "realm": self.realm,
                "token_type": token_data.get("token_type", "Bearer"),
            }

            return credentials

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid client credentials")
            elif e.response.status_code == 404:
                raise AuthenticationError(f"Invalid realm or auth URL: {token_url}")
            else:
                raise AuthenticationError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise AuthenticationError(f"Network error: {str(e)}")
        except KeyError as e:
            raise AuthenticationError(f"Invalid token response: missing {e}")

    def _save_credentials(self, credentials: Dict[str, Any]) -> None:
        """Save credentials to disk with secure permissions."""
        self._ensure_credentials_dir()

        with open(self.credentials_path, "w") as f:
            json.dump(credentials, f, indent=2)

        # Set secure permissions (owner read/write only)
        os.chmod(self.credentials_path, 0o600)

    def _load_credentials(self) -> Optional[Dict[str, Any]]:
        """Load credentials from disk."""
        if not self.credentials_path.exists():
            return None

        try:
            with open(self.credentials_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _is_token_expired(self, credentials: Dict[str, Any], buffer: Optional[int] = None) -> bool:
        """Check if the current token is expired or will expire soon.

        Args:
            credentials: Credential dictionary with expires_at
            buffer: Custom buffer in seconds (default: self._token_buffer)

        Returns:
            True if token is expired or will expire within buffer time
        """
        if buffer is None:
            buffer = self._token_buffer

        expires_at = credentials.get("expires_at", 0)
        current_time = time.time()
        time_until_expiry = expires_at - current_time

        # Log detailed expiration info
        if time_until_expiry <= buffer:
            self._logger.debug(
                f"Token expiring soon or expired. Time until expiry: {time_until_expiry:.0f}s, "
                f"buffer: {buffer}s"
            )

        return current_time >= (expires_at - buffer)

    def _refresh_token(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Attempt to refresh the token using refresh_token.

        Args:
            credentials: Current credentials with refresh_token

        Returns:
            New credentials if refresh succeeds, None otherwise
        """
        refresh_token = credentials.get("refresh_token")
        if not refresh_token:
            # This is expected for client_credentials flow
            self._logger.debug("No refresh_token available (likely client_credentials flow)")
            return None

        token_url = self._get_token_endpoint()

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            self._logger.debug("Attempting to refresh token...")
            with httpx.Client() as client:
                response = client.post(token_url, data=data, headers=headers)
                response.raise_for_status()

            token_data = response.json()

            # Calculate expiration timestamp
            expires_in = token_data.get("expires_in", 3600)
            expires_at = time.time() + expires_in

            new_credentials = {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token", refresh_token),
                "expires_at": expires_at,
                "realm": self.realm,
                "token_type": token_data.get("token_type", "Bearer"),
            }

            self._logger.debug(f"Token refreshed successfully. New expiration: {expires_in}s")
            return new_credentials

        except (httpx.HTTPStatusError, httpx.RequestError, KeyError) as e:
            # Refresh failed, will fallback to re-authentication
            self._logger.debug(f"Token refresh failed: {type(e).__name__}")
            return None

    def _handle_token_renewal(self, credentials: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle token renewal with fallback strategy.

        Strategy:
        1. Try refresh_token if available
        2. Fallback to full re-authentication
        3. Clear credentials on failure

        Args:
            credentials: Current credentials (may be expired or None)

        Returns:
            New valid credentials

        Raises:
            AuthenticationError: If all renewal attempts fail
        """
        # Try refresh first if we have credentials
        if credentials:
            refresh_token = credentials.get("refresh_token")

            if refresh_token:
                # Attempt refresh
                self._logger.debug("Attempting token refresh with refresh_token")
                new_credentials = self._refresh_token(credentials)
                if new_credentials:
                    self._logger.debug("Token refresh successful")
                    return new_credentials
                else:
                    self._logger.debug("Token refresh failed, falling back to full authentication")
            else:
                self._logger.debug("No refresh_token available, performing full authentication")

        # Fallback: full re-authentication
        try:
            self._logger.debug("Requesting new access token")
            new_credentials = self._request_access_token()
            self._logger.debug("New access token obtained successfully")
            return new_credentials
        except AuthenticationError as e:
            # Clear invalid credentials
            self._logger.error(f"Authentication failed: {e}")
            if self.credentials_path.exists():
                self._logger.debug("Clearing invalid credentials")
                self.credentials_path.unlink()
            raise

    def get_valid_token(self) -> str:
        """Get a valid access token, handling refresh and re-authentication as needed.

        This method implements proactive token refresh:
        - Checks cache first (in-memory)
        - Refreshes proactively before expiration
        - Uses lock to prevent concurrent refresh attempts

        Returns:
            Valid access token

        Raises:
            AuthenticationError: If authentication fails
        """
        with self._cache_lock:
            # Check cache first
            if self._token_cache and not self._is_token_expired(self._token_cache):
                self._logger.debug("Using cached token")
                return self._token_cache["access_token"]

            # Cache miss or expired, load from disk
            self._logger.debug("Cache miss or expired, loading credentials from disk")
            credentials = self._load_credentials()

            # If no credentials or expired, try refresh or re-auth
            if not credentials or self._is_token_expired(credentials):
                self._logger.debug("Credentials missing or expired, initiating token renewal")
                new_credentials = self._handle_token_renewal(credentials)
                self._save_credentials(new_credentials)
                self._token_cache = new_credentials
                return new_credentials["access_token"]

            # Valid credentials, update cache
            self._logger.debug("Credentials valid, updating cache")
            self._token_cache = credentials
            return credentials["access_token"]

    def is_authenticated(self) -> bool:
        """Check if we have valid authentication."""
        try:
            self.get_valid_token()
            return True
        except AuthenticationError:
            return False

    def get_auth_status(self) -> Dict[str, Any]:
        """Get current authentication status for display."""
        credentials = self._load_credentials()

        if not credentials:
            return {"authenticated": False, "status": "Not authenticated", "realm": None}

        if self._is_token_expired(credentials):
            return {
                "authenticated": False,
                "status": "Token expired",
                "realm": credentials.get("realm"),
            }

        return {"authenticated": True, "status": "Authenticated", "realm": credentials.get("realm")}

    def logout(self) -> None:
        """Remove stored credentials."""
        if self.credentials_path.exists():
            self.credentials_path.unlink()
