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

from typing import Any, Dict, Iterator, List, Optional
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
from ...cli.chat_client import ChatClient
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
    _chat_client: Optional[ChatClient] = None

    def __init__(self, **kwargs):
        """Initialize the StackSpot chat model.

        Args:
            **kwargs: Model configuration parameters
        """
        super().__init__(**kwargs)
        self._auth = StackSpotAuth()
        self._chat_client = ChatClient(self._auth)

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

        try:
            # Call StackSpot API (non-streaming)
            response = self._chat_client.chat_non_stream(self.agent_id, user_prompt)

            # Convert StackSpot response to LangChain format
            message = AIMessage(content=response.message)
            generation = ChatGeneration(message=message)

            return ChatResult(generations=[generation])

        except Exception as e:
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
            self._chat_client.chat_stream(self.agent_id, user_prompt, on_message=on_chunk)

            # Yield all collected chunks as one generation
            # (LangChain streaming can be optimized in future phases)
            full_content = "".join(chunks_buffer)
            chunk_message = AIMessageChunk(content=full_content)
            yield ChatGenerationChunk(message=chunk_message)

        except Exception as e:
            raise ValueError(f"StackSpot streaming error: {str(e)}")
