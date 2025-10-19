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

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from langchain_core.tools import tool


@dataclass
class Hunk:
    """Represents a single hunk in a unified diff.

    A hunk is a contiguous block of changes in a diff, marked by @@ headers.
    """
    old_start: int  # Line number where changes start in original file
    old_count: int  # Number of lines in the original file
    new_start: int  # Line number where changes start in new file
    new_count: int  # Number of lines in the new file
    lines: List[Tuple[str, str]]  # (operation, content) where operation is ' ', '-', or '+'


@dataclass
class FileDiff:
    """Represents changes to a single file in unified diff format."""
    old_path: str  # Original file path (from --- header)
    new_path: str  # New file path (from +++ header)
    hunks: List[Hunk]  # List of hunks to apply


def parse_hunk(hunk_lines: List[str]) -> Hunk:
    """Parse a single hunk from unified diff format.

    Args:
        hunk_lines: Lines of the hunk including the @@ header

    Returns:
        Hunk object with parsed information

    Raises:
        ValueError: If hunk format is invalid
    """
    if not hunk_lines:
        raise ValueError("Empty hunk")

    # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
    header = hunk_lines[0]
    match = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", header)
    if not match:
        raise ValueError(f"Invalid hunk header: {header}")

    old_start = int(match.group(1))
    old_count = int(match.group(2)) if match.group(2) else 1
    new_start = int(match.group(3))
    new_count = int(match.group(4)) if match.group(4) else 1

    # Parse hunk lines
    lines: List[Tuple[str, str]] = []
    for line in hunk_lines[1:]:
        if not line:
            continue
        if line[0] in (' ', '-', '+'):
            operation = line[0]
            content = line[1:] if len(line) > 1 else ""
            lines.append((operation, content))
        else:
            # Context line without prefix (treat as context)
            lines.append((' ', line))

    return Hunk(
        old_start=old_start,
        old_count=old_count,
        new_start=new_start,
        new_count=new_count,
        lines=lines
    )


def parse_unified_diff(diff_content: str) -> FileDiff:
    """Parse a unified diff for a single file.

    Args:
        diff_content: Complete diff content in unified diff format

    Returns:
        FileDiff object with parsed information

    Raises:
        ValueError: If diff format is invalid or contains multiple files
    """
    lines = diff_content.strip().split('\n')
    if not lines:
        raise ValueError("Empty diff content")

    # Find file headers
    old_path = None
    new_path = None
    hunks: List[Hunk] = []
    current_hunk_lines: List[str] = []
    file_count = 0

    for line in lines:
        # Check for file headers
        if line.startswith('---'):
            if old_path is not None:
                file_count += 1
                if file_count > 1:
                    raise ValueError(
                        "Diff contains multiple files. "
                        "Please provide a diff for a single file at a time."
                    )
            # Extract path, removing 'a/' prefix if present
            old_path = line[4:].strip()
            if old_path.startswith('a/'):
                old_path = old_path[2:]
            # Remove @ prefix if present (file reference syntax)
            if old_path.startswith('@'):
                old_path = old_path[1:]
        elif line.startswith('+++'):
            # Extract path, removing 'b/' prefix if present
            new_path = line[4:].strip()
            if new_path.startswith('b/'):
                new_path = new_path[2:]
            # Remove @ prefix if present (file reference syntax)
            if new_path.startswith('@'):
                new_path = new_path[1:]
        elif line.startswith('@@'):
            # Save previous hunk if exists
            if current_hunk_lines:
                hunks.append(parse_hunk(current_hunk_lines))
            # Start new hunk
            current_hunk_lines = [line]
        elif current_hunk_lines:
            # Add line to current hunk
            current_hunk_lines.append(line)

    # Save last hunk
    if current_hunk_lines:
        hunks.append(parse_hunk(current_hunk_lines))

    # Validate that we found file headers
    if old_path is None or new_path is None:
        raise ValueError(
            "Error: Invalid diff format.\n"
            "Missing file headers (--- and +++) or hunk headers (@@)."
        )

    return FileDiff(old_path=old_path, new_path=new_path, hunks=hunks)


