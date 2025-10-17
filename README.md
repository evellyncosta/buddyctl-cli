# BuddyCtl

CLI tool for managing StackSpot AI assistants (buddies).

## Installation

Install BuddyCtl using pip:

```bash
pip install buddyctl
```

**Verify Installation:**

```bash
buddyctl --version
buddyctl --help
```

**Upgrading:**

```bash
pip install --upgrade buddyctl
```

## Configuration

Create a `.env` file in your project directory with your StackSpot credentials:

```env
# Required: StackSpot Authentication
STACKSPOT_CLIENT_ID=your_client_id_here
STACKSPOT_CLIENT_SECRET=your_client_secret_here
STACKSPOT_REALM=your_realm_here

# Optional: Default Agent ID
STACKSPOT_CODER_ID=your_agent_id_here
```

**Where to get credentials:**
- Generate your credentials in your [StackSpot account](https://stackspot.com)
- Find your agent ID in the StackSpot AI dashboard

## Usage

After installation and configuration, use BuddyCtl directly:

```bash
# Run the interactive shell
buddyctl

# Check authentication status
buddyctl auth status

# Login with your credentials
buddyctl auth login

# Set default agent
buddyctl agent-default <agent_id>

# Show help
buddyctl --help
```

## Features

- 🔐 OAuth2 authentication with StackSpot
- 🤖 Agent management and configuration
- 💬 Interactive chat with streaming responses
- 📁 File autocompletion with @ navigation
- 🔍 Real-time file indexing and suggestions
- 📝 Command history and auto-suggestions

## Usage Examples

### Authentication
```bash
# Login with your credentials
buddyctl auth login

# Check authentication status
buddyctl auth status

# Logout
buddyctl auth logout
```

### Setting Default Agent
```bash
# Set the default agent for conversations
buddyctl agent-default <your-agent-id>
```

### Interactive Shell
```bash
# Start the interactive shell
buddyctl

# Inside the shell:
/help              # Show available commands
/status            # Check auth and agent status
/agent-default <id> # Set default agent
/provider          # List or change LLM provider
/clear             # Clear screen
/exit              # Exit shell

# Chat with the agent (any message without /)
Hello, how can you help me?

# Reference files in your messages using @
Can you review @src/main.py and suggest improvements?
```

## Development

For contributors and developers who want to work on BuddyCtl itself:

### Setup Development Environment

1. Clone the repository:
```bash
git clone https://github.com/evellyncosta/buddyctl-cli
cd buddyctl-cli
```

2. Install Poetry:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Install dependencies:
```bash
poetry install
```

4. Run in development mode:
```bash
poetry run buddyctl
```

### Useful Poetry commands:

```bash
# Add a new dependency
poetry add package-name

# Add a development dependency
poetry add --group dev package-name

# Update dependencies
poetry update

# Show installed packages
poetry show

# Show dependency tree
poetry show --tree

# Check for dependency issues
poetry check

# Run commands in the virtual environment
poetry run <command>

# Activate virtual environment (Poetry 2.0+)
source $(poetry env info --path)/bin/activate

# Or install the shell plugin for poetry shell command
poetry self add poetry-plugin-shell
poetry shell
```

### Adding LangChain Integration

```bash
# Add LangChain core
poetry add langchain

# Add specific integrations
poetry add langchain-openai      # For OpenAI/GPT models
poetry add langchain-anthropic   # For Claude API
poetry add langchain-community   # Community integrations

# Verify installation
poetry run python -c "import langchain; print(langchain.__version__)"
```

### Running tests and linters:

```bash
# If you add these dev dependencies:
poetry add --group dev pytest black ruff

# Run tests
poetry run pytest

# Format code
poetry run black .

# Lint code
poetry run ruff check .
```

### Project Structure

```
buddyctl-cli/
├── buddyctl/                # Main package
│   ├── __init__.py
│   ├── __main__.py
│   ├── main.py              # CLI entry point
│   ├── core/                # Core modules
│   │   ├── auth.py          # OAuth2 authentication
│   │   ├── config.py        # Configuration management
│   │   └── api_client.py    # API client wrapper
│   ├── cli/                 # CLI components
│   │   ├── interactive.py   # Interactive shell
│   │   ├── agent_validator.py   # Agent validation
│   │   └── chat_client.py   # Chat with SSE streaming
│   ├── integrations/        # External integrations
│   │   └── langchain/       # LangChain integration
│   │       ├── chat_model.py    # StackSpot LangChain wrapper
│   │       ├── chains.py        # Orchestration chains
│   │       ├── tools.py         # LangChain tools
│   │       ├── utils.py         # Utilities
│   │       └── examples/        # Usage examples
│   ├── ui/                  # User interface
│   │   ├── banner.py        # ASCII banner
│   │   ├── autosuggestion.py    # File autocompletion
│   │   ├── enhanced_input.py    # Enhanced input
│   │   └── visual_suggestions.py # Visual suggestions
│   └── utils/               # Utilities
│       ├── file_indexer.py  # File indexing system
│       └── file_autocomplete.py # File autocomplete
├── pyproject.toml           # Poetry configuration
├── poetry.lock              # Lock file (version pinning)
├── .env.example             # Environment template
└── README.md                # This file
```

### Using as a Library

BuddyCtl can be used as a library in other Python projects:

```python
# Install from PyPI
pip install buddyctl

# Or install from git
pip install git+https://github.com/evellyncosta/buddyctl-cli.git

# Use the LangChain integration
from buddyctl.integrations.langchain import StackSpotChatModel, create_coder_chain

# Create a StackSpot chat model
model = StackSpotChatModel(agent_id="your-agent-id")
response = model.invoke("Explain Python decorators")

# Or use chains to generate and apply diffs
chain = create_coder_chain(
    agent_id="your-agent-id",
    auto_apply=True  # Automatically applies the diff to the file
)

result = chain.invoke({
    "file_path": "src/main.py",
    "instruction": "Add error handling"
})

print(result["diff"])  # Shows the unified diff
print(result["apply_result"])  # Shows if the diff was applied successfully
```

## Troubleshooting

### Command not found: buddyctl
Make sure you're using `poetry run buddyctl` or have created an alias.

### Authentication fails
- Verify your credentials in `.env` file
- Check if CLIENT_ID, CLIENT_SECRET, and REALM are correct
- Try: `poetry run buddyctl auth login`

### Poetry command not found
Install Poetry:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### Dependency conflicts
```bash
# Clear cache and reinstall
poetry cache clear pypi --all
poetry install
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linters
5. Submit a pull request

## License

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

### What does this mean?

**You can:**
- ✅ Use this software for any purpose (commercial or personal)
- ✅ Modify the source code
- ✅ Distribute original or modified versions
- ✅ Sublicense (include it in your own projects)
- ✅ Use it in proprietary software

**You must:**
- 📝 Include the original copyright notice
- 📝 Include the LICENSE file
- 📝 State significant changes made to the code
- 📝 Include the NOTICE file (if present)

**Protection:**
- 🛡️ **Patent Grant**: Contributors grant you patent rights for their contributions
- 🛡️ **Patent Retaliation**: If you sue for patent infringement, your license terminates
- 🛡️ **No Trademark Rights**: You can't use project trademarks without permission

### Why Apache 2.0?

We chose Apache 2.0 because it:
- Encourages both open source and commercial adoption
- Provides explicit patent protection
- Is compatible with most other open source licenses
- Is trusted by major organizations and developers worldwide

### Third-Party Licenses

This project uses the following open source libraries:
- [typer](https://github.com/tiangolo/typer) - BSD-3-Clause
- [httpx](https://github.com/encode/httpx) - BSD-3-Clause
- [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) - BSD-3-Clause

All third-party libraries maintain their original licenses.