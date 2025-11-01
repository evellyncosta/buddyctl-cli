"""StackSpot AI adapter using LangChain integration."""

from typing import Iterator, Optional, List, Union
from langchain_core.messages import HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
import logging
import os

from ....integrations.langchain.chat_model import StackSpotChatModel
from ...auth import StackSpotAuth
from ...config import BuddyConfig
from ..base import ChatMessage, ChatResponse, ExecutorProtocol


class StackSpotAdapter:
    """
    Adapter para StackSpot AI - usa StackSpotChatModel (LangChain).

    Note: Não herda de ProviderAdapter - apenas implementa os métodos!
    Python Protocol usa duck typing: se tem os métodos, é válido.

    Example:
        ```python
        config = BuddyConfig()
        adapter = StackSpotAdapter(config)

        if adapter.is_available():
            messages = [ChatMessage(content="Hello!", role="user")]
            for chunk in adapter.chat_stream(messages):
                print(chunk, end="")
        ```
    """

    def __init__(self, config: BuddyConfig, auth: Optional[StackSpotAuth] = None):
        """
        Initialize StackSpot adapter.

        Args:
            config: BuddyConfig instance for accessing configuration
            auth: Optional StackSpotAuth instance (creates new if not provided)
        """
        self.config = config
        self.auth = auth or StackSpotAuth()
        self._model: Optional[StackSpotChatModel] = None
        self.file_indexer = None  # Will be set by InteractiveShell
        self.interactive_mode = False  # Feature 34: Interactive mode
        self.logger = logging.getLogger(__name__)

    def set_file_indexer(self, file_indexer) -> None:
        """
        Set file indexer for NEW_FILE support.

        Args:
            file_indexer: FileIndexer instance
        """
        self.file_indexer = file_indexer

    def set_interactive_mode(self, enabled: bool) -> None:
        """
        Enable or disable interactive mode (Feature 34).

        Args:
            enabled: True to enable interactive preview/review, False for auto-apply
        """
        self.interactive_mode = enabled
        self.logger.debug(f"Interactive mode: {enabled}")

    @property
    def name(self) -> str:
        """Nome do provider."""
        return "stackspot"

    @property
    def langchain_model(self) -> BaseChatModel:
        """
        Retorna o StackSpotChatModel configurado.

        Returns:
            BaseChatModel: StackSpotChatModel instance

        Raises:
            ValueError: Se agent_id não está configurado
        """
        if self._model is None:
            agent_id = self.config.get_default_agent_id()
            if not agent_id:
                raise ValueError(
                    "No default agent_id configured for StackSpot. "
                    "Use /agent-default <id> to set one."
                )

            self._model = StackSpotChatModel(
                agent_id=agent_id,
                streaming=True
            )

        return self._model

    def is_available(self) -> bool:
        """
        Verifica se StackSpot está configurado e autenticado.

        Returns:
            bool: True se autenticado e pronto para uso
        """
        try:
            # Attempt to get a valid token - this will trigger refresh if needed
            self.auth.get_valid_token()
            return True
        except Exception:
            return False

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        """
        Valida credenciais do StackSpot.

        Returns:
            tuple: (success: bool, error_message: Optional[str])
        """
        try:
            # Attempt to get a valid token - this will trigger refresh if needed
            self.auth.get_valid_token()

            # Verifica também se tem agent_id
            agent_id = self.config.get_default_agent_id()
            if not agent_id:
                return False, "No default agent_id configured"
            return True, None
        except Exception as e:
            return False, f"Authentication failed: {str(e)}"

    def chat_stream(
        self,
        messages: list[ChatMessage],
        **kwargs
    ) -> Iterator[str]:
        """
        Implementa chat streaming usando StackSpotChatModel.

        Args:
            messages: Lista de mensagens para enviar
            **kwargs: Parâmetros adicionais (agent_id pode sobrescrever default)

        Yields:
            str: Chunks da resposta streaming

        Raises:
            RuntimeError: Se ocorrer erro durante streaming
        """
        # Converte ChatMessage para formato LangChain
        lc_messages = [
            HumanMessage(content=msg.content)
            for msg in messages
        ]

        # Usa o modelo LangChain para streaming
        model = self.langchain_model

        try:
            for chunk in model.stream(lc_messages):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            raise RuntimeError(f"StackSpot streaming error: {e}") from e

    def chat(
        self,
        messages: list[ChatMessage],
        **kwargs
    ) -> ChatResponse:
        """
        Implementa chat non-streaming usando StackSpotChatModel.

        Args:
            messages: Lista de mensagens para enviar
            **kwargs: Parâmetros adicionais (agent_id pode sobrescrever default)

        Returns:
            ChatResponse: Resposta completa

        Raises:
            RuntimeError: Se ocorrer erro durante chat
        """
        # Converte ChatMessage para formato LangChain
        lc_messages = [
            HumanMessage(content=msg.content)
            for msg in messages
        ]

        # Usa o modelo LangChain
        model = self.langchain_model

        try:
            response = model.invoke(lc_messages)

            return ChatResponse(
                content=response.content,
                stop_reason=None,  # LangChain abstrai isso
                error=None,
            )
        except Exception as e:
            raise RuntimeError(f"StackSpot error: {e}") from e

    def handle_error(self, error: Exception) -> str:
        """
        Mapeia erros do StackSpot para mensagens amigáveis.

        Args:
            error: Exceção capturada

        Returns:
            str: Mensagem de erro amigável
        """
        error_str = str(error)

        # Mapeia erros HTTP comuns
        if "403" in error_str or "Forbidden" in error_str:
            return "Access denied. Check your credentials and permissions."
        elif "401" in error_str or "Unauthorized" in error_str:
            return "Authentication expired. Please re-authenticate."
        elif "404" in error_str or "not found" in error_str.lower():
            return "Agent not found. Check your agent ID configuration."
        elif "agent_id" in error_str.lower() and "not configured" in error_str.lower():
            return "No agent_id configured. Use /agent-default <id> to set one."
        else:
            return f"StackSpot error: {error_str}"

    def supports_native_tools(self) -> bool:
        """
        StackSpot não tem API nativa de function calling.

        Returns:
            False: StackSpot requer estratégia alternativa (Judge Agent)
        """
        return False

    def get_model_with_tools(
        self,
        tools: List[BaseTool]
    ) -> ExecutorProtocol:
        """
        Retorna executor com tools para StackSpot.

        StackSpot agora usa SEARCH/REPLACE pattern (single-stage):
        - Sempre usa StackSpotChain (SEARCH/REPLACE + validação local)
        - Remove Judge Agent (não funciona, conforme POCs 2 e 3)

        Args:
            tools: Lista de tools disponíveis

        Returns:
            ExecutorProtocol: StackSpotChain configurado

        Raises:
            ValueError: Se configuração está incorreta
        """
        main_agent_id = self.config.get_default_agent_id()

        if not main_agent_id:
            raise ValueError(
                "No default agent_id configured for StackSpot. "
                "Use /agent-default <id> to set one."
            )

        # Always use StackSpotChain with SEARCH/REPLACE pattern
        self.logger.info(f"Using StackSpotChain (SEARCH/REPLACE mode) with agent: {main_agent_id}")
        return self._create_stackspot_chain(
            main_agent_id=main_agent_id,
            tools=tools
        )


    def _create_stackspot_chain(
        self,
        main_agent_id: str,
        tools: List[BaseTool]
    ) -> "StackSpotChain":
        """Create StackSpot Chain (SEARCH/REPLACE pattern - single stage)."""
        from ....integrations.langchain.chains.stackspot_chain import StackSpotChain

        # StackSpotChain uses single-stage SEARCH/REPLACE pattern
        return StackSpotChain(
            main_agent_id=main_agent_id,
            tools=tools,
            file_indexer=self.file_indexer,  # Pass file indexer for NEW_FILE support
            interactive_mode=self.interactive_mode  # Pass interactive mode (Feature 34)
        )

    def _create_react_executor(self, tools: List[BaseTool]) -> "AgentExecutor":
        """Create ReAct Agent Executor (fallback)."""
        from ....integrations.langchain.agents import create_buddyctl_agent

        llm = self.langchain_model
        return create_buddyctl_agent(
            llm,
            tools=tools,
            verbose=False,
            use_streaming=False
        )
