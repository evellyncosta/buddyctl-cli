# Contributing to BuddyCtl

Thank you for your interest in contributing to BuddyCtl! 🎉

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Poetry for dependency management

### Setup Development Environment

1. **Clone the repository**
   ```bash
   git clone https://github.com/evellyncosta/buddyctl-cli
   cd buddyctl-cli
   ```

2. **Install Poetry** (if not already installed)
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies**
   ```bash
   poetry install
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your StackSpot credentials
   ```

5. **Run in development mode**
   ```bash
   poetry run buddyctl
   ```

### Useful Poetry Commands

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

# Activate virtual environment
poetry shell
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
│   │   ├── api_client.py    # API client wrapper
│   │   └── providers/       # Provider abstraction layer
│   │       ├── base.py          # ProviderAdapter protocol
│   │       ├── manager.py       # ProviderManager
│   │       └── adapters/        # Provider implementations
│   │           ├── stackspot.py    # StackSpot (implemented)
│   │           ├── openai.py       # OpenAI (planned)
│   │           └── anthropic.py    # Anthropic (planned)
│   ├── cli/                 # CLI components
│   │   ├── interactive.py   # Interactive shell
│   │   ├── agent_validator.py   # Agent validation
│   │   └── chat_client.py   # Chat with SSE streaming
│   ├── integrations/        # External integrations
│   │   └── langchain/       # LangChain integration
│   │       ├── chat_model.py    # StackSpot LangChain wrapper
│   │       ├── tools.py         # Tools (read_file, apply_diff)
│   │       ├── agents.py        # ReAct Agent
│   │       ├── context_formatter.py  # Context formatting
│   │       ├── chains/          # Chain implementations
│   │       │   ├── base.py          # Base chain
│   │       │   ├── stackspot_chain.py  # SEARCH/REPLACE pattern
│   │       │   └── legacy.py        # Legacy chains
│   │       └── examples/        # Usage examples
│   ├── ui/                  # User interface
│   │   ├── banner.py        # ASCII banner
│   │   ├── autosuggestion.py    # File autocompletion
│   │   ├── enhanced_input.py    # Enhanced input
│   │   └── visual_suggestions.py # Visual suggestions
│   └── utils/               # Utilities
│       ├── file_indexer.py  # File indexing system
│       └── file_autocomplete.py # File autocomplete
├── prompts/                 # Agent prompts
│   ├── README.md            # Prompts documentation
│   └── main_agent.md        # Main Agent system prompt (SEARCH/REPLACE)
├── tests/                   # Test suite
├── pyproject.toml           # Poetry configuration
├── poetry.lock              # Lock file (version pinning)
├── .env.example             # Environment template
├── README.md                # User documentation
├── ARCHITECTURE.md          # Architecture documentation
└── CONTRIBUTING.md          # This file
```

---

## How to Contribute

### Reporting Bugs 🐛

If you find a bug, please create an issue with:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, Poetry version)

### Suggesting Features 💡

We welcome feature suggestions! Please:
- Check if the feature was already suggested
- Explain the use case and benefits
- Provide examples if possible

### Code Contributions 🔧

1. **Fork the repository**
   ```bash
   git clone https://github.com/yourusername/buddyctl-cli.git
   cd buddyctl-cli
   ```

2. **Set up development environment** (see Development Setup above)
   ```bash
   poetry install
   cp .env.example .env
   # Edit .env with your credentials
   poetry run buddyctl --help
   ```

3. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make your changes**
   - Write clean, readable code
   - Follow existing code style
   - Add tests for new features
   - Update documentation if needed

5. **Run tests and linters**
   ```bash
   poetry run pytest
   poetry run black .
   poetry run ruff check .
   ```

6. **Commit your changes**
   ```bash
   git commit -m "feat: add amazing feature"
   ```

   Use conventional commit messages:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `refactor:` - Code refactoring
   - `test:` - Adding tests
   - `chore:` - Maintenance tasks

7. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style

We use:
- **Black** for code formatting
- **Ruff** for linting
- **mypy** for type checking (optional but recommended)

Run before committing:
```bash
poetry run black buddyctl/
poetry run ruff check buddyctl/
```

## Testing

We aim for high test coverage. When adding features:

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=buddyctl --cov-report=html

# View coverage report
open htmlcov/index.html
```

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

When you submit code changes, your submissions are understood to be under the same [Apache 2.0 License](LICENSE) that covers the project.

### Contributor License Agreement (CLA)

By submitting a pull request, you represent that:
- You have the right to license your contribution to the project
- You grant the project a perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable license
- You grant the project patent rights for your contributions (as per Apache 2.0)

## Questions?

Feel free to:
- Open an issue for questions
- Join discussions in existing issues
- Reach out to maintainers

Thank you for making BuddyCtl better! 🚀
