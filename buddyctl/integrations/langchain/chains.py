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

"""Chains for orchestrating multiple StackSpot agents."""

from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

from .chat_model import StackSpotChatModel
from .tools import read_file


def create_coder_differ_chain(coder_agent_id: str, differ_agent_id: str):
    """Create a chain that orchestrates Coder and Differ agents.

    This chain implements the following workflow:
    1. Read original code from file
    2. Send code + instruction to Coder Agent
    3. Coder generates modified code
    4. Send original + modified code to Differ Agent
    5. Differ generates git-style diff

    The Coder Agent is a developer specialist that generates/modifies code
    following best practices. The Differ Agent specializes in producing
    clean, unified diffs (git diff format).

    Args:
        coder_agent_id: ID of the StackSpot Coder agent
        differ_agent_id: ID of the StackSpot Differ agent

    Returns:
        Runnable chain that takes {file_path, instruction} and returns
        {original_code, modified_code, diff, file_path}

    Example:
        ```python
        from buddyctl.langchain_integration import create_coder_differ_chain

        chain = create_coder_differ_chain(
            coder_agent_id="coder-123",
            differ_agent_id="differ-456"
        )

        result = chain.invoke({
            "file_path": "src/user.py",
            "instruction": "Add email validation (must contain @)"
        })

        print(result["diff"])
        # Output: git-style diff with changes
        ```

    Input Schema:
        {
            "file_path": str,      # Path to the file to modify
            "instruction": str     # What to change/add/fix
        }

    Output Schema:
        {
            "file_path": str,           # Original file path
            "instruction": str,         # Original instruction
            "original_code": str,       # Code before changes
            "modified_code": str,       # Code after Coder agent
            "diff": str                 # Git-style diff from Differ agent
        }
    """
    # Initialize the two StackSpot agents
    coder = StackSpotChatModel(agent_id=coder_agent_id, streaming=False)
    differ = StackSpotChatModel(agent_id=differ_agent_id, streaming=False)

    # Step 1: Read original code from file
    def read_code_step(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Read the original code file.

        Args:
            inputs: Dict with 'file_path' and 'instruction'

        Returns:
            Dict with added 'original_code' field
        """
        file_path = inputs["file_path"]

        # Use the read_file tool
        code_result = read_file.invoke({"file_path": file_path})

        # Check if read was successful
        if code_result.startswith("Error:"):
            raise ValueError(f"Failed to read file: {code_result}")

        return {**inputs, "original_code": code_result}

    # Step 2: Coder Agent generates modified code
    coder_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "user",
                """Você receberá um código e uma instrução de modificação.
Gere o código completo modificado seguindo a instrução.

Arquivo: {file_path}

Código original:
{original_code}

Instrução: {instruction}

Retorne APENAS o código modificado completo, sem explicações adicionais.""",
            )
        ]
    )

    # Step 3: Differ Agent generates git-style diff
    differ_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "user",
                """Nome do arquivo: {file_path}

Código original:
{original_code}

Código modificado:
{modified_code}

Gere o diff unificado (git diff format) mostrando as alterações.""",
            )
        ]
    )

    # Build the complete chain using LCEL (LangChain Expression Language)
    chain = (
        # Start with input passthrough
        RunnablePassthrough()
        # Step 1: Read file
        | RunnableLambda(read_code_step)
        # Step 2: Generate modified code with Coder
        | RunnablePassthrough.assign(
            modified_code=(coder_prompt | coder | RunnableLambda(lambda x: x.content))
        )
        # Step 3: Generate diff with Differ
        | RunnablePassthrough.assign(
            diff=(differ_prompt | differ | RunnableLambda(lambda x: x.content))
        )
    )

    return chain


def create_simple_coder_chain(coder_agent_id: str):
    """Create a simple chain with just the Coder agent.

    This is a simplified chain for testing or when you only need
    code generation without diff output.

    Args:
        coder_agent_id: ID of the StackSpot Coder agent

    Returns:
        Runnable chain that generates modified code

    Example:
        ```python
        chain = create_simple_coder_chain("coder-123")

        result = chain.invoke({
            "file_path": "src/main.py",
            "instruction": "Add error handling"
        })

        print(result["modified_code"])
        ```
    """
    coder = StackSpotChatModel(agent_id=coder_agent_id, streaming=False)

    def read_code_step(inputs: Dict[str, Any]) -> Dict[str, Any]:
        file_path = inputs["file_path"]
        code_result = read_file.invoke({"file_path": file_path})

        if code_result.startswith("Error:"):
            raise ValueError(f"Failed to read file: {code_result}")

        return {**inputs, "original_code": code_result}

    coder_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "user",
                """Arquivo: {file_path}

Código original:
{original_code}

Instrução: {instruction}

Gere o código modificado completo.""",
            )
        ]
    )

    chain = (
        RunnablePassthrough()
        | RunnableLambda(read_code_step)
        | RunnablePassthrough.assign(
            modified_code=(coder_prompt | coder | RunnableLambda(lambda x: x.content))
        )
    )

    return chain
