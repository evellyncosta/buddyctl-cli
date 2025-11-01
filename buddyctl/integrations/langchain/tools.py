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

"""Tools for LangChain integration."""

from pathlib import Path

from langchain_core.tools import tool


@tool
def read_file(file_path: str) -> str:
    """Read content from a file.

    This tool reads the complete content of a file and returns it as a string.
    It's used primarily to load source code files that will be analyzed or
    modified by StackSpot agents.

    Args:
        file_path: Path to the file to read (relative or absolute).
                  Can be any text file (e.g., .py, .java, .kt, .go, .js)

    Returns:
        File content as string, or error message if operation fails

    Example:
        >>> result = read_file("src/main.py")
        >>> print(result)
        def main():
            print("Hello World")

    Error Cases:
        - File not found: Returns "Error: File not found: {path}"
        - Not a file: Returns "Error: Path is not a file: {path}"
        - Permission denied: Returns "Error: Permission denied reading: {path}"
        - Other errors: Returns "Error reading file: {exception}"
    """
    try:
        path = Path(file_path)

        # Check if file exists
        if not path.exists():
            return f"Error: File not found: {file_path}"

        # Check if path is actually a file (not a directory)
        if not path.is_file():
            return f"Error: Path is not a file: {file_path}"

        # Read file content with UTF-8 encoding
        content = path.read_text(encoding="utf-8")
        return content

    except PermissionError:
        return f"Error: Permission denied reading: {file_path}"
    except UnicodeDecodeError:
        # Handle binary files or non-UTF-8 encoded files
        return f"Error: File is not a valid UTF-8 text file: {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def extract_search_replace_blocks(response: str) -> str:
    """Extract SEARCH/REPLACE blocks from LLM response text.

    Supports two patterns:
    1. Single-file mode (no FILE: markers):
        <<<<<<< SEARCH
        exact text to find
        =======
        new text to replace
        >>>>>>> REPLACE

    2. Multi-file mode (with FILE: markers):
        FILE: path/to/file.py
        <<<<<<< SEARCH
        exact text
        =======
        replacement
        >>>>>>> REPLACE

    Args:
        response: LLM response text containing SEARCH/REPLACE blocks

    Returns:
        JSON string with list of blocks or error message.
        Success: '[{"file_path": "path/to/file.py", "search": "old", "replace": "new"}, ...]'
        Error: 'Error: Block 1: Malformed block - contains 2 `=======` markers...'

    Validation:
        - Each block must have EXACTLY ONE `=======` separator
        - Blocks must be well-formed (matching start/end markers)
    """
    import re
    import json

    try:
        # Check if multi-file mode (contains FILE: markers)
        if 'FILE:' in response:
            # Multi-file mode
            blocks = _parse_multi_file_blocks(response)
        else:
            # Single-file mode
            blocks = _parse_single_file_blocks(response)

        # Validate block format
        _validate_block_format(blocks, response)

        # Return as JSON string
        return json.dumps(blocks)

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error extracting blocks: {str(e)}"


@tool
def extract_new_file_blocks(response: str) -> str:
    """Extract NEW_FILE blocks from LLM response text.

    Pattern:
        NEW_FILE: path/to/file.py
        ```python
        file content here
        ```

    Args:
        response: LLM response text containing NEW_FILE blocks

    Returns:
        JSON string with list of new file blocks.
        Success: '[{"file_path": "src/helper.py", "content": "def foo()...", "language": "python"}, ...]'
        Empty list if no blocks found: '[]'

    Example:
        >>> result = extract_new_file_blocks("NEW_FILE: utils.py\\n```python\\ndef helper(): pass\\n```")
        >>> print(result)
        [{"file_path": "utils.py", "content": "def helper(): pass", "language": "python"}]
    """
    import re
    import json

    try:
        blocks = []

        # Pattern: NEW_FILE: <path> followed by code block
        pattern = r'NEW_FILE:\s*([^\n]+)\s*```(\w*)\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)

        for file_path, language, content in matches:
            file_path = file_path.strip()
            language = language.strip() if language else None

            blocks.append({
                "file_path": file_path,
                "content": content,
                "language": language
            })

        return json.dumps(blocks)

    except Exception as e:
        return f"Error extracting new file blocks: {str(e)}"


