"""Configuration management for buddyctl."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Any


class ConfigurationError(Exception):
    """Raised when configuration operations fail."""

    pass


class BuddyConfig:
    """Configuration manager for buddyctl settings."""

    def __init__(self):
        self.config_path = Path.home() / ".buddyctl" / "config.json"

    def _ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists with proper permissions."""
        config_dir = self.config_path.parent
        config_dir.mkdir(mode=0o700, exist_ok=True)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from disk."""
        if not self.config_path.exists():
            return {}

        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to disk with secure permissions."""
        self._ensure_config_dir()

        try:
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=2)

            # Set secure permissions (owner read/write only)
            os.chmod(self.config_path, 0o600)
        except IOError as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")

    def get_default_agent_id(self) -> Optional[str]:
        """Get the configured default agent ID."""
        config = self._load_config()
        return config.get("default_agent_id")

    def set_default_agent_id(self, agent_id: str) -> None:
        """Set the default agent ID."""
        if not agent_id or not agent_id.strip():
            raise ConfigurationError("Agent ID cannot be empty")

        config = self._load_config()
        config["default_agent_id"] = agent_id.strip()
        config["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._save_config(config)

    def remove_default_agent_id(self) -> None:
        """Remove the default agent ID configuration."""
        config = self._load_config()
        config.pop("default_agent_id", None)
        config["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._save_config(config)

    def get_config_status(self) -> Dict[str, Any]:
        """Get current configuration status for display."""
        config = self._load_config()
        agent_id = config.get("default_agent_id")
        updated_at = config.get("updated_at")

        return {
            "has_default_agent": bool(agent_id),
            "default_agent_id": agent_id,
            "updated_at": updated_at,
        }
