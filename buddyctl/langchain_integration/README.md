# LangChain Integration for StackSpot AI

This module provides LangChain integration for StackSpot AI, enabling orchestration of multiple StackSpot agents using LangChain chains and tools.

## 🎯 Purpose

The main goal is to enable complex workflows by coordinating multiple specialized StackSpot agents, similar to systems like Claude Code, Devin, or Cursor.

## 📦 Components

### 1. `StackSpotChatModel`
LangChain-compatible wrapper for StackSpot AI agents.

```python
from buddyctl.langchain_integration import StackSpotChatModel

model = StackSpotChatModel(
    agent_id="your-agent-id",
    streaming=False
)

response = model.invoke("Explain Python decorators")
print(response.content)
```

### 2. `create_coder_differ_chain()`
Orchestrates two agents: Coder (generates code) → Differ (produces diff).

```python
from buddyctl.langchain_integration import create_coder_differ_chain

chain = create_coder_differ_chain(
    coder_agent_id="coder-123",
    differ_agent_id="differ-456"
)

result = chain.invoke({
    "file_path": "src/main.py",
    "instruction": "Add email validation"
})

print(result["diff"])  # Git-style diff output
```

### 3. `read_file` Tool
LangChain tool for reading source code files.

```python
from buddyctl.langchain_integration import read_file

content = read_file.invoke({"file_path": "src/main.py"})
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd your-project
poetry add langchain>=0.3.27 pydantic>=2.0.0
```

Or update `pyproject.toml`:
```toml
[tool.poetry.dependencies]
langchain = "^0.3.27"
pydantic = "^2.0.0"
```

### 2. Configure Credentials

Create or update `.env` file:
```env
STACKSPOT_CLIENT_ID=your_client_id
STACKSPOT_CLIENT_SECRET=your_client_secret
STACKSPOT_REALM=your_realm

# Agent IDs
CODER_AGENT_ID=your-coder-agent-id
DIFFER_AGENT_ID=your-differ-agent-id
```

### 3. Run Example

```bash
poetry run python examples/coder_differ_example.py
```

## 📋 MVP Use Case: Coder → Differ

The MVP demonstrates a two-agent workflow:

1. **User** provides a file and instruction
2. **Coder Agent** generates modified code
3. **Differ Agent** produces git-style diff
4. **Output** shows exactly what changed

### Example Flow:

```
Input:
  file: example.py
  instruction: "Add email validation"

↓ [Coder Agent]
Generates complete modified code with validation

↓ [Differ Agent]
Produces:

```diff
--- a/example.py
+++ b/example.py
@@ -1,4 +1,6 @@
 def register_user(name, email):
+    if "@" not in email:
+        raise ValueError("Invalid email")
     user = User(name=name, email=email)
     user.save()
```
```

## 🏗️ Architecture

```
User Input (file + instruction)
        ↓
   read_file tool
        ↓
   Coder Agent (StackSpot)
        ↓
   Differ Agent (StackSpot)
        ↓
   Git-style Diff Output
```

## 🔧 Advanced Usage

### Custom Chain

```python
from buddyctl.langchain_integration import StackSpotChatModel
from langchain_core.prompts import ChatPromptTemplate

# Create custom agent
analyzer = StackSpotChatModel(agent_id="analyzer-id")

# Create custom prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a code analyzer"),
    ("user", "Analyze: {code}")
])

# Build chain
chain = prompt | analyzer

# Execute
result = chain.invoke({"code": "def foo(): pass"})
```

### Using with LCEL

```python
from langchain_core.runnables import RunnablePassthrough

# Compose multiple steps
chain = (
    RunnablePassthrough()
    | step1
    | step2
    | step3
)
```

## 🧪 Testing

Run tests:
```bash
poetry run pytest tests/langchain_integration/
```

## ⚠️ Known Limitations (MVP)

- ❌ Temperature not adjustable (set in StackSpot Agent)
- ❌ No function calling/tools support
- ❌ No automatic file writing (diff only)
- ❌ No memory/context persistence
- ❌ Chain is hardcoded (not dynamic)

## 🔮 Future Phases

### Phase 2: Tools Ecosystem
- `write_file` - Apply changes automatically
- `apply_diff` - Apply git patches
- `git_commit` - Commit changes
- `run_tests` - Execute tests

### Phase 3: Intelligent Orchestration
- ReAct agent with dynamic tool selection
- Router to choose appropriate agent
- Memory for context across calls

### Phase 4: CLI Integration
- `buddyctl code-diff` command
- Interactive preview
- Apply/reject changes

## 📚 References

- [LangChain Documentation](https://python.langchain.com/)
- [StackSpot AI Documentation](https://ai.stackspot.com/docs/)
- [LangChain Expression Language (LCEL)](https://python.langchain.com/docs/expression_language/)

## 📄 License

Apache License 2.0 - See [LICENSE](../LICENSE) file for details.