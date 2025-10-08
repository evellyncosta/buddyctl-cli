"""OAuth2 authentication module for StackSpot integration."""

import json
import os
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

    def _is_token_expired(self, credentials: Dict[str, Any]) -> bool:
        """Check if the current token is expired."""
        expires_at = credentials.get("expires_at", 0)
        # Add 60 second buffer to account for request time
        return time.time() >= (expires_at - 60)

    def _refresh_token(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Attempt to refresh the token using refresh_token."""
        refresh_token = credentials.get("refresh_token")
        if not refresh_token:
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

            return new_credentials

        except (httpx.HTTPStatusError, httpx.RequestError, KeyError):
            # Refresh failed, will need to re-authenticate
            return None

    def get_valid_token(self) -> str:
        """Get a valid access token, handling refresh and re-authentication as needed."""
        credentials = self._load_credentials()

        # If no credentials exist or token is expired, try to refresh or re-authenticate
        if not credentials or self._is_token_expired(credentials):
            if credentials:
                # Try to refresh the token first
                new_credentials = self._refresh_token(credentials)
                if new_credentials:
                    self._save_credentials(new_credentials)
                    return new_credentials["access_token"]

            # Refresh failed or no credentials, perform full authentication
            new_credentials = self._request_access_token()
            self._save_credentials(new_credentials)
            return new_credentials["access_token"]

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
