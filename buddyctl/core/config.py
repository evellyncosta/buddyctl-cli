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

    def get_current_provider(self) -> str:
        """Get the current LLM provider. Defaults to 'stackspot'."""
        config = self._load_config()
        return config.get("llm", {}).get("current_provider", "stackspot")

    def set_current_provider(self, provider: str) -> None:
        """Set the current LLM provider."""
        if not provider or not provider.strip():
            raise ConfigurationError("Provider name cannot be empty")

        config = self._load_config()

        # Initialize llm config if not exists
        if "llm" not in config:
            config["llm"] = {}

        config["llm"]["current_provider"] = provider.strip().lower()
        config["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._save_config(config)

    def get_provider_config(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific provider."""
        config = self._load_config()
        providers = config.get("llm", {}).get("providers", {})
        return providers.get(provider)

    def get_all_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get all provider configurations."""
        config = self._load_config()
        return config.get("llm", {}).get("providers", {})

    def initialize_default_providers(self) -> None:
        """Initialize default provider configurations if not present."""
        config = self._load_config()

        if "llm" not in config:
            config["llm"] = {
                "current_provider": "stackspot",
                "providers": {
                    "stackspot": {
                        "enabled": True,
                        "implemented": True,
                        "requires_credentials": ["STACKSPOT_CLIENT_ID", "STACKSPOT_CLIENT_SECRET", "STACKSPOT_REALM"]
                    },
                    "openai": {
                        "enabled": False,
                        "implemented": False,
                        "model": "gpt-4",
                        "requires_credentials": ["OPENAI_API_KEY"]
                    },
                    "anthropic": {
                        "enabled": False,
                        "implemented": False,
                        "model": "claude-3-5-sonnet-20241022",
                        "requires_credentials": ["ANTHROPIC_API_KEY"]
                    },
                    "google": {
                        "enabled": False,
                        "implemented": False,
                        "model": "gemini-pro",
                        "requires_credentials": ["GOOGLE_API_KEY"]
                    },
                    "ollama": {
                        "enabled": False,
                        "implemented": False,
                        "model": "llama2",
                        "base_url": "http://localhost:11434",
                        "requires_credentials": []
                    }
                }
            }
            config["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_config(config)

    def get_config_status(self) -> Dict[str, Any]:
        """Get current configuration status for display."""
        config = self._load_config()
        agent_id = config.get("default_agent_id")
        updated_at = config.get("updated_at")
        current_provider = self.get_current_provider()

        return {
            "has_default_agent": bool(agent_id),
            "default_agent_id": agent_id,
            "current_provider": current_provider,
            "updated_at": updated_at,
        }
