"""OpenAI adapter (stub - not yet implemented)."""

import os
from typing import Iterator, Optional
from langchain_core.messages import HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel

from ...config import BuddyConfig
from ..base import ChatMessage, ChatResponse


class OpenAIAdapter:
    """
    Adapter para OpenAI API - usa ChatOpenAI (LangChain).

    Status: STUB - Not yet implemented
    Para usar, instale: pip install langchain-openai

    Example (futuro):
        ```python
        config = BuddyConfig()
        adapter = OpenAIAdapter(config)

        if adapter.is_available():
            messages = [ChatMessage(content="Hello!", role="user")]
            response = adapter.chat(messages)
            print(response.content)
        ```
    """

    def __init__(self, config: BuddyConfig):
        """
        Initialize OpenAI adapter.

        Args:
            config: BuddyConfig instance for accessing configuration
        """
        self.config = config
        self._model: Optional[BaseChatModel] = None

    @property
    def name(self) -> str:
        """Nome do provider."""
        return "openai"

    @property
    def langchain_model(self) -> BaseChatModel:
        """
        Retorna o ChatOpenAI configurado.

        Returns:
            BaseChatModel: ChatOpenAI instance

        Raises:
            NotImplementedError: Provider ainda não implementado
        """
        if self._model is None:
            # TODO: Implementar quando adicionar suporte OpenAI
            # from langchain_openai import ChatOpenAI
            # provider_config = self.config.get_provider_config("openai")
            # model_name = provider_config.get("model", "gpt-4") if provider_config else "gpt-4"
            #
            # self._model = ChatOpenAI(
            #     model=model_name,
            #     streaming=True,
            #     temperature=0.7,
            # )
            raise NotImplementedError(
                "OpenAI provider is not implemented yet. "
                "Please use 'stackspot' provider for now."
            )

        return self._model

    def is_available(self) -> bool:
        """
        Verifica se OpenAI está configurado.

        Returns:
            bool: True se OPENAI_API_KEY está presente
        """
        return bool(os.getenv("OPENAI_API_KEY"))

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        """
        Valida credenciais OpenAI.

        Returns:
            tuple: (success: bool, error_message: Optional[str])
        """
        if not self.is_available():
            return False, "OPENAI_API_KEY not found in environment"

        # TODO: Implementar teste real de API quando provider for implementado
        return False, "OpenAI provider not yet implemented"

    def chat_stream(
        self,
        messages: list[ChatMessage],
        **kwargs
    ) -> Iterator[str]:
        """
        Implementa chat streaming usando ChatOpenAI.

        Args:
            messages: Lista de mensagens para enviar
            **kwargs: Parâmetros adicionais

        Yields:
            str: Chunks da resposta streaming

        Raises:
            NotImplementedError: Provider ainda não implementado
        """
        raise NotImplementedError(
            "OpenAI provider is not implemented yet. "
            "Please use 'stackspot' provider for now."
        )

    def chat(
        self,
        messages: list[ChatMessage],
        **kwargs
    ) -> ChatResponse:
        """
        Implementa chat non-streaming usando ChatOpenAI.

        Args:
            messages: Lista de mensagens para enviar
            **kwargs: Parâmetros adicionais

        Returns:
            ChatResponse: Resposta completa

        Raises:
            NotImplementedError: Provider ainda não implementado
        """
        raise NotImplementedError(
            "OpenAI provider is not implemented yet. "
            "Please use 'stackspot' provider for now."
        )

    def handle_error(self, error: Exception) -> str:
        """
        Mapeia erros OpenAI.

        Args:
            error: Exceção capturada

        Returns:
            str: Mensagem de erro amigável
        """
        error_str = str(error)

        if "rate_limit" in error_str.lower():
            return "Rate limit exceeded. Please try again later."
        elif "invalid_api_key" in error_str.lower():
            return "Invalid API key. Check your OPENAI_API_KEY."
        elif "not implemented" in error_str.lower():
            return "OpenAI provider is not implemented yet. Use 'stackspot' instead."
        else:
            return f"OpenAI error: {error_str}"
