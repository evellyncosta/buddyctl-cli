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
from pathlib import Path

from .base import BaseChain
from ..chat_model import StackSpotChatModel
from ....ui.message_box import MessageBox
from ....core.dependency_analyzer import analyze_dependencies, get_supported_extensions


@dataclass
class SearchReplaceBlock:
    """Represents a SEARCH/REPLACE block from Main Agent."""
    search: str
    replace: str
    file_path: str | None = None  # Optional file path for multi-file support

    def __str__(self) -> str:
        search_preview = self.search[:50] + "..." if len(self.search) > 50 else self.search
        replace_preview = self.replace[:50] + "..." if len(self.replace) > 50 else self.replace
        file_info = f", file='{self.file_path}'" if self.file_path else ""
        return f"SearchReplaceBlock(search='{search_preview}', replace='{replace_preview}'{file_info})"


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

            # 3. Determine file paths for blocks (HYBRID MODE)
            self.logger.debug("Step 3: Determining file paths for blocks (hybrid mode)")

            # Extract all files sent in context
            files_in_context = self._extract_all_files_from_input(user_input)
            self.logger.debug(f"Files in context: {len(files_in_context)} - {[Path(f).name for f in files_in_context]}")

            # Pre-load all file contents (for performance)
            files_content_cache: Dict[str, str] = {}
            for file_path in files_in_context:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        files_content_cache[file_path] = f.read()
                except Exception as e:
                    self.logger.warning(f"Failed to load {file_path}: {e}")

            # Assign file_path to each block (hybrid approach)
            auto_detection_failed = False
            for i, block in enumerate(blocks, 1):
                if block.file_path:
                    # Strategy 1: LLM provided FILE: marker
                    self.logger.debug(f"  Block {i}: Using LLM-provided path: {Path(block.file_path).name}")
                else:
                    # Strategy 2: System detects automatically
                    try:
                        block.file_path = self._find_matching_file(
                            block.search,
                            files_in_context,
                            files_content_cache
                        )
                        self.logger.info(f"  Block {i}: Auto-detected path: {Path(block.file_path).name}")
                    except ValueError as e:
                        # Could not determine file - will fail and retry
                        self.logger.warning(f"  Block {i}: Could not auto-detect file: {e}")
                        validation_error = str(e)
                        auto_detection_failed = True
                        break

            # Skip validation if auto-detection failed (go straight to retry)
            if auto_detection_failed:
                is_valid = False
                # validation_error already set above
            else:
                # 4. Validate SEARCH/REPLACE blocks
                self.logger.debug(f"Step 4: Validating {len(blocks)} block(s)")
                is_valid, validation_error = self._validate_multi_file_blocks(blocks)

            if is_valid:
                # 5. Apply blocks
                self.logger.info(f"✅ All {len(blocks)} block(s) validated successfully on round {round_number}")
                self.logger.debug("Step 5: Applying blocks")

                try:
                    affected_files = self._apply_multi_file_blocks(blocks)

                    # Build success message
                    if len(affected_files) == 1:
                        files_msg = f"Arquivo: {list(affected_files.keys())[0]}"
                    else:
                        files_msg = f"Arquivos: {', '.join(affected_files.keys())}"

                    MessageBox.success(
                        f"SUCESSO: {len(blocks)} modificação(ões) aplicada(s) em {len(affected_files)} arquivo(s) (round {round_number})",
                        files_msg
                    )

                    return {
                        "output": main_response,
                        "tool_calls_made": [
                            {
                                "name": "apply_search_replace",
                                "args": {
                                    "files": affected_files,
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

        Supports two patterns:

        1. Single-file mode (legacy):
            <<<<<<< SEARCH
            exact text to find
            =======
            new text to replace
            >>>>>>> REPLACE

        2. Multi-file mode (with FILE: markers):
            FILE: path/to/file1.py
            <<<<<<< SEARCH
            exact text to find
            =======
            new text to replace
            >>>>>>> REPLACE

            FILE: path/to/file2.py
            <<<<<<< SEARCH
            ...
            >>>>>>> REPLACE

        Returns:
            List of SearchReplaceBlock objects (with optional file_path attribute)
        """
        blocks = []

        # Check if response contains FILE: markers (multi-file mode)
        if 'FILE:' in response:
            self.logger.debug("Detected multi-file mode (FILE: markers present)")
            blocks = self._extract_multi_file_blocks(response)
        else:
            self.logger.debug("Detected single-file mode (no FILE: markers)")
            blocks = self._extract_single_file_blocks(response)

        self.logger.info(f"Extracted {len(blocks)} SEARCH/REPLACE block(s)")
        for i, block in enumerate(blocks, 1):
            self.logger.debug(f"  Block {i}: {block}")

        return blocks

    def _extract_single_file_blocks(self, response: str) -> List[SearchReplaceBlock]:
        """
        Extract SEARCH/REPLACE blocks in single-file mode (no FILE: markers).

        Returns:
            List of SearchReplaceBlock objects (without file_path)
        """
        pattern = r'<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE'
        matches = re.findall(pattern, response, re.DOTALL)

        blocks = []
        for search_text, replace_text in matches:
            blocks.append(SearchReplaceBlock(
                search=search_text,
                replace=replace_text,
                file_path=None
            ))

        return blocks

    def _extract_multi_file_blocks(self, response: str) -> List[SearchReplaceBlock]:
        """
        Extract SEARCH/REPLACE blocks in multi-file mode (with FILE: markers).

        Pattern:
            FILE: path/to/file.py
            <<<<<<< SEARCH
            ...
            =======
            ...
            >>>>>>> REPLACE

        Returns:
            List of SearchReplaceBlock objects (with file_path attribute)
        """
        blocks = []

        # Split response into sections by FILE: markers
        # Pattern: FILE: <path> followed by SEARCH/REPLACE blocks
        file_sections_pattern = r'FILE:\s*([^\n]+)\s*((?:<<<<<<< SEARCH.*?>>>>>>> REPLACE\s*)+)'
        file_sections = re.findall(file_sections_pattern, response, re.DOTALL)

        for file_path, blocks_text in file_sections:
            file_path = file_path.strip()
            self.logger.debug(f"Processing FILE: {file_path}")

            # Extract SEARCH/REPLACE blocks within this file section
            block_pattern = r'<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE'
            block_matches = re.findall(block_pattern, blocks_text, re.DOTALL)

            for search_text, replace_text in block_matches:
                blocks.append(SearchReplaceBlock(
                    search=search_text,
                    replace=replace_text,
                    file_path=file_path
                ))

        return blocks

    def _validate_search_replace_blocks(
        self,
        blocks: List[SearchReplaceBlock],
        file_path: str
    ) -> tuple[bool, str | None]:
        """
        [DEPRECATED] Legacy method for single-file validation.
        Use _validate_multi_file_blocks() instead.

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

    def _validate_multi_file_blocks(
        self,
        blocks: List[SearchReplaceBlock]
    ) -> tuple[bool, str | None]:
        """
        Validate SEARCH/REPLACE blocks for multiple files.

        Each block must have a file_path attribute.
        Validates that SEARCH content exists in the corresponding file.

        Returns:
            (is_valid, error_message)

        Example errors:
            (False, "File test-cases/UserService.kt, Block 2: SEARCH content not found...")
        """
        # Group blocks by file
        files_content: Dict[str, str] = {}

        for i, block in enumerate(blocks, 1):
            if not block.file_path:
                return (False, f"Block {i}: Missing file_path attribute")

            file_path = block.file_path

            # Load file content (cached per file)
            if file_path not in files_content:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        files_content[file_path] = f.read()
                except FileNotFoundError:
                    return (False, f"File not found: {file_path}")
                except Exception as e:
                    return (False, f"Error reading file {file_path}: {e}")

            # Validate SEARCH content
            file_content = files_content[file_path]
            if block.search not in file_content:
                # Better error message
                lines = block.search.split('\n')
                first_line = lines[0] if lines else ""
                snippet = first_line[:60] + "..." if len(first_line) > 60 else first_line

                error_msg = (
                    f"File {file_path}, Block {i}/{len(blocks)}: SEARCH content not found.\n"
                    f"First line of SEARCH block: '{snippet}'\n"
                    f"Make sure text matches EXACTLY (including whitespace)."
                )

                self.logger.warning(error_msg)
                return (False, error_msg)

        self.logger.debug(f"All {len(blocks)} block(s) validated successfully across {len(files_content)} file(s)")
        return (True, None)

    def _apply_search_replace_blocks(
        self,
        blocks: List[SearchReplaceBlock],
        file_path: str
    ) -> None:
        """
        [DEPRECATED] Legacy method for single-file application.
        Use _apply_multi_file_blocks() instead.

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

    def _apply_multi_file_blocks(
        self,
        blocks: List[SearchReplaceBlock]
    ) -> Dict[str, int]:
        """
        Apply SEARCH/REPLACE blocks to multiple files.

        Groups blocks by file_path and applies them sequentially to each file.

        Args:
            blocks: List of SearchReplaceBlock objects (each with file_path)

        Returns:
            Dictionary mapping file_path to number of blocks applied
            Example: {"UserController.kt": 1, "UserService.kt": 1}

        Raises:
            ValueError: If SEARCH content not found (should not happen after validation)
        """
        # Group blocks by file
        blocks_by_file: Dict[str, List[SearchReplaceBlock]] = {}
        for block in blocks:
            if not block.file_path:
                raise ValueError(f"Block missing file_path: {block}")

            if block.file_path not in blocks_by_file:
                blocks_by_file[block.file_path] = []

            blocks_by_file[block.file_path].append(block)

        # Apply blocks to each file
        affected_files: Dict[str, int] = {}

        for file_path, file_blocks in blocks_by_file.items():
            self.logger.info(f"Applying {len(file_blocks)} block(s) to {file_path}")

            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_length = len(content)

            # Apply each block
            for i, block in enumerate(file_blocks, 1):
                if block.search in content:
                    # Replace first occurrence only
                    content = content.replace(block.search, block.replace, 1)
                    self.logger.debug(f"  Applied block {i}/{len(file_blocks)} in {file_path}")
                else:
                    # Should not happen (validation passed)
                    error_msg = (
                        f"File {file_path}, Block {i}: SEARCH content disappeared between validation and apply. "
                        f"File may have been modified externally."
                    )
                    self.logger.error(error_msg)
                    raise ValueError(error_msg)

            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            chars_changed = len(content) - original_length
            self.logger.info(
                f"✅ Applied {len(file_blocks)} block(s) to {file_path} "
                f"({chars_changed:+d} characters)"
            )

            affected_files[file_path] = len(file_blocks)

        self.logger.info(
            f"Successfully applied {len(blocks)} block(s) across {len(affected_files)} file(s)"
        )
        return affected_files

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

    def _extract_all_files_from_input(self, user_input: str) -> List[str]:
        """
        Extract all file paths from enriched input.

        Looks for all occurrences of:
            File: path/to/file.py (N lines total)

        Returns:
            List of absolute file paths that were sent to LLM

        Example:
            Input contains:
            - File: /path/to/Controller.kt (94 lines)
            - File: /path/to/Service.kt (129 lines)

            Returns: ['/path/to/Controller.kt', '/path/to/Service.kt']
        """
        pattern = r'File: (.*?) \(\d+ lines total\)'
        matches = re.findall(pattern, user_input)
        self.logger.debug(f"Extracted {len(matches)} file(s) from input")
        return matches

    def _find_matching_file(
        self,
        search_text: str,
        candidate_files: List[str],
        files_content_cache: Dict[str, str]
    ) -> str:
        """
        Find which file contains the SEARCH text (automatic file detection).

        Args:
            search_text: The SEARCH block content
            candidate_files: List of file paths to search in
            files_content_cache: Pre-loaded file contents (for performance)

        Returns:
            Path to the file containing search_text

        Raises:
            ValueError: If found in 0 files or 2+ files (ambiguous)

        Example:
            search_text = "@Transactional\n    fun deleteHypothesis"
            candidate_files = ['Controller.kt', 'Service.kt', 'Repository.kt']

            Returns: 'Service.kt'  # Only file containing this text
        """
        matches = []

        for file_path in candidate_files:
            file_content = files_content_cache.get(file_path)
            if file_content and search_text in file_content:
                matches.append(file_path)

        if len(matches) == 0:
            # Better error message
            first_line = search_text.split('\n')[0] if search_text else ""
            snippet = first_line[:60] + "..." if len(first_line) > 60 else first_line
            raise ValueError(
                f"SEARCH content not found in any of {len(candidate_files)} files in context.\n"
                f"First line: '{snippet}'\n"
                f"Files searched: {[Path(f).name for f in candidate_files]}"
            )
        elif len(matches) > 1:
            # Ambiguous - ask LLM to be more specific
            raise ValueError(
                f"SEARCH content is AMBIGUOUS: found in {len(matches)} files.\n"
                f"Files: {[Path(f).name for f in matches]}\n"
                f"Please make SEARCH block more specific by including more surrounding context."
            )
        else:
            return matches[0]  # Exactly one match ✅

    def enrich_with_dependencies(
        self,
        user_input: str,
        project_root: Path | None = None
    ) -> str:
        """
        Enrich user input with related files from dependency analysis.

        Analyzes the main file for imports and automatically includes related
        project files in the context sent to the LLM.

        Args:
            user_input: Original user input with file content
            project_root: Project root directory (defaults to current working directory)

        Returns:
            Enriched input with additional file contexts, or original input if:
            - No file path found
            - File extension not supported
            - No dependencies found
            - Analysis fails

        Example:
            Input:  "File: UserController.kt\n..."
            Output: "File: UserController.kt\n...\n\nFile: UserService.kt\n...\n\nFile: UserRepository.kt\n..."
        """
        # Extract main file path
        main_file_path = self._extract_file_path_from_input(user_input)
        if not main_file_path:
            self.logger.debug("No file path found, skipping dependency analysis")
            return user_input

        # Check if file extension is supported
        main_file = Path(main_file_path)
        if main_file.suffix not in get_supported_extensions():
            self.logger.debug(f"File extension {main_file.suffix} not supported for dependency analysis")
            return user_input

        # Determine project root
        if project_root is None:
            project_root = Path.cwd()

        # Analyze dependencies (with transitive support: Controller → Service → Repository)
        try:
            related_files = analyze_dependencies(main_file, project_root, max_depth=2)

            if not related_files:
                self.logger.debug("No project dependencies found")
                return user_input

            self.logger.info(f"Found {len(related_files)} related file(s): {[str(f) for f in related_files]}")

            # Format related files with line numbers
            additional_contexts = []
            for related_file in related_files:
                try:
                    with open(related_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    formatted_lines = []
                    for i, line in enumerate(lines, 1):
                        formatted_lines.append(f"{i:3} | {line.rstrip()}")

                    total_lines = len(lines)
                    separator = "─" * 60

                    file_context = f"""File: {related_file} ({total_lines} lines total)
{separator}
{chr(10).join(formatted_lines)}
{separator}"""

                    additional_contexts.append(file_context)
                    self.logger.debug(f"Added related file: {related_file}")

                except Exception as e:
                    self.logger.warning(f"Failed to read related file {related_file}: {e}")
                    continue

            if additional_contexts:
                # Add header to explain multi-file context
                header = f"\n\n--- Related Files (automatically included based on imports) ---\n"
                enriched_input = user_input + header + "\n\n".join(additional_contexts)

                self.logger.info(f"Enriched input with {len(additional_contexts)} related file(s)")
                return enriched_input
            else:
                return user_input

        except Exception as e:
            self.logger.warning(f"Dependency analysis failed: {e}")
            return user_input

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
