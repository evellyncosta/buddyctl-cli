"""
StackSpot Chain - SEARCH/REPLACE Pattern (Single-Stage)

Fluxo:
1. Main Agent → resposta em texto livre com SEARCH/REPLACE blocks
2. Extract blocks → valida localmente → aplica (com retry)

Removido: Judge Agent (não funciona, conforme POC 2 e 3)
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from langchain_core.tools import BaseTool
import logging
import re

from .base import BaseChain
from ..chat_model import StackSpotChatModel
from ....ui.message_box import MessageBox


@dataclass
class SearchReplaceBlock:
    """Represents a SEARCH/REPLACE block from Main Agent."""
    search: str
    replace: str

    def __str__(self) -> str:
        search_preview = self.search[:50] + "..." if len(self.search) > 50 else self.search
        replace_preview = self.replace[:50] + "..." if len(self.replace) > 50 else self.replace
        return f"SearchReplaceBlock(search='{search_preview}', replace='{replace_preview}')"


class StackSpotChain(BaseChain):
    """
    Chain simplificada para StackSpot com SEARCH/REPLACE pattern.

    Orquestra: Main Agent → Extract SEARCH/REPLACE → Validate → Apply
    """

    def __init__(
        self,
        main_agent_id: str,
        tools: List[BaseTool]
    ):
        """
        Initialize StackSpot Chain with SEARCH/REPLACE pattern.

        Args:
            main_agent_id: StackSpot agent ID for main agent
            tools: Available tools (kept for compatibility with base class)
        """
        super().__init__(tools)

        self.logger = logging.getLogger(__name__)

        # Create main model (only one needed)
        self.main_model = StackSpotChatModel(
            agent_id=main_agent_id,
            streaming=False
        )

    def invoke(self, user_input: str) -> Dict[str, Any]:
        """
        Execute: Main Agent → Extract SEARCH/REPLACE → Validate → Apply (with retry)

        Returns:
            {
                "output": str,              # Final response from Main Agent
                "tool_calls_made": List,    # Tools executed (empty or [apply_search_replace])
                "validation_rounds": int,   # Number of retry rounds (0 = success first try)
                "blocks_applied": int       # Number of SEARCH/REPLACE blocks applied
            }
        """
        MAX_ROUNDS = 3

        self.logger.debug("="*60)
        self.logger.debug("StackSpotChain.invoke() started (SEARCH/REPLACE mode)")

        validation_error = None
        main_response = None

        for round_number in range(1, MAX_ROUNDS + 1):
            self.logger.info(f"--- ROUND {round_number}/{MAX_ROUNDS} ---")

            # 1. Call Main Agent
            if round_number == 1:
                self.logger.debug("Step 1: Calling Main Agent (initial)")
                response = self.main_model.invoke(user_input)
                main_response = response.content if hasattr(response, 'content') else str(response)
            else:
                self.logger.debug(f"Step 1: Calling Main Agent (correction round {round_number})")
                file_context = self._extract_file_context(user_input)
                main_response = self.next_round(
                    original_request=user_input,
                    previous_response=main_response,
                    validation_error=validation_error,
                    file_context=file_context,
                    round_number=round_number
                )

            self.logger.debug(f"Main Agent response length: {len(main_response)}")

            # 2. Extract SEARCH/REPLACE blocks
            self.logger.debug("Step 2: Extracting SEARCH/REPLACE blocks")
            blocks = self._extract_search_replace_blocks(main_response)

            if not blocks:
                # No modifications - just conversational response
                self.logger.debug("No SEARCH/REPLACE blocks found, returning conversational response")
                return {
                    "output": main_response,
                    "tool_calls_made": [],
                    "validation_rounds": 0,
                    "blocks_applied": 0
                }

            # 3. Extract file path from input
            self.logger.debug("Step 3: Extracting file path from input")
            file_path = self._extract_file_path_from_input(user_input)

            if not file_path:
                self.logger.error("No file path found in user input")
                MessageBox.error(
                    "ERRO: Caminho do arquivo não encontrado",
                    "O input deve conter 'File: path/to/file.py (N lines total)'"
                )
                return {
                    "output": main_response,
                    "error": "No file path in input",
                    "validation_rounds": 0,
                    "blocks_applied": 0
                }

            # 4. Validate SEARCH/REPLACE blocks
            self.logger.debug(f"Step 4: Validating {len(blocks)} block(s)")
            is_valid, validation_error = self._validate_search_replace_blocks(blocks, file_path)

            if is_valid:
                # 5. Apply blocks
                self.logger.info(f"✅ All {len(blocks)} block(s) validated successfully on round {round_number}")
                self.logger.debug("Step 5: Applying blocks")

                try:
                    self._apply_search_replace_blocks(blocks, file_path)

                    MessageBox.success(
                        f"SUCESSO: {len(blocks)} modificação(ões) aplicada(s) (round {round_number})",
                        f"Arquivo: {file_path}"
                    )

                    return {
                        "output": main_response,
                        "tool_calls_made": [
                            {
                                "name": "apply_search_replace",
                                "args": {
                                    "file_path": file_path,
                                    "blocks_count": len(blocks)
                                }
                            }
                        ],
                        "validation_rounds": round_number - 1,
                        "blocks_applied": len(blocks)
                    }
                except Exception as e:
                    self.logger.error(f"Error applying blocks: {e}")
                    MessageBox.error(
                        "ERRO: Falha ao aplicar modificações",
                        str(e)
                    )
                    return {
                        "output": main_response,
                        "error": str(e),
                        "validation_rounds": round_number - 1,
                        "blocks_applied": 0
                    }
            else:
                # Invalid - retry or fail
                self.logger.warning(f"❌ Validation failed on round {round_number}")
                self.logger.warning(f"Validation error: {validation_error}")

                if round_number == MAX_ROUNDS:
                    # Last attempt failed
                    MessageBox.error(
                        f"ERRO: Falha após {MAX_ROUNDS} tentativas",
                        f"Erro de validação: {validation_error}"
                    )

                    error_message = (
                        f"Failed to generate valid SEARCH/REPLACE blocks after {MAX_ROUNDS} attempts.\n\n"
                        f"Final validation error:\n{validation_error}\n\n"
                        f"Last response from Main Agent:\n{main_response}"
                    )

                    self.logger.error(error_message)
                    return {
                        "output": error_message,
                        "error": validation_error,
                        "validation_rounds": MAX_ROUNDS,
                        "blocks_applied": 0
                    }
                else:
                    # Retry
                    MessageBox.warning(
                        f"RETRY: Blocos inválidos, tentando ROUND {round_number + 1}/{MAX_ROUNDS}",
                        f"Razão: {validation_error}"
                    )
                    self.logger.info(f"Retrying with correction (round {round_number + 1})")
                    # Continue to next round

        # Should never reach here
        self.logger.error("Unexpected: exited retry loop without return")
        return {
            "output": "Internal error: retry loop failed",
            "error": "Unexpected loop exit",
            "validation_rounds": MAX_ROUNDS,
            "blocks_applied": 0
        }

    def _extract_search_replace_blocks(self, response: str) -> List[SearchReplaceBlock]:
        """
        Extract SEARCH/REPLACE blocks from Main Agent response.

        Pattern:
            <<<<<<< SEARCH
            exact text to find
            =======
            new text to replace
            >>>>>>> REPLACE

        Returns:
            List of SearchReplaceBlock objects
        """
        pattern = r'<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE'
        matches = re.findall(pattern, response, re.DOTALL)

        blocks = []
        for search_text, replace_text in matches:
            blocks.append(SearchReplaceBlock(
                search=search_text,
                replace=replace_text
            ))

        self.logger.info(f"Extracted {len(blocks)} SEARCH/REPLACE block(s)")
        for i, block in enumerate(blocks, 1):
            self.logger.debug(f"  Block {i}: {block}")

        return blocks

    def _validate_search_replace_blocks(
        self,
        blocks: List[SearchReplaceBlock],
        file_path: str
    ) -> tuple[bool, str | None]:
        """
        Validate that SEARCH blocks exist in target file (dry-run).

        Returns:
            (is_valid, error_message)

        Example errors:
            (False, "Block 1: SEARCH content not found. First line: 'def subtract...'")
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except FileNotFoundError:
            return (False, f"File not found: {file_path}")
        except Exception as e:
            return (False, f"Error reading file: {e}")

        for i, block in enumerate(blocks, 1):
            if block.search not in file_content:
                # Better error message: show first line of SEARCH
                lines = block.search.split('\n')
                first_line = lines[0] if lines else ""

                # Show snippet for debugging
                snippet = first_line[:60] + "..." if len(first_line) > 60 else first_line

                error_msg = (
                    f"Block {i}/{len(blocks)}: SEARCH content not found in file.\n"
                    f"First line of SEARCH block: '{snippet}'\n"
                    f"Make sure text matches EXACTLY (including whitespace)."
                )

                self.logger.warning(error_msg)
                return (False, error_msg)

        self.logger.debug(f"All {len(blocks)} block(s) validated successfully")
        return (True, None)

    def _apply_search_replace_blocks(
        self,
        blocks: List[SearchReplaceBlock],
        file_path: str
    ) -> None:
        """
        Apply SEARCH/REPLACE blocks to file.

        Replaces first occurrence of each SEARCH block with REPLACE content.

        Args:
            blocks: List of SearchReplaceBlock objects
            file_path: Path to target file

        Raises:
            ValueError: If SEARCH content not found (should not happen after validation)
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_length = len(content)

        for i, block in enumerate(blocks, 1):
            if block.search in content:
                # Replace first occurrence only
                content = content.replace(block.search, block.replace, 1)
                self.logger.info(f"Applied block {i}/{len(blocks)}")
            else:
                # Should not happen (validation passed)
                error_msg = (
                    f"Block {i}: SEARCH content disappeared between validation and apply. "
                    f"File may have been modified externally."
                )
                self.logger.error(error_msg)
                raise ValueError(error_msg)

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        chars_changed = len(content) - original_length
        self.logger.info(
            f"Successfully applied {len(blocks)} change(s) to {file_path}. "
            f"Changed {chars_changed:+d} characters."
        )

    def _extract_file_path_from_input(self, user_input: str) -> str | None:
        """
        Extract file path from user input.

        Looks for pattern:
            File: path/to/file.py (N lines total)

        Returns:
            File path or None if not found
        """
        # Pattern: File: path/to/file.py (N lines total)
        pattern = r'File: (.*?) \(\d+ lines total\)'
        match = re.search(pattern, user_input)

        if match:
            file_path = match.group(1)
            self.logger.debug(f"Extracted file path: {file_path}")
            return file_path

        self.logger.warning("No file path found in user input")
        return None

    def _extract_file_context(self, user_input: str) -> str:
        """
        Extract file content from user_input (if present).

        Looks for pattern:
        File: path (X lines total)
        ────────────────────────────────────────────
        1 | code
        ...

        Returns:
            Formatted file content or empty string
        """
        # Regex to find file content with line numbers
        pattern = r'File: (.*?) \(\d+ lines total\)\n─+\n(.*?)\n─+'
        match = re.search(pattern, user_input, re.DOTALL)

        if match:
            file_path = match.group(1)
            content = match.group(2)
            return f"File: {file_path}\n────────────────────────────────────────────\n{content}\n────────────────────────────────────────────"

        return ""

    def next_round(
        self,
        original_request: str,
        previous_response: str,
        validation_error: str,
        file_context: str,
        round_number: int
    ) -> str:
        """
        Request correction from Main Agent after validation failure.

        Builds contextualized prompt with:
        - Specific validation error
        - Original user request
        - Previous attempt that failed
        - Current file content (with line numbers)
        - Round number

        Args:
            original_request: Original user request
            previous_response: Previous Main Agent response that failed
            validation_error: Validation error message
            file_context: Formatted file content (with line numbers)
            round_number: Current attempt number (2, 3, ...)

        Returns:
            New Main Agent response (corrected)

        Example Flow:
            Round 1: User request → Main Agent → Invalid SEARCH
            Round 2: next_round(error="Block 1: text not found...") → Main Agent → Valid ✅
        """
        self.logger.info(f"Starting correction round {round_number}")
        self.logger.debug(f"Validation error: {validation_error}")

        # Build correction prompt
        correction_prompt = f"""ROUND {round_number} - SEARCH/REPLACE CORRECTION REQUIRED

