"""Provider manager for handling multiple LLM providers transparently."""

from typing import Iterator
from langchain_core.language_models.chat_models import BaseChatModel

from ..config import BuddyConfig
from .base import ProviderAdapter, ChatMessage, ChatResponse


class ProviderManager:
    """
    Gerenciador central de providers de LLM.

    Responsável por:
    - Selecionar o provider correto baseado na configuração
    - Rotear mensagens para o adapter apropriado
    - Fornecer interface unificada para a aplicação

    Example:
        ```python
        config = BuddyConfig()
        manager = ProviderManager(config)

        # Simple chat
        for chunk in manager.chat_stream("Hello!"):
            print(chunk, end="")

        # Advanced LangChain usage
        llm = manager.get_langchain_model()
        agent = create_react_agent(llm, tools)
        ```
    """

    def __init__(self, config: BuddyConfig, auth=None):
        """
        Initialize provider manager.

        Args:
            config: BuddyConfig instance for accessing configuration
            auth: Optional auth instance to share with adapters (e.g., StackSpotAuth)
        """
        self.config = config
        self.auth = auth
        self._adapters: dict[str, ProviderAdapter] = {}
        self._register_adapters()

    def _register_adapters(self):
        """Registra todos os adapters disponíveis."""
        from .adapters.stackspot import StackSpotAdapter
        # from .adapters.openai import OpenAIAdapter  # Futuro
        # from .adapters.anthropic import AnthropicAdapter  # Futuro

        self._adapters = {
            "stackspot": StackSpotAdapter(self.config, auth=self.auth),
            # "openai": OpenAIAdapter(self.config),
            # "anthropic": AnthropicAdapter(self.config),
        }

    def get_adapter(self, provider_name: str) -> ProviderAdapter:
        """
        Get adapter for specified provider (Feature 17).

        Args:
            provider_name: Provider name (stackspot, openai, etc.)

        Returns:
            ProviderAdapter instance

        Raises:
            ValueError: If provider not found or not available
            TypeError: If adapter doesn't implement ProviderAdapter protocol

        Example:
            >>> manager = ProviderManager(config)
            >>> adapter = manager.get_adapter("stackspot")
            >>> tools = [read_file, apply_diff]
            >>> executor = adapter.get_model_with_tools(tools)
            >>> result = executor.invoke("Read file")
        """
        if provider_name not in self._adapters:
            available = ", ".join(self._adapters.keys())
            raise ValueError(
                f"Unknown provider: '{provider_name}'. "
                f"Available providers: {available}"
            )

        adapter = self._adapters[provider_name]

        # Validação opcional em runtime (graças ao @runtime_checkable)
        if not isinstance(adapter, ProviderAdapter):
            raise TypeError(
                f"Adapter '{provider_name}' doesn't implement ProviderAdapter protocol"
            )

        if not adapter.is_available():
            raise ValueError(
                f"Provider '{provider_name}' is not available. "
                "Check credentials and configuration."
            )

        return adapter

    def get_current_adapter(self) -> ProviderAdapter:
        """
        Retorna o adapter do provider atualmente configurado.

        Returns:
            ProviderAdapter: Adapter do provider atual

        Raises:
            ValueError: Se provider é desconhecido ou não disponível
            TypeError: Se adapter não implementa ProviderAdapter protocol
        """
        provider_name = self.config.get_current_provider()
        return self.get_adapter(provider_name)

    def chat_stream(
        self,
        message: str,
        **kwargs
    ) -> Iterator[str]:
        """
        Envia mensagem usando provider atual (streaming).

        Args:
            message: Mensagem do usuário
            **kwargs: Parâmetros adicionais específicos do provider

        Yields:
            str: Chunks da resposta streaming

        Raises:
            RuntimeError: Se ocorrer erro durante o chat
        """
        adapter = self.get_current_adapter()

        # Converte string simples em formato de mensagem
        messages = [ChatMessage(content=message, role="user")]

        try:
            yield from adapter.chat_stream(messages, **kwargs)
        except Exception as e:
            # Mapeia erro específico do provider
            error_msg = adapter.handle_error(e)
            raise RuntimeError(f"Chat error: {error_msg}") from e

    def chat(self, message: str, **kwargs) -> ChatResponse:
        """
        Envia mensagem usando provider atual (non-streaming).

        Args:
            message: Mensagem do usuário
            **kwargs: Parâmetros adicionais específicos do provider

        Returns:
            ChatResponse: Resposta completa

        Raises:
            RuntimeError: Se ocorrer erro durante o chat
        """
        adapter = self.get_current_adapter()

        # Converte string simples em formato de mensagem
        messages = [ChatMessage(content=message, role="user")]

        try:
            return adapter.chat(messages, **kwargs)
        except Exception as e:
            # Mapeia erro específico do provider
            error_msg = adapter.handle_error(e)
            raise RuntimeError(f"Chat error: {error_msg}") from e

    def get_langchain_model(self) -> BaseChatModel:
        """
        Retorna o modelo LangChain do provider atual.

        Útil para uso avançado com LangChain (agents, tools, chains).

        Returns:
            BaseChatModel: Modelo LangChain do provider atual

        Example:
            ```python
            manager = ProviderManager(config)
            llm = manager.get_langchain_model()

            # Use with LangChain
            from langchain.agents import create_react_agent
            agent = create_react_agent(llm, tools, prompt)
            ```
        """
        adapter = self.get_current_adapter()
        return adapter.langchain_model

    def list_available_providers(self) -> list[str]:
        """
        Lista todos os providers registrados.

        Returns:
            list[str]: Nomes dos providers disponíveis
        """
        return list(self._adapters.keys())

    def get_provider_status(self, provider_name: str) -> dict:
        """
        Obtém status de um provider específico.

        Args:
            provider_name: Nome do provider

        Returns:
            dict: Status com keys: name, available, credentials_valid, error

        Example:
            ```python
            status = manager.get_provider_status("stackspot")
            if status["available"]:
                print(f"{status['name']} is ready!")
            ```
        """
        if provider_name not in self._adapters:
            return {
                "name": provider_name,
                "available": False,
                "credentials_valid": False,
                "error": "Provider not registered"
            }

        adapter = self._adapters[provider_name]

        is_available = adapter.is_available()
        creds_valid, creds_error = adapter.validate_credentials()

        return {
            "name": adapter.name,
            "available": is_available,
            "credentials_valid": creds_valid,
            "error": creds_error
        }
