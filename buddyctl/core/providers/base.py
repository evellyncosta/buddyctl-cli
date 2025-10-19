"""Base protocol and data models for provider adapters."""

from typing import Protocol, Iterator, Optional, runtime_checkable, List, Union, Dict, Any
from dataclasses import dataclass
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool


@dataclass
class ChatMessage:
    """Formato universal de mensagem entre providers."""

    content: str
    role: str = "user"  # user, assistant, system


@dataclass
class ChatResponse:
    """Formato universal de resposta entre providers."""

    content: str
    stop_reason: Optional[str] = None
    usage: Optional[dict] = None
    error: Optional[str] = None


@runtime_checkable
class ProviderAdapter(Protocol):
    """
    Protocol para adapters de providers de LLM.

    Todos os adapters devem implementar estes métodos.
    Não é necessário herdar desta classe - Python usa duck typing.
    Use @runtime_checkable para validação opcional em runtime.

    Example:
        ```python
        class MyAdapter:
            @property
            def name(self) -> str:
                return "my_provider"

            # ... implement other methods

        # Automatically valid as ProviderAdapter!
        adapter: ProviderAdapter = MyAdapter()
        ```
    """

    @property
    def name(self) -> str:
        """Nome do provider (stackspot, openai, etc.)."""
        ...

    @property
    def langchain_model(self) -> BaseChatModel:
        """Retorna o modelo LangChain configurado para este provider."""
        ...

    def is_available(self) -> bool:
        """Verifica se o provider está configurado e disponível."""
        ...

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        """
        Valida credenciais do provider.

        Returns:
            tuple: (success: bool, error_message: Optional[str])
        """
        ...

    def chat_stream(
        self,
        messages: list[ChatMessage],
        **kwargs
    ) -> Iterator[str]:
        """
        Envia mensagens e retorna stream de resposta (via LangChain).

        Args:
            messages: Lista de mensagens para enviar
            **kwargs: Parâmetros adicionais específicos do provider

        Yields:
            str: Chunks da resposta streaming
        """
        ...

    def chat(
        self,
        messages: list[ChatMessage],
        **kwargs
    ) -> ChatResponse:
        """
        Envia mensagens e retorna resposta completa (via LangChain).

        Args:
            messages: Lista de mensagens para enviar
            **kwargs: Parâmetros adicionais específicos do provider

        Returns:
            ChatResponse: Resposta completa do provider
        """
        ...

    def handle_error(self, error: Exception) -> str:
        """
        Mapeia erros específicos do provider para mensagens amigáveis.

        Args:
            error: Exceção capturada

        Returns:
            str: Mensagem de erro amigável
        """
        ...

    def supports_native_tools(self) -> bool:
        """
        Indica se o provider tem suporte nativo a function calling.

        Returns:
            True: Provider tem API nativa (OpenAI, Anthropic)
            False: Provider requer estratégia alternativa (StackSpot)

        Example:
            >>> stackspot_adapter.supports_native_tools()
            False
            >>> openai_adapter.supports_native_tools()
            True
        """
        ...

    def get_model_with_tools(
        self,
        tools: List[BaseTool]
    ) -> Union[BaseChatModel, "ExecutorProtocol"]:
        """
        Retorna modelo/executor com tools configurados.

        IMPORTANTE: Tool calling é SEMPRE ativo e transparente.
        Provider decide internamente qual estratégia usar (Judge, Chain, Native).

        Args:
            tools: Lista de tools disponíveis

        Returns:
            Executor com interface .invoke(user_input) -> result

        Raises:
            ValueError: Se provider não está configurado corretamente

        Example:
            >>> from buddyctl.integrations.langchain.tools import read_file, apply_diff
            >>> tools = [read_file, apply_diff]
            >>> executor = provider.get_model_with_tools(tools)
            >>> result = executor.invoke("Read calculator.py")
            >>> print(result["output"])
        """
        ...


@runtime_checkable
class ExecutorProtocol(Protocol):
    """
    Interface comum para executores/chains.

    Chains (StackSpotChain, ReActExecutor) e AgentExecutor implementam esta interface.
    Permite uso transparente de diferentes estratégias de tool calling.

    Example:
        >>> executor = provider.get_model_with_tools(tools)
        >>> result = executor.invoke("Read file and modify")
        >>> print(result["output"])
    """

    def invoke(self, user_input: str) -> Dict[str, Any]:
        """
        Execute workflow.

        Args:
            user_input: User request

        Returns:
            {
                "output": str,              # Final response
                "tool_calls_made": List,    # Tools executed
                "iterations": int           # Number of cycles
            }

        Example:
            >>> result = executor.invoke("Read calculator.py")
            >>> print(result["output"])
            >>> print(f"Tools used: {len(result['tool_calls_made'])}")
        """
        ...