Your previous SEARCH/REPLACE blocks failed validation with the following error:

ERROR:
{validation_error}

This means the SEARCH content doesn't match the actual file. Common causes:
1. **Whitespace mismatch**: Tabs vs spaces, trailing spaces, line breaks
2. **Incomplete context**: SEARCH block doesn't include enough surrounding code
3. **Text doesn't exist**: Content may have been misread from line numbers

Original user request:
{original_request}

Your previous attempt (REJECTED):
{previous_response}

Current file content with line numbers:
{file_context}

Please generate CORRECTED SEARCH/REPLACE blocks:

CRITICAL INSTRUCTIONS:
1. Copy the SEARCH content EXACTLY from the file above
   - Include ALL whitespace exactly as shown (tabs, spaces, newlines)
   - The text after line numbers (after " | ") is the ACTUAL file content
   - Example: If you see " 5 |     return x", the actual line is "    return x" (4 spaces)

2. Include enough context to make SEARCH unique
   - Typically 5-10 lines
   - Include surrounding functions/code to ensure uniqueness

3. Use the correct format:
   <<<<<<< SEARCH
   exact text from file
   =======
   new text to replace with
   >>>>>>> REPLACE

REMEMBER: The SEARCH block must match the file EXACTLY, character-by-character, including all whitespace.
"""

        # Call Main Agent with correction prompt
        self.logger.debug("Invoking Main Agent for correction")
        response = self.main_model.invoke(correction_prompt)
        corrected_response = response.content if hasattr(response, 'content') else str(response)

        self.logger.debug(f"Main Agent correction response length: {len(corrected_response)}")
        return corrected_response


__all__ = ["StackSpotChain", "SearchReplaceBlock"]