def apply_hunk(file_lines: List[str], hunk: Hunk) -> List[str]:
    """Apply a single hunk to file content.

    Args:
        file_lines: Current content of the file as list of lines
        hunk: Hunk to apply

    Returns:
        Modified file content as list of lines

    Raises:
        ValueError: If hunk cannot be applied (context doesn't match)
    """
    # Find the position to apply the hunk
    # Use fuzzy search window: ±5 lines from expected position
    SEARCH_WINDOW = 5
    expected_position = max(0, hunk.old_start - 1)  # 0-indexed
    search_start = max(0, expected_position - SEARCH_WINDOW)
    search_end = min(len(file_lines), expected_position + SEARCH_WINDOW + 1)

    # Extract context and operations from hunk
    context_lines = []
    operations = []
    for op, content in hunk.lines:
        operations.append((op, content))
        if op in (' ', '-'):
            context_lines.append(content)

    # Try to find matching context in the file
    # Strategy 1: Try within search window first (±5 lines)
    found_position = None
    for i in range(search_start, search_end):
        match = True
        context_idx = 0
        for op, content in operations:
            if op in (' ', '-'):
                if i + context_idx >= len(file_lines):
                    match = False
                    break
                if file_lines[i + context_idx] != content:
                    match = False
                    break
                context_idx += 1
        if match:
            found_position = i
            break

    # Strategy 2: If not found, search entire file as fallback
    if found_position is None:
        for i in range(0, len(file_lines)):
            match = True
            context_idx = 0
            for op, content in operations:
                if op in (' ', '-'):
                    if i + context_idx >= len(file_lines):
                        match = False
                        break
                    if file_lines[i + context_idx] != content:
                        match = False
                        break
                    context_idx += 1
            if match:
                found_position = i
                break

    if found_position is None:
        raise ValueError(
            f"Hunk at line {hunk.old_start} does not match the file content.\n"
            f"Expected context not found in entire file."
        )

    # Apply the hunk
    result = file_lines[:found_position]
    current_pos = found_position

    for op, content in operations:
        if op == ' ':
            # Context line - keep it
            result.append(file_lines[current_pos])
            current_pos += 1
        elif op == '-':
            # Deletion - skip the line
            current_pos += 1
        elif op == '+':
            # Addition - add new line
            result.append(content)

    # Add remaining lines after the hunk
    result.extend(file_lines[current_pos:])

    return result


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
def apply_diff(diff_content: str) -> str:
    """Apply a unified diff to a single file.

    This tool applies changes from a unified diff format to an existing file.
    The diff must contain changes for exactly one file and can include multiple hunks.

    Args:
        diff_content: Complete diff in unified diff format for a single file.
                     Must include file headers (--- and +++) and hunk headers (@@).
                     Can contain one or multiple hunks for the same file.

    Returns:
        Success message with statistics, or detailed error message if operation fails.

    Example Input (single hunk):
        ---
        --- a/src/calculator.py
        +++ b/src/calculator.py
        @@ -10,3 +10,4 @@
         def add(a, b):
        -    return a + b
        +    # Add two numbers
        +    return a + b
        ---

    Example Input (multiple hunks):
        ---
        --- a/src/calculator.py
        +++ b/src/calculator.py
        @@ -10,3 +10,4 @@
         def add(a, b):
             return a + b
        +
        @@ -20,2 +21,4 @@
         def multiply(a, b):
        +    # Multiply two numbers
             return a * b
        ---

    Success Output:
        Successfully applied diff to src/calculator.py
        - 2 hunks applied
        - 3 lines added, 1 line removed

    Error Cases:
        - File not found: Returns "Error: File not found: {path}"
        - Invalid format: Returns "Error: Invalid diff format..."
        - Hunk mismatch: Returns "Error applying diff... Expected context not found"
        - Multiple files: Returns "Error: Diff contains multiple files..."
    """
    try:
        # Validate input
        if not diff_content or not diff_content.strip():
            return "Error: Empty diff content provided."

        # Parse the diff
        try:
            file_diff = parse_unified_diff(diff_content)
        except ValueError as e:
            return str(e)

        # Validate security: prevent path traversal
        file_path = Path(file_diff.new_path)
        try:
            # Resolve to absolute path and check it's within current directory
            resolved_path = file_path.resolve()
            cwd = Path.cwd().resolve()
            if not str(resolved_path).startswith(str(cwd)):
                return f"Error: Path traversal detected. File must be within current directory: {file_diff.new_path}"
        except Exception:
            return f"Error: Invalid file path: {file_diff.new_path}"

        # Check if file exists
        if not file_path.exists():
            return f"Error: File not found: {file_diff.new_path}\nCannot apply diff to non-existent file."

        if not file_path.is_file():
            return f"Error: Path is not a file: {file_diff.new_path}"

        # Read current file content
        try:
            content = file_path.read_text(encoding="utf-8")
            file_lines = content.split('\n')
        except UnicodeDecodeError:
            return f"Error: File is not a valid UTF-8 text file: {file_diff.new_path}"
        except PermissionError:
            return f"Error: Permission denied reading file: {file_diff.new_path}"

        # Apply each hunk sequentially
        lines_added = 0
        lines_removed = 0

        try:
            for hunk in file_diff.hunks:
                # Count additions and removals
                for op, _ in hunk.lines:
                    if op == '+':
                        lines_added += 1
                    elif op == '-':
                        lines_removed += 1

                # Apply the hunk
                file_lines = apply_hunk(file_lines, hunk)

        except ValueError as e:
            return f"Error applying diff to {file_diff.new_path}:\n{str(e)}"

        # Write the modified content back to file
        try:
            new_content = '\n'.join(file_lines)
            file_path.write_text(new_content, encoding="utf-8")
        except PermissionError:
            return f"Error: Permission denied writing to file: {file_diff.new_path}"
        except Exception as e:
            return f"Error writing to file: {str(e)}"

        # Build success message
        hunk_count = len(file_diff.hunks)
        hunk_word = "hunk" if hunk_count == 1 else "hunks"

        return (
            f"Successfully applied diff to {file_diff.new_path}\n"
            f"- {hunk_count} {hunk_word} applied\n"
            f"- {lines_added} lines added, {lines_removed} lines removed"
        )

    except Exception as e:
        return f"Unexpected error applying diff: {str(e)}"


# Export tools list for easy usage in chains
BASIC_TOOLS = [read_file, apply_diff]
