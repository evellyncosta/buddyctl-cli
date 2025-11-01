# Copyright 2024 Evellyn
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Prompt loading utilities for local templates."""

import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class PromptLoader:
    """
    Load prompts from local templates directory.

    Simple, zero-configuration prompt loading that works out-of-the-box.
    All prompts are included in the package distribution.

    Example:
        >>> loader = PromptLoader()
        >>> prompt = loader.load_prompt("code_agent")
        >>> print(prompt)
        "You are an expert coding assistant..."
    """

    def __init__(self):
        """Initialize prompt loader with local templates directory."""
        self.templates_dir = Path(__file__).parent / "templates"
        self._cache: Dict[str, str] = {}  # Cache prompts in memory
        logger.debug(f"PromptLoader initialized with templates_dir: {self.templates_dir}")

    def load_prompt(self, name: str, fallback: Optional[str] = None) -> str:
        """
        Load prompt from local templates.

        Args:
            name: Prompt name (e.g., "code_agent", "tool_instructions")
            fallback: Optional fallback text if template not found

        Returns:
            Prompt text from local template file

        Raises:
            FileNotFoundError: If template not found and no fallback provided

        Example:
            >>> loader = PromptLoader()
            >>> prompt = loader.load_prompt("code_agent")
        """
        # Check cache first
        if name in self._cache:
            logger.debug(f"Using cached prompt: {name}")
            return self._cache[name]

        # Load from local templates
        try:
            prompt = self._load_from_file(name)
            self._cache[name] = prompt
            logger.info(f"Loaded prompt '{name}' ({len(prompt)} chars)")
            return prompt
        except FileNotFoundError:
            if fallback:
                logger.warning(f"Template '{name}' not found, using fallback")
                return fallback
            else:
                raise FileNotFoundError(
                    f"Prompt template '{name}' not found in {self.templates_dir}. "
                    f"Available templates: {self.list_available_prompts()}"
                )

    def _load_from_file(self, name: str) -> str:
        """
        Load prompt from template file.

        Supports both formats:
        - "code_agent" → code_agent.md
        - "code-agent" → code_agent.md

        Args:
            name: Template name

        Returns:
            Template content

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        # Normalize name (convert - to _)
        normalized_name = name.replace("-", "_")

        # Try .md extension first
        file_path = self.templates_dir / f"{normalized_name}.md"

        if not file_path.exists():
            raise FileNotFoundError(f"Template file not found: {file_path}")

        logger.debug(f"Reading template from: {file_path}")
        return file_path.read_text(encoding="utf-8")

    def list_available_prompts(self) -> list[str]:
        """
        List all available prompt templates.

        Returns:
            List of template names (without .md extension)

        Example:
            >>> loader.list_available_prompts()
            ['code_agent', 'tool_instructions', 'error_recovery']
        """
        if not self.templates_dir.exists():
            return []

        templates = []
        for file_path in self.templates_dir.glob("*.md"):
            # Remove .md extension
            template_name = file_path.stem
            templates.append(template_name)

        return sorted(templates)

    def clear_cache(self) -> None:
        """Clear the prompt cache."""
        self._cache.clear()
        logger.debug("Prompt cache cleared")


__all__ = ["PromptLoader"]
