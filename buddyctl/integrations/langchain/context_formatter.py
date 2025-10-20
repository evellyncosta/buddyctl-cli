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
Context formatting for sending to LLMs.

Formats files and data in a structured way to improve
the quality of agent responses.
"""

from pathlib import Path


def format_file_with_line_numbers(file_path: str) -> str:
    """
    Format file with line numbers for LLM context.

    Output format:
        File: calculator.py (15 lines total)
        ────────────────────────────────────────────
           1 | def add_two_numbers(a, b):
           2 |     return a + b
           3 |
          ...
          15 | print(result)
        ────────────────────────────────────────────

    Args:
        file_path: File path (absolute or relative)

    Returns:
        String formatted with line numbers (no truncation)

    Raises:
        FileNotFoundError: If file doesn't exist
        UnicodeDecodeError: If file is not UTF-8

    Examples:
        >>> content = format_file_with_line_numbers("src/main.py")
        >>> print(content)
        File: src/main.py (42 lines total)
        ────────────────────────────────────────────
           1 | import sys
           2 |
           3 | def main():
        ...
          42 | if __name__ == "__main__":
        ────────────────────────────────────────────
    """
    path = Path(file_path)

    # Validations
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    # Read content
    content = path.read_text(encoding="utf-8")
    lines = content.split('\n')
    total_lines = len(lines)

    # Calculate line number width (for alignment)
    line_num_width = len(str(total_lines))

    # Build header
    separator = "─" * 60
    header = f"File: {file_path} ({total_lines} lines total)\n{separator}"

    # Format each line
    formatted_lines = []
    for i, line in enumerate(lines, start=1):
        # NO TRUNCATION - show full lines
        # (Truncation was causing diff validation failures because Main Agent
        # saw truncated content but generated diffs for full lines)

        # Format: "   1 | content"
        formatted_line = f"{i:>{line_num_width}} | {line}"
        formatted_lines.append(formatted_line)

    # Build footer
    footer = separator

    # Combine everything
    result = f"{header}\n" + "\n".join(formatted_lines) + f"\n{footer}"
    return result


def format_file_with_line_numbers_safe(file_path: str) -> str:
    """
    Safe version of format_file_with_line_numbers that doesn't raise exceptions.

    Returns formatted error message if it fails.

    Args:
        file_path: File path

    Returns:
        Formatted content or error message

    Examples:
        >>> content = format_file_with_line_numbers_safe("missing.txt")
        >>> print(content)
        Error reading file: missing.txt
        File not found
    """
    try:
        return format_file_with_line_numbers(file_path)
    except FileNotFoundError:
        return f"Error reading file: {file_path}\nFile not found"
    except UnicodeDecodeError:
        return f"Error reading file: {file_path}\nFile is not valid UTF-8"
    except Exception as e:
        return f"Error reading file: {file_path}\n{str(e)}"


__all__ = ["format_file_with_line_numbers", "format_file_with_line_numbers_safe"]