@tool
def search_replace_in_file(file_path: str, search: str, replace: str) -> str:
    """Apply exact text replacement in a file.

    Validates file exists, SEARCH content matches exactly, then replaces
    first occurrence with REPLACE content.

    Args:
        file_path: Path to file to modify
        search: Exact text to find (must match character-by-character)
        replace: Text to replace with

    Returns:
        Success: "✅ Successfully replaced text in file.py (replaced 1 occurrence, +23 characters)"
        Error: "❌ Error: SEARCH content not found in file.py. Make sure text matches EXACTLY."

    Validations:
        - Path traversal prevention (must be within current directory)
        - File exists and is a file (not directory)
        - SEARCH content exists in file (exact match)
        - UTF-8 encoding validation
        - Read/write permissions

    Example:
        >>> result = search_replace_in_file("main.py", "def old():", "def new():")
        >>> print(result)
        ✅ Successfully replaced text in main.py (replaced 1 occurrence, +2 characters)
    """
    try:
        path = Path(file_path)

        # Validation: path traversal
        if not _is_path_safe(path):
            return f"❌ Error: Path '{file_path}' is outside current directory (security violation)"

        # Validation: file exists
        if not path.exists():
            return f"❌ Error: File not found: {file_path}"

        # Validation: is a file (not directory)
        if not path.is_file():
            return f"❌ Error: Path is not a file: {file_path}"

        # Read file content
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"❌ Error: File is not valid UTF-8: {file_path}"
        except PermissionError:
            return f"❌ Error: Permission denied reading: {file_path}"

        # Validation: SEARCH content exists
        if search not in content:
            # Better error message with snippet
            first_line = search.split('\n')[0] if search else ""
            snippet = first_line[:60] + "..." if len(first_line) > 60 else first_line
            return (
                f"❌ Error: SEARCH content not found in {file_path}.\n"
                f"First line of SEARCH: '{snippet}'\n"
                f"Make sure text matches EXACTLY (including whitespace)."
            )

        # Apply replacement (first occurrence only)
        original_length = len(content)
        new_content = content.replace(search, replace, 1)
        chars_changed = len(new_content) - original_length

        # Write back
        try:
            path.write_text(new_content, encoding="utf-8")
        except PermissionError:
            return f"❌ Error: Permission denied writing: {file_path}"

        return f"✅ Successfully replaced text in {file_path} (replaced 1 occurrence, {chars_changed:+d} characters)"

    except Exception as e:
        return f"❌ Error: {str(e)}"


@tool
def create_new_file(file_path: str, content: str) -> str:
    """Create a new file with specified content.

    Creates parent directories if needed. Validates file doesn't already exist
    and path is within project boundaries.

    Args:
        file_path: Path where file will be created (relative to current directory)
        content: File content to write

    Returns:
        Success: "✅ Created file src/helper.py (245 characters)"
        Error: "❌ Error: File 'helper.py' already exists. Use search_replace_in_file to modify it."

    Validations:
        - Path within project (security)
        - File does NOT exist
        - Parent directories can be created
        - Write permissions

    Example:
        >>> result = create_new_file("src/utils/helper.py", "def foo():\\n    pass")
        >>> print(result)
        ✅ Created file src/utils/helper.py (19 characters)
    """
    try:
        path = Path(file_path)
        project_root = Path.cwd()

        # Security: ensure path is within project
        try:
            abs_path = (project_root / path).resolve()
            if not abs_path.is_relative_to(project_root):
                return (
                    f"❌ Error: Path '{file_path}' is outside project boundaries "
                    f"(security violation prevented)"
                )
        except (ValueError, OSError) as e:
            return f"❌ Error: Invalid path '{file_path}': {e}"

        # Validation: file does NOT exist
        if abs_path.exists():
            return (
                f"❌ Error: File '{file_path}' already exists. "
                f"Use search_replace_in_file to modify it."
            )

        # Create parent directories
        try:
            abs_path.parent.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            return f"❌ Error: Cannot create parent directory for '{file_path}': {e}"

        # Write file content
        try:
            abs_path.write_text(content, encoding="utf-8")
        except PermissionError:
            return f"❌ Error: Permission denied writing: {file_path}"

        return f"✅ Created file {file_path} ({len(content)} characters)"

    except Exception as e:
        return f"❌ Error: {str(e)}"


