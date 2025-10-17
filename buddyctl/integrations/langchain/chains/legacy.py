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

"""
Chains for orchestrating StackSpot agents.

DEPRECATED: This module is deprecated in favor of provider-specific chains.

See:
- buddyctl/integrations/langchain/chains/ (new provider-specific chains)
- buddyctl/integrations/langchain/chains/stackspot_chain.py (StackSpot-specific chain)
- buddyctl/integrations/langchain/chains/base.py (base chain protocol)

For Feature 17 (Unified Tool Calling Abstraction) and Feature 18 (Judge Agent Integration),
use the provider-specific chains instead of this generic implementation.

This module is kept for backward compatibility only.
"""

import warnings

warnings.warn(
    "buddyctl.integrations.langchain.chains is deprecated. "
    "Use buddyctl.integrations.langchain.chains.stackspot_chain.StackSpotChain instead.",
    DeprecationWarning,
    stacklevel=2
)

from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

from ..chat_model import StackSpotChatModel
from ..tools import read_file, apply_diff


def create_coder_chain(agent_id: str, auto_apply: bool = True):
    """Create a chain with a single agent that generates diffs.

    This chain implements the following workflow:
    1. Read original code from file
    2. Send code + instruction to the Agent
    3. Agent generates a unified diff (git diff format)
    4. Optionally apply the diff automatically to the file

    Args:
        agent_id: ID of the StackSpot agent that generates diffs
        auto_apply: If True, automatically applies the diff to the file (default: False)

    Returns:
        Runnable chain that takes {file_path, instruction} and returns
        {original_code, diff, file_path, applied} (and optionally 'apply_result')

    Example:
        ```python
        from buddyctl.integrations.langchain import create_coder_chain

        # Create chain that just generates diff
        chain = create_coder_chain(agent_id="agent-123")
        result = chain.invoke({
            "file_path": "src/user.py",
            "instruction": "Add email validation"
        })
        print(result["diff"])

        # Create chain that generates and applies diff
        chain_auto = create_coder_chain(agent_id="agent-123", auto_apply=True)
        result = chain_auto.invoke({
            "file_path": "src/user.py",
            "instruction": "Add email validation"
        })
        print(result["apply_result"])  # Shows if diff was applied successfully
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
            "diff": str,                # Generated unified diff
            "applied": bool,            # Whether diff was applied
            "apply_result": str         # Result of applying diff (if auto_apply=True)
        }
    """
    agent = StackSpotChatModel(agent_id=agent_id, streaming=False)

    # Step 1: Read original code from file
    def read_code_step(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Read the original code file."""
        file_path = inputs["file_path"]
        code_result = read_file.invoke({"file_path": file_path})

        if code_result.startswith("Error:"):
            raise ValueError(f"Failed to read file: {code_result}")

        return {**inputs, "original_code": code_result}

    # Step 2: Agent generates unified diff
    diff_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "user",
                """Você receberá um código e uma instrução de modificação.
Gere um diff unificado (unified diff / git diff format) mostrando as alterações necessárias.

FORMATO OBRIGATÓRIO:
- NÃO use blocos de código markdown (``` diff ```)
- NÃO adicione explicações antes ou depois do diff
- Inicie com --- a/{file_path}
- Siga com +++ b/{file_path}
- Inclua os headers @@ para cada hunk com números de linha
- Use - para linhas removidas
- Use + para linhas adicionadas
- Use espaço para linhas de contexto

Arquivo: {file_path}

Código original:
{original_code}

Instrução: {instruction}
.""",
            )
        ]
    )

    # Step 3: Optionally apply the diff
    def apply_diff_step(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply the diff if auto_apply is enabled."""
        if not auto_apply:
            return {**inputs, "applied": False}

        diff_content = inputs.get("diff", "")
        if not diff_content:
            return {**inputs, "applied": False, "apply_result": "No diff to apply"}

        # Extract diff from markdown code blocks if present
        import re

        # Check if diff is wrapped in markdown code blocks
        markdown_pattern = r"```(?:diff)?\n(.*?)\n```"
        match = re.search(markdown_pattern, diff_content, re.DOTALL)

        if match:
            # Extract the diff content from markdown
            clean_diff = match.group(1).strip()
        else:
            # Try to find diff content by looking for --- and +++ headers
            lines = diff_content.split('\n')
            diff_start = None
            for i, line in enumerate(lines):
                if line.startswith('---') or line.startswith('+++'):
                    diff_start = i
                    break

            if diff_start is not None:
                # Found diff markers, extract from there
                clean_diff = '\n'.join(lines[diff_start:]).strip()
            else:
                # Use the content as-is
                clean_diff = diff_content.strip()

        # Apply the diff using the tool
        result = apply_diff.invoke({"diff_content": clean_diff})

        # Check if application was successful
        applied_successfully = result.startswith("Successfully")

        return {
            **inputs,
            "applied": applied_successfully,
            "apply_result": result,
            "clean_diff": clean_diff  # Include cleaned diff for debugging
        }

    # Build the complete chain using LCEL (LangChain Expression Language)
    chain = (
        RunnablePassthrough()
        # Step 1: Read file
        | RunnableLambda(read_code_step)
        # Step 2: Generate diff
        | RunnablePassthrough.assign(
            diff=(diff_prompt | agent | RunnableLambda(lambda x: x.content))
        )
        # Step 3: Apply diff if auto_apply is enabled
        | RunnableLambda(apply_diff_step)
    )

    return chain
