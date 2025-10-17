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

"""LangChain integration for StackSpot AI.

This module provides LangChain integration for StackSpot AI, enabling
orchestration of StackSpot agents using LangChain chains, tools, and agents.

Main Components:
    - StackSpotChatModel: LangChain-compatible wrapper for StackSpot agents
    - create_buddyctl_agent: ReAct Agent with automatic tool execution
    - create_coder_chain: Chain that generates diffs and optionally applies them
    - read_file: Tool for reading source code files
    - apply_diff: Tool for applying unified diffs to files

Example (ReAct Agent - Recommended):
    ```python
    from buddyctl.integrations.langchain import (
        create_buddyctl_agent
    )
    from buddyctl.core.providers import ProviderManager

    # Get LangChain model
    manager = ProviderManager(config)
    llm = manager.get_langchain_model()

    # Create agent with tools
    agent = create_buddyctl_agent(llm, verbose=True)

    # Execute - agent will automatically use tools
    result = agent.invoke({"input": "altere calculator.py para 3 números"})
    print(result["output"])
    ```

Example (Chain):
    ```python
    from buddyctl.integrations.langchain import (
        StackSpotChatModel,
        create_coder_chain
    )

    # Create chain that generates and applies diffs
    chain = create_coder_chain(
        agent_id="your-agent-id",
        auto_apply=True
    )

    # Execute chain
    result = chain.invoke({
        "file_path": "src/main.py",
        "instruction": "Add email validation"
    })

    print(result["diff"])
    print(result["apply_result"])
    ```
"""

from .chat_model import StackSpotChatModel
from .chains import create_coder_chain
from .tools import read_file, apply_diff, BASIC_TOOLS
from .agents import create_buddyctl_agent

__all__ = [
    "StackSpotChatModel",
    "create_buddyctl_agent",
    "create_coder_chain",
    "read_file",
    "apply_diff",
    "BASIC_TOOLS",
]
