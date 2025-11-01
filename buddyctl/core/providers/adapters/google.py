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

"""Google Gemini Provider Adapter."""

import logging
import os
from typing import Iterator, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from ..base import ChatMessage, ChatResponse, ExecutorProtocol


class GoogleAdapter:
    """
    Provider adapter for Google Gemini.

    Features:
    - Native function calling (Gemini 1.5+)
    - 2M token context (gemini-1.5-pro)
    - Fast inference (gemini-1.5-flash)
    - Safety filters
    - System prompt via PromptedToolExecutor

    Architecture:
    - Uses PromptedToolExecutor (Feature 31) for tool calling
    - Uses BASIC_TOOLS (Feature 30) for file operations
    - LLM decides when to call tools autonomously

    Example:
        >>> from buddyctl.core.config import BuddyConfig
        >>> config = BuddyConfig()
        >>> adapter = GoogleAdapter(config)
        >>>
        >>> if adapter.is_available():
        >>>     executor = adapter.get_model_with_tools(BASIC_TOOLS)
        >>>     result = executor.invoke("Add logging to calculator.py")
    """

    def __init__(self, config):
        """
        Initialize Google Gemini adapter.

        Args:
            config: BuddyConfig instance
        """
        self.config = config
        self._model = None
        self.interactive_mode = False  # Feature 33: Dynamic prompts
        self.logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        """Provider name."""
        return "google"

    @property
    def langchain_model(self) -> BaseChatModel:
        """
        Get ChatGoogleGenerativeAI model instance.

        Lazy initialization with caching.

        Gemini-specific configurations:
        - convert_system_message_to_human=True (Gemini doesn't support system messages natively)
        - temperature=0.7 (balanced creativity)
        - max_output_tokens=8192 (max response length)

        Returns:
            ChatGoogleGenerativeAI instance

        Raises:
            ValueError: If GOOGLE_API_KEY not set
            ImportError: If langchain-google-genai not installed
        """
        if self._model is None:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
            except ImportError:
                raise ImportError(
                    "langchain-google-genai is required for Google Gemini. "
                    "Install with: pip install langchain-google-genai"
                )

            provider_config = self.config.get_provider_config("google")
            model_name = (
                provider_config.get("model", "gemini-2.0-flash-exp")
                if provider_config
                else "gemini-2.0-flash-exp"
            )

            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError(
                    "GOOGLE_API_KEY environment variable not set. "
                    "Get an API key at: https://makersuite.google.com/app/apikey"
                )

            self.logger.info(f"Initializing Google Gemini model: {model_name}")

            self._model = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.7,
                convert_system_message_to_human=True,  # Gemini-specific
                max_output_tokens=8192,
            )

        return self._model

    def is_available(self) -> bool:
        """
        Check if Google Gemini is available.

        Checks:
        1. GOOGLE_API_KEY environment variable is set
        2. langchain-google-genai package is installed

        Returns:
            True if available, False otherwise
        """
        # Check API key
        if not os.getenv("GOOGLE_API_KEY"):
            self.logger.warning("Google Gemini not available: GOOGLE_API_KEY not set")
            return False

        # Check package
        try:
            import langchain_google_genai
            return True
        except ImportError:
            self.logger.warning(
                "Google Gemini not available: langchain-google-genai not installed"
            )
            return False

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        """
        Validate Google API credentials.

        Performs a simple API call to verify the key works.

        Returns:
            (is_valid, error_message)
            - (True, None) if valid
            - (False, "error message") if invalid
        """
        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            return (False, "GOOGLE_API_KEY environment variable not set")

        if not api_key.startswith("AIza"):
            return (
                False,
                "Invalid API key format (should start with 'AIza'). "
                "Get a key at: https://makersuite.google.com/app/apikey"
            )

        # Try a simple API call
        try:
            model = self.langchain_model
            response = model.invoke([HumanMessage(content="Hello")])

            if response and response.content:
                self.logger.info("Google Gemini credentials validated successfully")
                return (True, None)
            else:
                return (False, "API returned empty response")

        except Exception as e:
            error_msg = self.handle_error(e)
            return (False, error_msg)

    def chat_stream(self, messages: list[ChatMessage], **kwargs) -> Iterator[str]:
        """
        Stream chat response from Google Gemini.

        Args:
            messages: List of chat messages
            **kwargs: Additional arguments (ignored)

        Yields:
            Response chunks as strings

        Example:
            >>> for chunk in adapter.chat_stream(messages):
            >>>     print(chunk, end="", flush=True)
        """
        # Convert to LangChain messages
        lc_messages = []
        for msg in messages:
            if msg.role == "user":
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                lc_messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                # Gemini doesn't support system messages - handled by convert_system_message_to_human
                lc_messages.append(SystemMessage(content=msg.content))

        model = self.langchain_model

        try:
            for chunk in model.stream(lc_messages):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            error_msg = self.handle_error(e)
            self.logger.error(f"Gemini streaming error: {error_msg}")
            raise RuntimeError(f"Gemini streaming error: {error_msg}") from e

    def chat(self, messages: list[ChatMessage], **kwargs) -> ChatResponse:
        """
        Non-streaming chat with Google Gemini.

        Args:
            messages: List of chat messages
            **kwargs: Additional arguments (ignored)

        Returns:
            ChatResponse with full response
        """
        # Convert to LangChain messages
        lc_messages = []
        for msg in messages:
            if msg.role == "user":
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                lc_messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                lc_messages.append(SystemMessage(content=msg.content))

        model = self.langchain_model

        try:
            response = model.invoke(lc_messages)

            return ChatResponse(
                content=response.content,
                stop_reason=None,
                error=None
            )

        except Exception as e:
            error_msg = self.handle_error(e)
            self.logger.error(f"Gemini chat error: {error_msg}")
            raise RuntimeError(f"Gemini chat error: {error_msg}") from e

    def handle_error(self, error: Exception) -> str:
        """
        Map Gemini errors to user-friendly messages.

        Common errors:
        - Invalid API key
        - Quota exceeded
        - Safety filter blocks
        - Permission denied
        - Model not found

        Args:
            error: Exception from Gemini API

        Returns:
            Friendly error message
        """
        error_str = str(error).lower()

        # API key errors
        if "api_key" in error_str or "api key" in error_str:
            return (
                "Invalid API key. Check your GOOGLE_API_KEY environment variable.\n"
                "Get an API key at: https://makersuite.google.com/app/apikey"
            )

        # Quota/rate limit errors
        if "quota" in error_str or "rate" in error_str:
            return (
                "Quota exceeded. Check your Google Cloud quota limits.\n"
                "Visit: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas"
            )

        # Permission errors
        if "permission" in error_str or "forbidden" in error_str:
            return (
                "Permission denied. Ensure Gemini API is enabled in your Google Cloud project.\n"
                "Enable at: https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com"
            )

        # Safety filter errors
        if "safety" in error_str or "blocked" in error_str:
            return (
                "Content blocked by safety filters. Try rephrasing your request.\n"
                "Gemini has strict content policies to prevent harmful outputs."
            )

        # Model not found
        if "model" in error_str and ("not found" in error_str or "invalid" in error_str):
            return (
                "Model not found. Check your configured model name.\n"
                "Supported models: gemini-1.5-pro, gemini-1.5-flash"
            )

        # Generic error
        return f"Gemini API error: {error}"

    def supports_native_tools(self) -> bool:
        """
        Check if provider supports native function calling.

        Gemini 1.5+ has native function calling support.

        Returns:
            True (Gemini supports native tools)
        """
        return True

    def set_interactive_mode(self, enabled: bool) -> None:
        """
        Set interactive mode for this adapter (Feature 33).

        When enabled, uses code_agent_interactive.md prompt template.
        When disabled, uses code_agent_auto.md prompt template.

        Args:
            enabled: True for interactive mode, False for auto-apply mode
        """
        self.interactive_mode = enabled
        self.logger.debug(f"Interactive mode set to: {enabled}")

    def get_model_with_tools(self, tools: List[BaseTool]) -> ExecutorProtocol:
        """
        Get model with tools bound (native function calling + system prompt).

        Uses PromptedToolExecutor (Feature 31) which:
        1. Loads system prompt from local templates
        2. Binds tools to LLM model
        3. LLM decides when to call tools
        4. Executes tools automatically
        5. Returns results in standard format

        Args:
            tools: List of LangChain tools (e.g., BASIC_TOOLS)

        Returns:
            PromptedToolExecutor instance

        Example:
            >>> from buddyctl.integrations.langchain.tools import BASIC_TOOLS
            >>> executor = adapter.get_model_with_tools(BASIC_TOOLS)
            >>> result = executor.invoke("Add comments to @calculator.py")
            >>> print(result["output"])
        """
        from ....integrations.langchain.executors import PromptedToolExecutor

        # Get LangChain model
        model = self.langchain_model

        # Bind tools to model (Gemini native function calling)
        self.logger.info(f"Binding {len(tools)} tools to Gemini model")
        model_with_tools = model.bind_tools(tools)

        # Select prompt based on interactive mode (Feature 33: Dynamic Prompts)
        prompt_name = (
            "code_agent_interactive" if self.interactive_mode
            else "code_agent_auto"
        )
        self.logger.info(
            f"Using prompt: {prompt_name} (interactive_mode={self.interactive_mode})"
        )

        # Wrap in PromptedToolExecutor (adds system prompt from local templates)
        return PromptedToolExecutor(
            model=model_with_tools,
            tools=tools,
            prompt_name=prompt_name  # Dynamic prompt selection
        )


__all__ = ["GoogleAdapter"]
