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
orchestration of multiple StackSpot agents using LangChain chains and tools.

Main Components:
    - StackSpotChatModel: LangChain-compatible wrapper for StackSpot agents
    - create_coder_differ_chain: Chain that orchestrates Coder → Differ agents
    - create_simple_coder_chain: Simplified chain with just the Coder agent
    - read_file: Tool for reading source code files

Example:
    ```python
    from buddyctl.langchain_integration import (
        StackSpotChatModel,
        create_coder_differ_chain
    )
    
    # Create orchestration chain
    chain = create_coder_differ_chain(
        coder_agent_id="your-coder-agent-id",
        differ_agent_id="your-differ-agent-id"
    )
    
    # Execute chain
    result = chain.invoke({
        "file_path": "src/main.py",
        "instruction": "Add email validation"
    })
    
    print(result["diff"])
    ```
"""

from .chat_model import StackSpotChatModel
from .chains import create_coder_differ_chain, create_simple_coder_chain
from .tools import read_file, BASIC_TOOLS

__all__ = [
    "StackSpotChatModel",
    "create_coder_differ_chain",
    "create_simple_coder_chain",
    "read_file",
    "BASIC_TOOLS",
]