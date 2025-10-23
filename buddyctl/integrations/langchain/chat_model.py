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

"""LangChain wrapper for StackSpot AI."""

import json
import logging
from typing import Any, Callable, Dict, Iterator, List, Optional
import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.callbacks import CallbackManagerForLLMRun
from pydantic import ConfigDict, Field

from ...core.auth import StackSpotAuth
from ...core.config import BuddyConfig
from .utils import convert_langchain_messages_to_stackspot


class StackSpotChatModel(BaseChatModel):
    """LangChain wrapper for StackSpot AI.

    This wrapper allows using StackSpot AI agents as LangChain models,
    enabling integration with chains, tools, and the LangChain ecosystem.

    Note: Temperature and other model parameters are configured in the
    StackSpot Agent during creation, not adjustable via API at runtime.

    Example:
        ```python
        from buddyctl.langchain_integration import StackSpotChatModel

        model = StackSpotChatModel(
            agent_id="your-agent-id",
            streaming=False
        )

        response = model.invoke("Analyze this Python code")
        print(response.content)
        ```

    Attributes:
        agent_id: StackSpot Agent ID (required)
        model: Model identifier (default: "stackspot-ai")
        streaming: Enable SSE streaming (default: False for MVP)
        stackspot_knowledge: Use StackSpot Knowledge Sources (default: False)
        return_ks_in_response: Return Knowledge Sources in response (default: True)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    agent_id: str = Field(description="StackSpot Agent ID")
    model: str = Field(default="stackspot-ai", description="Model identifier")
    streaming: bool = Field(default=False, description="Enable SSE streaming (MVP uses False)")
    stackspot_knowledge: bool = Field(default=False, description="Use StackSpot Knowledge Sources")
    return_ks_in_response: bool = Field(
        default=True, description="Return Knowledge Sources in response"
    )

    # Internal clients (not exposed to Pydantic serialization)
    _auth: Optional[StackSpotAuth] = None
    _config: Optional[BuddyConfig] = None
    _logger: Optional[logging.Logger] = None

    def __init__(self, **kwargs):
        """Initialize the StackSpot chat model.

        Args:
            **kwargs: Model configuration parameters
        """
        super().__init__(**kwargs)
        self._auth = StackSpotAuth()
        self._config = BuddyConfig()
        self._logger = logging.getLogger(__name__)

    @property
    def _llm_type(self) -> str:
        """Return identifier for this LLM type.

        Returns:
            String identifier "stackspot-ai"
        """
        return "stackspot-ai"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return identifying parameters for this model.

        Returns:
            Dictionary with agent_id, model, and streaming parameters
        """
        return {
            "agent_id": self.agent_id,
            "model": self.model,
            "streaming": self.streaming,
        }

    def _get_api_base_url(self) -> str:
        """Get the StackSpot API base URL."""
        import os
        return os.getenv("STACKSPOT_API_URL", "https://genai-inference-app.stackspot.com")

    def _build_url(self, path: str) -> str:
        """Build API URL for StackSpot.

        Args:
            path: API endpoint path (e.g., "/v1/agent/{agent_id}/chat")

        Returns:
            Complete URL with base URL
        """
        base_url = self._get_api_base_url()
        if not path.startswith("/"):
            path = "/" + path
        return f"{base_url}{path}"

    def _get_headers(self, streaming: bool = False) -> dict:
        """Get request headers with authentication.

        Args:
            streaming: If True, add SSE-specific headers

        Returns:
            Dictionary with request headers
        """
        token = self._auth.get_valid_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        if streaming:
            headers.update({
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
            })

        return headers

    def _get_timeout_config(self, streaming: bool = False) -> httpx.Timeout:
        """Get timeout configuration for httpx client.

        Args:
            streaming: If True, configure for SSE streaming (no read timeout between chunks)

        Returns:
            httpx.Timeout object with appropriate settings

        Note:
            For streaming, we use read=None to avoid timeout between SSE chunks.
            The StackSpot API can take time to generate tokens, and setting a read
            timeout would close the connection prematurely.
        """
        if streaming:
            # For streaming: no timeout between chunks
            # Only timeout on initial connection
            return httpx.Timeout(
                connect=30.0,    # 30s to establish connection
                read=None,       # No timeout between SSE chunks (infinite)
                write=30.0,      # 30s to write request
                pool=30.0        # 30s for connection pool
            )
        else:
            # For non-streaming: 120s timeout (Judge Agent pode demorar)
            return httpx.Timeout(120.0)

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle HTTP error responses.

        Args:
            response: HTTP response object

        Raises:
            httpx.HTTPStatusError: With formatted error message
        """
        error_msg = response.text or f"HTTP {response.status_code}"

        if response.status_code == 403:
            error_msg = "Forbidden - Check your API credentials and permissions"
        elif response.status_code == 401:
            error_msg = "Unauthorized - Authentication failed. Try refreshing your token"
        elif response.status_code == 404:
            error_msg = f"Agent not found (ID: {self.agent_id})"

        raise httpx.HTTPStatusError(
            f"API error (status {response.status_code}): {error_msg}",
            request=response.request,
            response=response,
        )

    def _stream_sse(
        self,
        url: str,
        payload: dict,
        on_chunk: Callable[[str], None]
    ) -> None:
        """Stream Server-Sent Events from StackSpot API.

        Args:
            url: Full API URL
            payload: Request JSON body
            on_chunk: Callback function for each message chunk

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        headers = self._get_headers(streaming=True)

        # Use streaming-specific timeout configuration (no read timeout between chunks)
        timeout = self._get_timeout_config(streaming=True)

        with httpx.Client(timeout=timeout) as client:
            with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    self._handle_error_response(response)

                for line in response.iter_lines():
                    if not line or not line.strip():
                        continue

                    line = line.strip()

                    # SSE format: "data: {json}" or "data: [DONE]"
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix

                        # Skip ping/heartbeat messages
                        if not data or data == ":":
                            continue

                        # Handle end of stream
                        if data == "[DONE]":
                            break

                        try:
                            # Parse JSON response
                            response_data = json.loads(data)
                            message = response_data.get("message", "")

                            # Send message chunk if available
                            if message:
                                on_chunk(message)

                            # Check for stop condition
                            stop_reason = response_data.get("stop_reason")
                            if stop_reason and stop_reason != "null":
                                break

                            # Handle errors
                            error = response_data.get("error")
                            if error:
                                raise ValueError(f"API error: {error}")

                        except json.JSONDecodeError:
                            # If we can't parse as JSON, treat as raw text
                            on_chunk(data)

    def _post_json(self, url: str, payload: dict) -> dict:
        """Post JSON request and return JSON response.

        Args:
            url: Full API URL
            payload: Request JSON body

        Returns:
            Response JSON as dictionary

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        headers = self._get_headers()

        # Use non-streaming timeout configuration
        timeout = self._get_timeout_config(streaming=False)

        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                self._handle_error_response(response)

            return response.json()

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response (non-streaming mode).

        This method converts LangChain messages to StackSpot format and
        calls the StackSpot API to generate a response.

        Args:
            messages: List of messages in the conversation
            stop: Stop sequences (not supported by StackSpot API)
            run_manager: Callback manager for this run
            **kwargs: Additional parameters (ignored)

        Returns:
            ChatResult with the generated response

        Raises:
            ValueError: If StackSpot API call fails
        """
        # Convert LangChain messages to StackSpot format (single string)
        user_prompt = convert_langchain_messages_to_stackspot(messages)

        self._logger.debug(f"StackSpotChatModel: Calling agent {self.agent_id}")
        self._logger.debug(f"User prompt: {user_prompt[:200]}...")

        # Build URL and payload
        url = self._build_url(f"/v1/agent/{self.agent_id}/chat")
        payload = {
            "streaming": False,
            "user_prompt": user_prompt,
            "stackspot_knowledge": self.stackspot_knowledge,
            "return_ks_in_response": self.return_ks_in_response,
        }

        try:
            # Call StackSpot API (non-streaming)
            response_data = self._post_json(url, payload)

            # Validate response
            if response_data is None:
                raise ValueError("StackSpot API returned None response")

            # Convert StackSpot response to LangChain format
            message_content = response_data.get("message")

            # Check if message is None (content filter issue)
            if message_content is None:
                self._logger.warning(f"StackSpot returned null message. Full response: {response_data}")
                # Try to extract useful info from response
                tokens = response_data.get("tokens", {})
                output_tokens = tokens.get("output", 0) if tokens else 0

                error_msg = (
                    f"StackSpot returned null message (likely filtered by content policy). "
                    f"Output tokens generated: {output_tokens}. "
                    f"This usually happens with Judge Agents. Consider using direct validation instead."
                )
                raise ValueError(error_msg)

            self._logger.debug(f"StackSpot response: {message_content[:200]}...")

            message = AIMessage(content=message_content)
            generation = ChatGeneration(message=message)

            return ChatResult(generations=[generation])

        except Exception as e:
            self._logger.error(f"StackSpot API error: {str(e)}")
            raise ValueError(f"StackSpot API error: {str(e)}")

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Generate response (streaming mode).

        This method converts LangChain messages to StackSpot format and
        uses Server-Sent Events (SSE) to stream the response token by token.

        Note: For MVP, streaming is disabled by default. This method is
        implemented for future phases.

        Args:
            messages: List of messages in the conversation
            stop: Stop sequences (not supported by StackSpot API)
            run_manager: Callback manager for this run
            **kwargs: Additional parameters (ignored)

        Yields:
            ChatGenerationChunk for each token received

        Raises:
            ValueError: If StackSpot streaming API call fails
        """
        # Convert messages to StackSpot format
        user_prompt = convert_langchain_messages_to_stackspot(messages)

        # Build URL and payload
        url = self._build_url(f"/v1/agent/{self.agent_id}/chat")
        payload = {
            "streaming": True,
            "user_prompt": user_prompt,
            "stackspot_knowledge": self.stackspot_knowledge,
            "return_ks_in_response": self.return_ks_in_response,
        }

        # Storage for chunks received from streaming
        chunks_buffer = []

        def on_chunk(chunk: str):
            """Callback invoked for each chunk received from SSE stream.

            Args:
                chunk: Text chunk received from StackSpot API
            """
            chunks_buffer.append(chunk)

            # Notify callback manager if available
            if run_manager:
                run_manager.on_llm_new_token(chunk)

        try:
            # Call StackSpot streaming API
            self._stream_sse(url, payload, on_chunk)

            # Yield all collected chunks as one generation
            # (LangChain streaming can be optimized in future phases)
            full_content = "".join(chunks_buffer)
            chunk_message = AIMessageChunk(content=full_content)
            yield ChatGenerationChunk(message=chunk_message)

        except Exception as e:
            raise ValueError(f"StackSpot streaming error: {str(e)}")