# ========================================
# PRIVATE HELPER FUNCTIONS (testable but not exposed as tools)
# ========================================

def _parse_single_file_blocks(response: str) -> list:
    """Parse SEARCH/REPLACE blocks in single-file mode (no FILE: markers).

    Args:
        response: LLM response text

    Returns:
        List of dicts: [{"search": str, "replace": str, "file_path": None}, ...]
    """
    import re

    pattern = r'<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE'
    matches = re.findall(pattern, response, re.DOTALL)

    blocks = []
    for search_text, replace_text in matches:
        blocks.append({
            "search": search_text,
            "replace": replace_text,
            "file_path": None
        })

    return blocks


def _parse_multi_file_blocks(response: str) -> list:
    """Parse SEARCH/REPLACE blocks in multi-file mode (with FILE: markers).

    Args:
        response: LLM response text

    Returns:
        List of dicts: [{"search": str, "replace": str, "file_path": str}, ...]
    """
    import re

    blocks = []

    # Pattern: FILE: <path> followed by SEARCH/REPLACE blocks
    file_sections_pattern = r'FILE:\s*([^\n]+)\s*((?:<<<<<<< SEARCH.*?>>>>>>> REPLACE\s*)+)'
    file_sections = re.findall(file_sections_pattern, response, re.DOTALL)

    for file_path, blocks_text in file_sections:
        file_path = file_path.strip()

        # Extract SEARCH/REPLACE blocks within this file section
        block_pattern = r'<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE'
        block_matches = re.findall(block_pattern, blocks_text, re.DOTALL)

        for search_text, replace_text in block_matches:
            blocks.append({
                "search": search_text,
                "replace": replace_text,
                "file_path": file_path
            })

    return blocks


def _validate_block_format(blocks: list, response: str) -> None:
    """Validate that SEARCH/REPLACE blocks are well-formed.

    Checks for common formatting errors like multiple `=======` markers.

    Args:
        blocks: Extracted blocks
        response: Original response text

    Raises:
        ValueError: If malformed blocks are detected
    """
    import re

    # Pattern to find all potential blocks (including malformed ones)
    full_block_pattern = r'<<<<<<< SEARCH\n(.*?)\n>>>>>>> REPLACE'
    full_blocks = re.findall(full_block_pattern, response, re.DOTALL)

    for i, full_block_content in enumerate(full_blocks, 1):
        # Count the number of `=======` separators in this block
        separator_count = full_block_content.count('\n=======\n')

        if separator_count == 0:
            raise ValueError(
                f"Block {i}: Malformed SEARCH/REPLACE block - missing `=======` separator.\n"
                f"Each block must have EXACTLY ONE `=======` marker separating SEARCH from REPLACE.\n"
                f"Block preview: {full_block_content[:100]}..."
            )
        elif separator_count > 1:
            raise ValueError(
                f"Block {i}: Malformed SEARCH/REPLACE block - contains {separator_count} `=======` markers.\n"
                f"Each block must have EXACTLY ONE `=======` marker separating SEARCH from REPLACE.\n"
                f"The `=======` is a SEPARATOR, not part of your code!"
            )


def _is_path_safe(path: Path) -> bool:
    """Check if path is within current directory (prevents path traversal).

    Args:
        path: Path to validate

    Returns:
        True if path is safe (within cwd), False otherwise
    """
    try:
        resolved = path.resolve()
        cwd = Path.cwd().resolve()
        return resolved.is_relative_to(cwd)
    except (ValueError, OSError):
        return False


# Export tools list for easy usage in chains
BASIC_TOOLS = [
    read_file,
    extract_search_replace_blocks,
    extract_new_file_blocks,
    search_replace_in_file,
    create_new_file
]

# Export private functions for testing
__all__ = [
    "read_file",
    "extract_search_replace_blocks",
    "extract_new_file_blocks",
    "search_replace_in_file",
    "create_new_file",
    "BASIC_TOOLS",
    "_parse_single_file_blocks",
    "_parse_multi_file_blocks",
    "_validate_block_format",
    "_is_path_safe"
]
