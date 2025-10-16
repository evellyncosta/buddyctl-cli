# BuddyCtl - Architecture Documentation

## Overview

BuddyCtl is a CLI tool for managing and interacting with StackSpot AI assistants (buddies). The application follows a layered architecture with clear separation of concerns, provider abstraction, and LangChain integration for multi-provider support.

## Table of Contents

- [System Context](#system-context)
- [Container Diagram](#container-diagram)
- [Component Diagram](#component-diagram)
- [Provider Architecture](#provider-architecture)
- [Authentication Flow](#authentication-flow)
- [Chat Flow](#chat-flow)
- [Technology Stack](#technology-stack)
- [Package Structure](#package-structure)

---

## System Context

The following diagram shows how BuddyCtl fits into the broader ecosystem:

```mermaid
C4Context
    title System Context Diagram - BuddyCtl CLI

    Person(developer, "Developer", "Uses CLI to interact with AI assistants")

    System(buddyctl, "BuddyCtl CLI", "Command-line interface for AI assistant management")

    System_Ext(stackspot, "StackSpot AI API", "AI assistant platform")
    System_Ext(openai, "OpenAI API", "GPT models (future)")
    System_Ext(anthropic, "Anthropic API", "Claude models (future)")

    Rel(developer, buddyctl, "Uses", "Terminal")
    Rel(buddyctl, stackspot, "Authenticates & chats", "HTTPS/REST")
    Rel(buddyctl, openai, "Sends prompts", "HTTPS/REST (planned)")
    Rel(buddyctl, anthropic, "Sends prompts", "HTTPS/REST (planned)")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

**Key Interactions:**
- **Developer**: Uses the CLI to authenticate, configure agents, and chat with AI assistants
- **StackSpot API**: Current primary provider for AI chat completions
- **OpenAI/Anthropic**: Future providers for multi-LLM support

---

## Container Diagram

High-level view of the application containers and their interactions:

```mermaid
C4Container
    title Container Diagram - BuddyCtl CLI Architecture

    Person(user, "User", "Developer using CLI")

    Container(cli, "Interactive Shell", "Python/prompt_toolkit", "Handles user input, commands, and file autocompletion")
    Container(core, "Core Layer", "Python", "Authentication, configuration, provider management")
    Container(integration, "LangChain Integration", "Python/LangChain", "Unified LLM interface and custom models")
    Container(ui, "UI Layer", "Python/rich", "Banner, suggestions, visual feedback")
    Container(utils, "Utils Layer", "Python", "File indexing, autocompletion")

    ContainerDb(config_storage, "Config Storage", "JSON Files", "Stores credentials, tokens, settings")

    System_Ext(stackspot_api, "StackSpot API", "AI Assistant Platform")
    System_Ext(other_llm, "Other LLM APIs", "OpenAI, Anthropic, etc.")

    Rel(user, cli, "Interacts with", "Commands/Chat")
    Rel(cli, core, "Uses", "Python API")
    Rel(cli, ui, "Uses", "Display functions")
    Rel(cli, utils, "Uses", "File indexing")
    Rel(core, integration, "Uses", "LangChain models")
    Rel(core, config_storage, "Reads/Writes", "JSON")
    Rel(integration, stackspot_api, "HTTP Requests", "REST/SSE")
    Rel(integration, other_llm, "HTTP Requests", "REST (future)")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="2")
```

**Container Responsibilities:**
- **Interactive Shell**: User interaction, command parsing, chat orchestration
- **Core Layer**: Business logic, authentication, provider management
- **LangChain Integration**: LLM abstraction, custom chat models
- **UI Layer**: User interface components and visual feedback
- **Utils Layer**: Supporting utilities like file indexing

---

## Component Diagram

Detailed view of the Core Layer components:

```mermaid
C4Component
    title Component Diagram - Core Layer Components

    Container(cli, "Interactive Shell", "Python/prompt_toolkit")

    Component(provider_mgr, "ProviderManager", "Python", "Manages provider selection and routing")
    Component(provider_adapter, "ProviderAdapter Protocol", "Python Protocol", "Defines interface for all providers")
    Component(stackspot_adapter, "StackSpotAdapter", "Python", "StackSpot-specific implementation")
    Component(openai_adapter, "OpenAIAdapter", "Python", "OpenAI implementation (future)")
    Component(auth, "StackSpotAuth", "Python", "OAuth2 authentication")
    Component(config, "BuddyConfig", "Python", "Configuration management")
    Component(registry, "ProviderRegistry", "Python", "Provider metadata registry")
    Component(validator, "ProviderValidator", "Python", "Validates provider credentials")

    Container_Ext(langchain, "LangChain Models", "BaseChatModel")
    ContainerDb(storage, "Config Storage", "JSON Files")

    Rel(cli, provider_mgr, "Uses", "chat_stream()")
    Rel(provider_mgr, provider_adapter, "Routes to", "Protocol")
    Rel(provider_adapter, stackspot_adapter, "Implements", "Duck typing")
    Rel(provider_adapter, openai_adapter, "Implements", "Duck typing")
    Rel(stackspot_adapter, auth, "Uses", "get_valid_token()")
    Rel(stackspot_adapter, langchain, "Uses", "StackSpotChatModel")
    Rel(provider_mgr, config, "Reads", "get_current_provider()")
    Rel(provider_mgr, validator, "Validates", "credentials")
    Rel(provider_mgr, registry, "Queries", "provider metadata")
    Rel(auth, storage, "Reads/Writes", "tokens")
    Rel(config, storage, "Reads/Writes", "settings")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="2")
```

**Component Responsibilities:**

| Component | Responsibility |
|-----------|---------------|
| **ProviderManager** | Central facade for provider operations, routes messages to correct adapter |
| **ProviderAdapter** | Protocol defining the interface all providers must implement |
| **StackSpotAdapter** | Concrete implementation for StackSpot AI using LangChain |
| **StackSpotAuth** | OAuth2 authentication with token refresh and persistence |
| **BuddyConfig** | Configuration management (agent IDs, provider selection) |
| **ProviderRegistry** | Metadata registry for all known providers |
| **ProviderValidator** | Validates provider credentials and availability |

---

## Provider Architecture

The provider abstraction layer enables multi-LLM support through a unified interface:

```mermaid
graph TB
    subgraph "Application Layer"
        Shell[InteractiveShell]
    end

    subgraph "Provider Abstraction Layer"
        Manager[ProviderManager<br/>Facade]
        Protocol[ProviderAdapter<br/>Protocol]
    end

    subgraph "Provider Implementations"
        StackSpot[StackSpotAdapter]
        OpenAI[OpenAIAdapter<br/>future]
        Anthropic[AnthropicAdapter<br/>future]
    end

    subgraph "LangChain Layer"
        SSModel[StackSpotChatModel<br/>BaseChatModel]
        OAIModel[ChatOpenAI<br/>BaseChatModel]
        ClaudeModel[ChatAnthropic<br/>BaseChatModel]
    end

    subgraph "HTTP Communication Layer"
        HTTPX1[httpx Client<br/>SSE Streaming]
        HTTPX2[httpx Client]
        HTTPX3[httpx Client]
    end

    subgraph "External APIs"
        StackSpotAPI[(StackSpot API)]
        OpenAIAPI[(OpenAI API)]
        AnthropicAPI[(Anthropic API)]
    end

    Shell --> Manager
    Manager --> Protocol
    Protocol -.implements.-> StackSpot
    Protocol -.implements.-> OpenAI
    Protocol -.implements.-> Anthropic

    StackSpot --> SSModel
    OpenAI --> OAIModel
    Anthropic --> ClaudeModel

    SSModel --> HTTPX1
    OAIModel --> HTTPX2
    ClaudeModel --> HTTPX3

    HTTPX1 --> StackSpotAPI
    HTTPX2 --> OpenAIAPI
    HTTPX3 --> AnthropicAPI

    style Manager fill:#4A90E2,color:#fff
    style Protocol fill:#50C878,color:#fff
    style StackSpot fill:#F39C12,color:#fff
    style SSModel fill:#9B59B6,color:#fff
```

**Architecture Principles:**
1. **Single Responsibility**: Each adapter handles only one provider
2. **Open/Closed**: Add new providers without modifying existing code
3. **Dependency Inversion**: Application depends on Protocol, not concrete implementations
4. **Protocol-based Design**: Python Protocols enable structural subtyping (duck typing)
5. **LangChain Integration**: All providers use LangChain models for consistency

---

## Authentication Flow

OAuth2 authentication flow with token refresh:

```mermaid
sequenceDiagram
    actor User
    participant Shell as InteractiveShell
    participant Auth as StackSpotAuth
    participant Storage as ~/.buddyctl/credentials.json
    participant IDP as StackSpot IDP

    User->>Shell: Launch buddyctl
    Shell->>Auth: get_auth_status()
    Auth->>Storage: Load credentials

    alt Token Valid
        Storage-->>Auth: Valid token
        Auth-->>Shell: authenticated=true
        Shell-->>User: Display prompt ✅
    else Token Expired
        Storage-->>Auth: Expired token
        Auth->>IDP: POST /oauth/token (refresh_token)
        IDP-->>Auth: New access_token
        Auth->>Storage: Save new credentials
        Auth-->>Shell: authenticated=true
        Shell-->>User: Display prompt ✅
    else No Credentials
        Auth-->>Shell: authenticated=false
        Shell-->>User: Display prompt ❌
        User->>Shell: /status or send message
        Shell->>Auth: get_valid_token()
        Auth->>IDP: POST /oauth/token (client_credentials)
        IDP-->>Auth: access_token + refresh_token
        Auth->>Storage: Save credentials
        Auth-->>Shell: Return token
        Shell-->>User: Authenticated ✅
    end
```

**Token Lifecycle:**
- **Access Token**: Valid for ~1 hour, used for API requests
- **Refresh Token**: Used to obtain new access tokens without re-authenticating
- **Auto-Refresh**: Tokens automatically refreshed 60 seconds before expiration
- **Secure Storage**: Tokens stored in `~/.buddyctl/credentials.json` with `0600` permissions

---

## Chat Flow

End-to-end flow for sending a chat message:

```mermaid
sequenceDiagram
    actor User
    participant Shell as InteractiveShell
    participant Manager as ProviderManager
    participant Adapter as StackSpotAdapter
    participant Model as StackSpotChatModel
    participant Auth as StackSpotAuth
    participant API as StackSpot API

    User->>Shell: "Explain Python decorators"
    Shell->>Shell: _process_file_references()

    Shell->>Manager: chat_stream(message)
    Manager->>Manager: get_current_adapter()
    Manager->>Adapter: chat_stream(messages)

    Adapter->>Adapter: langchain_model (property)
    Adapter->>Model: stream(lc_messages)

    Model->>Auth: get_valid_token()
    Auth-->>Model: access_token

    Model->>Model: _build_url("/v1/agent/{id}/chat")
    Model->>Model: _get_headers(streaming=true)

    Model->>API: POST /v1/agent/{id}/chat<br/>SSE streaming

    loop For each SSE chunk
        API-->>Model: data: {"message": "Python "}
        Model-->>Adapter: yield "Python "
        Adapter-->>Manager: yield "Python "
        Manager-->>Shell: yield "Python "
        Shell-->>User: Display "Python "
    end

    API-->>Model: data: [DONE]
    Model-->>Adapter: End stream
    Adapter-->>Manager: End stream
    Manager-->>Shell: End stream
    Shell-->>User: Display complete response
```

**Key Steps:**
1. **File Reference Processing**: Shell checks for `@file` references and loads content
2. **Provider Routing**: ProviderManager selects appropriate adapter
3. **LangChain Abstraction**: Adapter converts to LangChain message format
4. **Authentication**: Model obtains valid token from Auth layer
5. **SSE Streaming**: HTTP request with Server-Sent Events for real-time response
6. **Chunk Processing**: Each chunk yielded through the entire stack to user

---

## Technology Stack

### Core Technologies

```mermaid
graph LR
    subgraph "Python 3.9+"
        Poetry[Poetry<br/>Dependency Manager]
        Pydantic[Pydantic v2<br/>Data Validation]
    end

    subgraph "CLI Framework"
        Typer[Typer<br/>CLI Framework]
        PromptToolkit[prompt_toolkit<br/>Interactive Input]
    end

    subgraph "HTTP & Networking"
        HTTPX[httpx<br/>Async HTTP Client]
        SSE[Server-Sent Events<br/>Streaming]
    end

    subgraph "LLM Integration"
        LangChain[LangChain<br/>v0.3.27]
        LangChainCore[langchain-core<br/>v0.3.27]
    end

    subgraph "Authentication"
        OAuth2[OAuth2<br/>Client Credentials]
        JWT[JWT Tokens<br/>Bearer Auth]
    end

    Poetry --> Typer
    Poetry --> HTTPX
    Poetry --> LangChain
    Poetry --> Pydantic

    Typer --> PromptToolkit
    HTTPX --> SSE
    HTTPX --> OAuth2
    OAuth2 --> JWT

    LangChain --> LangChainCore

    style LangChain fill:#4A90E2,color:#fff
    style HTTPX fill:#F39C12,color:#fff
    style Pydantic fill:#E91E63,color:#fff
```

### Key Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| **typer[all]** | ^0.9.0 | CLI framework with rich output |
| **httpx** | ^0.24.0 | Modern HTTP client with async support |
| **prompt-toolkit** | ^3.0.0 | Interactive input, autocompletion, history |
| **langchain** | ^0.3.27 | LLM abstraction and orchestration |
| **langchain-core** | ^0.3.27 | Core LangChain components |
| **pydantic** | ^2.0.0 | Data validation and settings management |

### Development Tools

| Tool | Purpose |
|------|---------|
| **pytest** | Testing framework |
| **black** | Code formatting |
| **ruff** | Fast Python linter |
| **mypy** | Static type checking |

---

## Package Structure

```
buddyctl-cli/
│
├── buddyctl/                          # Main package
│   ├── __init__.py
│   ├── __main__.py                    # Entry point for python -m buddyctl
│   ├── main.py                        # CLI entry point (Typer app)
│   │
│   ├── core/                          # Core business logic
│   │   ├── __init__.py
│   │   ├── auth.py                    # StackSpotAuth - OAuth2 authentication
│   │   ├── config.py                  # BuddyConfig - Configuration management
│   │   ├── api_client.py              # Legacy API client (deprecated)
│   │   ├── provider_registry.py       # Provider metadata registry
│   │   ├── provider_validator.py      # Provider credential validation
│   │   │
│   │   └── providers/                 # Provider abstraction layer
│   │       ├── __init__.py
│   │       ├── base.py                # ProviderAdapter Protocol + data models
│   │       ├── manager.py             # ProviderManager - Central facade
│   │       │
│   │       └── adapters/              # Provider implementations
│   │           ├── __init__.py
│   │           ├── stackspot.py       # StackSpotAdapter (implemented)
│   │           ├── openai.py          # OpenAIAdapter (future)
│   │           └── anthropic.py       # AnthropicAdapter (future)
│   │
│   ├── integrations/                  # External integrations
│   │   ├── __init__.py
│   │   │
│   │   └── langchain/                 # LangChain integration
│   │       ├── __init__.py
│   │       ├── chat_model.py          # StackSpotChatModel - Custom BaseChatModel
│   │       ├── utils.py               # Message conversion utilities
│   │       ├── chains.py              # LangChain chains (orchestration)
│   │       ├── tools.py               # LangChain tools
│   │       │
│   │       └── examples/              # Usage examples
│   │           ├── calculator.py      # Tool integration example
│   │           └── calculator_example.py
│   │
│   ├── cli/                           # CLI components
│   │   ├── __init__.py
│   │   ├── interactive.py             # InteractiveShell - Main shell
│   │   ├── agent_validator.py         # Agent ID validation
│   │   └── chat_client.py             # Legacy chat client (deprecated)
│   │
│   ├── ui/                            # User interface components
│   │   ├── __init__.py
│   │   ├── banner.py                  # ASCII banner display
│   │   ├── autosuggestion.py          # File autosuggestion logic
│   │   ├── enhanced_input.py          # Enhanced input handling
│   │   └── visual_suggestions.py      # Visual suggestion display
│   │
│   └── utils/                         # Utility modules
│       ├── __init__.py
│       ├── file_indexer.py            # File indexing system
│       └── file_autocomplete.py       # File autocompletion
│
├── tests/                             # Test suite
│   └── ...
│
├── .doc/                              # Feature documentation
│   ├── feature-template.md
│   ├── fix-template.md
│   ├── feature-12-use-stackspot-adapter.md
│   └── ...
│
├── pyproject.toml                     # Poetry configuration
├── poetry.lock                        # Dependency lock file
├── .env.example                       # Environment variables template
├── README.md                          # User documentation
└── ARCHITECTURE.md                    # This file
```

### Package Responsibilities

#### `buddyctl/core/`
- **Authentication**: OAuth2 flow, token management, credential storage
- **Configuration**: Agent IDs, provider selection, settings persistence
- **Provider Management**: Adapter selection, routing, validation

#### `buddyctl/core/providers/`
- **base.py**: Defines `ProviderAdapter` Protocol and data models (`ChatMessage`, `ChatResponse`)
- **manager.py**: `ProviderManager` - Central facade for provider operations
- **adapters/**: Concrete provider implementations following the Protocol

#### `buddyctl/integrations/langchain/`
- **chat_model.py**: Custom `StackSpotChatModel` extending LangChain's `BaseChatModel`
- **utils.py**: Message format conversion (LangChain ↔ StackSpot)
- **chains.py**: LangChain chains for complex workflows
- **tools.py**: Custom tools for agent integration

#### `buddyctl/cli/`
- **interactive.py**: Main interactive shell with command parsing and chat orchestration
- **agent_validator.py**: Validates agent IDs and availability

#### `buddyctl/ui/`
- **banner.py**: Displays status banner with auth/agent info
- **autosuggestion.py**: Handles file reference suggestions (`@file` syntax)
- **enhanced_input.py**: Enhanced input with history and completion
- **visual_suggestions.py**: Visual display of file suggestions

#### `buddyctl/utils/`
- **file_indexer.py**: Indexes project files for autocompletion
- **file_autocomplete.py**: Provides file completion in chat input

---

## Design Patterns

### 1. **Facade Pattern**
- **ProviderManager** acts as a simplified interface to the provider subsystem
- Hides complexity of adapter selection and message routing

### 2. **Protocol Pattern (Structural Subtyping)**
- **ProviderAdapter** defines interface without inheritance
- Enables duck typing with runtime validation via `@runtime_checkable`

### 3. **Adapter Pattern**
- **StackSpotAdapter** adapts StackSpot API to unified `ProviderAdapter` interface
- Future adapters (OpenAI, Anthropic) follow same pattern

### 4. **Strategy Pattern**
- Providers are interchangeable strategies for chat completion
- Selected dynamically based on configuration

### 5. **Factory Pattern**
- **ProviderManager** constructs appropriate adapter based on provider name
- Encapsulates adapter instantiation logic

---

## Configuration Files

### `~/.buddyctl/credentials.json`
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "refresh_token_here",
  "expires_at": 1234567890,
  "realm": "your-realm",
  "token_type": "Bearer"
}
```
- **Permissions**: `0600` (owner read/write only)
- **Auto-managed**: Created and updated by `StackSpotAuth`

### `~/.buddyctl/config.json`
```json
{
  "default_agent_id": "01K48SKQWX4D7A3AYF0P02X6GJ",
  "current_provider": "stackspot"
}
```
- **Managed by**: `BuddyConfig`
- **Stores**: User preferences and settings

### `.env`
```bash
STACKSPOT_CLIENT_ID=your_client_id
STACKSPOT_CLIENT_SECRET=your_client_secret
STACKSPOT_REALM=your_realm
STACKSPOT_AUTH_URL=https://idm.stackspot.com
STACKSPOT_API_URL=https://genai-inference-app.stackspot.com
```
- **Required for**: StackSpot authentication
- **Loaded by**: `StackSpotAuth` and `StackSpotChatModel`

---

## Future Enhancements

### Planned Features
1. **Multi-Provider Support**
   - OpenAI (ChatGPT) integration
   - Anthropic (Claude) integration
   - Google (Gemini) integration
   - Ollama (local models) integration

2. **Advanced LangChain Features**
   - Agent chains with tools
   - Memory and conversation history
   - RAG (Retrieval-Augmented Generation)
   - Multi-agent orchestration

3. **Enhanced CLI Features**
   - Plugin system for custom commands
   - Configuration profiles
   - Batch processing mode
   - Export chat history

4. **Performance Optimizations**
   - Connection pooling
   - Request caching
   - Async I/O for multiple providers

---

## References

### Related Documentation
- [Feature 12: Unified Architecture Migration](.doc/feature-12-use-stackspot-adapter.md)
- [Feature 11: Provider Abstraction Layer](.doc/feature-11-provider-abstraction.md)
- [Feature 7: LangChain Wrapper](.doc/feature-7-langchain-wrapper.md)

### External Resources
- [LangChain Documentation](https://python.langchain.com/)
- [Typer Documentation](https://typer.tiangolo.com/)
- [httpx Documentation](https://www.python-httpx.org/)
- [Python Protocols (PEP 544)](https://peps.python.org/pep-0544/)
- [C4 Model](https://c4model.com/)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-16
**Author**: Architecture Team
**Status**: Current
