"""Auto-suggestion handler for file autocompletion with @ navigation."""

import re
from typing import List, Optional, Dict, Any, Tuple

from ..utils.file_indexer import FileIndexer


class AutoSuggestionHandler:
    """Handler for processing file autosuggestion with @ navigation."""

    def __init__(self, indexer: FileIndexer):
        """Initialize the auto-suggestion handler.

        Args:
            indexer: File indexer instance for getting suggestions
        """
        self.indexer = indexer

    def extract_file_query(self, text: str, cursor_pos: int) -> Optional[Tuple[str, int, int]]:
        """Extract file query from text at cursor position.

        Args:
            text: Full text input
            cursor_pos: Current cursor position

        Returns:
            Tuple of (query, start_pos, end_pos) or None if no file query found
        """
        if not text or cursor_pos < 0:
            return None

        # Find the closest @ symbol before cursor
        at_pos = -1
        for i in range(cursor_pos - 1, -1, -1):
            if text[i] == "@":
                at_pos = i
                break
            elif text[i].isspace():
                # Stop at whitespace
                break

        if at_pos == -1:
            return None

        # Extract query from @ to cursor or next whitespace
        query_start = at_pos + 1
        query_end = cursor_pos

        # Extend to next whitespace if cursor is in middle of word
        while query_end < len(text) and not text[query_end].isspace():
            query_end += 1

        query = text[query_start:query_end]
        return query, at_pos, query_end

    def get_suggestions(
        self, text: str, cursor_pos: int, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Get file suggestions for current input.

        Args:
            text: Full text input
            cursor_pos: Current cursor position
            max_results: Maximum number of suggestions

        Returns:
            List of suggestion dictionaries
        """
        file_query = self.extract_file_query(text, cursor_pos)
        if not file_query:
            return []

        query, _, _ = file_query
        raw_suggestions = self.indexer.get_suggestions(query, max_results)

        # Enhance suggestions with display formatting
        suggestions = []
        for i, suggestion in enumerate(raw_suggestions, 1):
            enhanced = suggestion.copy()
            enhanced["number"] = i
            enhanced["formatted_display"] = self._format_suggestion(suggestion, i)
            suggestions.append(enhanced)

        return suggestions

    def _format_suggestion(self, suggestion: Dict[str, Any], number: int) -> str:
        """Format a suggestion for display with colors and icons.

        Args:
            suggestion: Suggestion dictionary
            number: Suggestion number (1-9)

        Returns:
            Formatted HTML string for display
        """
        name = suggestion["name"]
        type_icon = "📁" if suggestion["type"] == "folder" else "📄"
        color = "ansiblue" if suggestion["type"] == "folder" else "white"

        display_name = name
        if suggestion["type"] == "folder":
            display_name += "/"

        return f"<{color}>{number}. {type_icon} {display_name}</{color}>"

    def format_suggestions_display(self, suggestions: List[Dict[str, Any]]) -> str:
        """Format multiple suggestions for display.

        Args:
            suggestions: List of suggestion dictionaries

        Returns:
            Formatted HTML string for all suggestions
        """
        if not suggestions:
            return ""

        lines = ["<ansiyellow>📁 File suggestions:</ansiyellow>"]
        for suggestion in suggestions:
            lines.append(f"  {suggestion['formatted_display']}")

        lines.append("")
        lines.append("<ansiyellow>💡 Press TAB to autocomplete, or type 1-9 to select</ansiyellow>")

        return "\n".join(lines)

    def apply_suggestion(
        self, text: str, cursor_pos: int, suggestion: Dict[str, Any]
    ) -> Tuple[str, int]:
        """Apply a file suggestion to the current text.

        Args:
            text: Current text
            cursor_pos: Current cursor position
            suggestion: Selected suggestion

        Returns:
            Tuple of (new_text, new_cursor_pos)
        """
        file_query = self.extract_file_query(text, cursor_pos)
        if not file_query:
            return text, cursor_pos

        query, start_pos, end_pos = file_query

        # Build replacement text
        replacement = suggestion["display"]

        # Replace the @query part with the suggestion
        new_text = text[:start_pos] + "@" + replacement + text[end_pos:]
        new_cursor_pos = start_pos + 1 + len(replacement)

        return new_text, new_cursor_pos

    def get_file_references(self, text: str) -> List[Dict[str, Any]]:
        """Extract all file references (@ patterns) from text.

        Args:
            text: Text to parse

        Returns:
            List of file reference dictionaries
        """
        references = []

        # Pattern to match @filename or @path/filename
        pattern = r"@([^\s@]+)"

        for match in re.finditer(pattern, text):
            file_path = match.group(1)

            # Check if file exists
            if self.indexer.file_exists(file_path):
                references.append(
                    {"path": file_path, "start": match.start(), "end": match.end(), "exists": True}
                )
            else:
                references.append(
                    {"path": file_path, "start": match.start(), "end": match.end(), "exists": False}
                )

        return references

    def load_referenced_files(
        self, text: str, max_file_size: int = 1024 * 1024
    ) -> Dict[str, Optional[str]]:
        """Load content of all referenced files in text.

        Args:
            text: Text containing file references
            max_file_size: Maximum file size to load

        Returns:
            Dictionary mapping file paths to their content (or None if failed)
        """
        references = self.get_file_references(text)
        file_contents = {}

        for ref in references:
            if ref["exists"]:
                content = self.indexer.get_file_content(ref["path"], max_file_size)
                file_contents[ref["path"]] = content
            else:
                file_contents[ref["path"]] = None

        return file_contents

    def validate_file_references(self, text: str) -> List[str]:
        """Validate all file references in text and return error messages.

        Args:
            text: Text containing file references

        Returns:
            List of error messages for invalid references
        """
        references = self.get_file_references(text)
        errors = []

        for ref in references:
            if not ref["exists"]:
                errors.append(f"File not found: @{ref['path']}")

        return errors

    def suggest_similar_files(self, file_path: str, max_suggestions: int = 5) -> List[str]:
        """Suggest similar files for a non-existent file path.

        Args:
            file_path: The file path that wasn't found
            max_suggestions: Maximum number of suggestions

        Returns:
            List of similar file paths
        """
        # Extract filename from path
        filename = file_path.split("/")[-1].lower()

        # Get all suggestions with similar names
        suggestions = self.indexer.get_suggestions(filename, max_suggestions * 2)

        # Filter and format results
        similar_files = []
        for suggestion in suggestions:
            if suggestion["name"].lower() != filename:  # Exclude exact matches
                similar_files.append(suggestion["display"])

        return similar_files[:max_suggestions]
