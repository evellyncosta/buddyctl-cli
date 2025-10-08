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


# Export tools list for easy usage in chains
BASIC_TOOLS = [read_file]
