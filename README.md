# BuddyCtl

CLI tool for managing StackSpot AI assistants (buddies).

## Installation

Install BuddyCtl using pip:

```bash
pip install buddyctl
```

**Verify Installation:**

```bash
buddyctl --help
```

**Upgrading:**

```bash
pip install --upgrade buddyctl
```

## Configuration

### Setting up StackSpot Provider

BuddyCtl currently supports **StackSpot AI** as the LLM provider. You'll need to configure two agents in your StackSpot account:

#### 1. Get StackSpot Credentials

Generate your API credentials in your [StackSpot account](https://stackspot.com):
- Client ID
- Client Secret
- Realm

#### 2. Create Two Agents in StackSpot

You need to create **two separate agents** in StackSpot AI:

**Main Agent (Coder Agent)**
- **Purpose**: Generates responses and code modifications
- **Recommended Prompt**: Use the validated prompt from [`prompts/main_agent.md`](prompts/main_agent.md)
- **Custom Prompts**: You can use your own prompt if preferred
- **Characteristics**: Natural, conversational tone; generates complete unified diffs

**Judge Agent**
- **Purpose**: Analyzes Main Agent responses and decides when to execute tools
- **Recommended Prompt**: Use the validated prompt from [`prompts/judge_agent.md`](prompts/judge_agent.md)
- **Custom Prompts**: You can use your own prompt if preferred
- **Characteristics**: Analytical tone; returns structured JSON decisions

> **Note**: The validated prompts in the `prompts/` directory are tested and optimized for the two-stage tool calling pattern. While you can use custom prompts, the provided ones are recommended for best results.

#### 3. Configure Environment Variables

Create a `.env` file in your project directory:

```env
# Required: StackSpot Authentication
STACKSPOT_CLIENT_ID=your_client_id_here
STACKSPOT_CLIENT_SECRET=your_client_secret_here
STACKSPOT_REALM=your_realm_here

# Required: StackSpot API URLs
STACKSPOT_AUTH_URL=https://idm.stackspot.com
STACKSPOT_API_URL=https://genai-inference-app.stackspot.com

# Required: Agent IDs (from StackSpot AI dashboard)
STACKSPOT_CODER_ID=your_main_agent_id_here
STACKSPOT_JUDGE_AGENT_ID=your_judge_agent_id_here
```

**All variables are required.** BuddyCtl uses both agents together in a two-stage pattern for improved reliability when modifying code.

#### Architecture Details

For more information about how the two-stage tool calling pattern works, see [ARCHITECTURE.md](ARCHITECTURE.md#judge-agent-pattern-two-stage-tool-calling).

---

**Future Providers**: Support for OpenAI, Anthropic, and other LLM providers is planned but not yet implemented. Currently, only StackSpot AI is supported.

## Usage

After installation and configuration, use BuddyCtl directly:

```bash
# Run the interactive shell
buddyctl

# Login with your credentials (if not authenticated)
buddyctl auth login

# Show help
buddyctl --help
```

## Features

- 🔐 OAuth2 authentication with StackSpot
- 🤖 Agent management and configuration
- 💬 Interactive chat with streaming responses
- 🛠️ **Two-stage tool calling** with Judge Agent pattern
- 🔄 Automatic diff validation and retry logic (up to 3 attempts)
- 📝 Code modification with unified diff format
- 📁 File autocompletion with @ navigation
- 🔍 Real-time file indexing and suggestions
- 📋 Command history and auto-suggestions
- 🔌 Provider abstraction layer (OpenAI, Anthropic planned)

## Usage Examples

### Authentication
```bash
# Login with your credentials
buddyctl auth login
```

### Interactive Shell
```bash
# Start the interactive shell
buddyctl

# Inside the shell:
/help              # Show available commands
/status            # Check auth and agent status
/clear             # Clear screen
/exit              # Exit shell

# Chat with the agent (any message without /)
Hello, how can you help me?

# Reference files in your messages using @
Can you review @src/main.py and suggest improvements?

# Request code modifications (automatically applied)
Add type hints to @calculator.py
```

## Using as a Library

BuddyCtl can be used as a library in other Python projects:

```python
# Install from PyPI
pip install buddyctl

# Or install from git
pip install git+https://github.com/evellyncosta/buddyctl-cli.git

# Use the LangChain integration
from buddyctl.integrations.langchain import StackSpotChatModel
from buddyctl.integrations.langchain.chains import StackSpotChain
from buddyctl.integrations.langchain.tools import read_file, apply_diff

# Create a StackSpot chat model
model = StackSpotChatModel(agent_id="your-agent-id")
response = model.invoke("Explain Python decorators")

# Use Judge Agent pattern for code modifications
chain = StackSpotChain(
    main_agent_id="your-main-agent-id",
    judge_agent_id="your-judge-agent-id",
    tools=[read_file, apply_diff]
)

result = chain.invoke("Add type hints to calculator.py")

print(result["output"])          # Final response
print(result["tool_calls_made"]) # Tools that were executed
print(result["iterations"])      # Number of cycles
```

## Troubleshooting

### Command not found: buddyctl
If you installed with pip, make sure the installation directory is in your PATH.

### Authentication fails
- Verify your credentials in `.env` file
- Check if all required variables are set correctly
- Try: `buddyctl auth login`

## Contributing

Interested in contributing? Check out our [Contributing Guide](CONTRIBUTING.md) for details on:
- Setting up the development environment
- Code style and testing guidelines
- How to submit pull requests

We welcome contributions! 🚀

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