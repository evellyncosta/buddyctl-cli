"""File autocompletion integration with prompt_toolkit."""

from typing import List, Optional, Dict, Any, Iterable
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from .file_indexer import FileIndexer
from .autosuggestion import AutoSuggestionHandler


class FileAutoCompleter(Completer):
    """Custom completer for file autocompletion with @ navigation."""

    def __init__(self, indexer: FileIndexer, command_completer: Optional[Completer] = None):
        """Initialize the file auto-completer.

        Args:
            indexer: File indexer for getting suggestions
            command_completer: Optional command completer to chain with
        """
        self.indexer = indexer
        self.command_completer = command_completer
        self.suggestion_handler = AutoSuggestionHandler(indexer)

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """Get completions for the current document.

        Args:
            document: Current document state
            complete_event: Completion event

        Yields:
            Completion objects
        """
        text = document.text
        cursor_pos = document.cursor_position

        # Check if we're in a file reference context
        file_query = self.suggestion_handler.extract_file_query(text, cursor_pos)

        if file_query:
            # We're in file completion mode
            yield from self._get_file_completions(document, file_query)
        elif self.command_completer:
            # Fall back to command completion
            yield from self.command_completer.get_completions(document, complete_event)

    def _get_file_completions(self, document: Document, file_query_info) -> Iterable[Completion]:
        """Get file completions for the current query.

        Args:
            document: Current document
            file_query_info: Tuple of (query, start_pos, end_pos)

        Yields:
            File completion objects
        """
        query, start_pos, end_pos = file_query_info
        suggestions = self.indexer.get_suggestions(query, max_results=20)

        cursor_pos = document.cursor_position
        query_start_in_line = start_pos + 1  # +1 to skip the @

        for suggestion in suggestions:
            # Calculate how much of the current query to replace
            start_position = query_start_in_line - cursor_pos

            # Create display text with icon
            icon = "📁" if suggestion['type'] == 'folder' else "📄"
            display_text = f"{icon} {suggestion['display']}"

            # Create completion
            yield Completion(
                text=suggestion['display'],
                start_position=start_position,
                display=display_text,
            )


class EnhancedFileAutoCompleter(FileAutoCompleter):
    """Enhanced file auto-completer with better integration and number selection."""

    def __init__(self, indexer: FileIndexer, command_completer: Optional[Completer] = None):
        """Initialize the enhanced file auto-completer."""
        super().__init__(indexer, command_completer)
        self._current_suggestions: List[Dict[str, Any]] = []

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """Get completions with enhanced features."""
        text = document.text
        cursor_pos = document.cursor_position

        # Check for number selection (1-9)
        if self._handle_number_selection(document):
            return

        # Check if we're in a file reference context
        file_query = self.suggestion_handler.extract_file_query(text, cursor_pos)

        if file_query:
            # Cache suggestions for number selection
            self._current_suggestions = self.suggestion_handler.get_suggestions(
                text, cursor_pos, max_results=9
            )
            yield from self._get_enhanced_file_completions(document, file_query)
        elif self.command_completer:
            # Clear cached suggestions when not in file mode
            self._current_suggestions = []
            yield from self.command_completer.get_completions(document, complete_event)
        else:
            self._current_suggestions = []

    def _handle_number_selection(self, document: Document) -> bool:
        """Handle number-based selection (1-9).

        Args:
            document: Current document

        Returns:
            True if number selection was handled
        """
        text = document.text
        cursor_pos = document.cursor_position

        # Check if the last character is a number 1-9
        if cursor_pos > 0 and text[cursor_pos - 1].isdigit():
            digit = int(text[cursor_pos - 1])
            if 1 <= digit <= len(self._current_suggestions):
                # This would require integration with the input handler
                # to actually replace the text - this is a placeholder
                return True

        return False

    def _get_enhanced_file_completions(self, document: Document, file_query_info) -> Iterable[Completion]:
        """Get enhanced file completions with better formatting.

        Args:
            document: Current document
            file_query_info: Tuple of (query, start_pos, end_pos)

        Yields:
            Enhanced completion objects
        """
        query, start_pos, end_pos = file_query_info
        cursor_pos = document.cursor_position
        query_start_in_line = start_pos + 1  # +1 to skip the @

        for i, suggestion in enumerate(self._current_suggestions, 1):
            # Calculate replacement position
            start_position = query_start_in_line - cursor_pos

            # Create enhanced display with number and icon
            icon = "📁" if suggestion['type'] == 'folder' else "📄"
            type_color = "blue" if suggestion['type'] == 'folder' else "white"

            # Format display with number for easy selection
            display_text = f"{i}. {icon} {suggestion['display']}"

            yield Completion(
                text=suggestion['display'],
                start_position=start_position,
                display=display_text,
                style=f"fg:{type_color}",
            )

    def get_current_suggestions(self) -> List[Dict[str, Any]]:
        """Get current cached suggestions."""
        return self._current_suggestions.copy()

    def clear_suggestions(self):
        """Clear cached suggestions."""
        self._current_suggestions = []

    def select_suggestion_by_number(self, number: int) -> Optional[Dict[str, Any]]:
        """Select a suggestion by its number.

        Args:
            number: Suggestion number (1-9)

        Returns:
            Selected suggestion or None if invalid
        """
        if 1 <= number <= len(self._current_suggestions):
            return self._current_suggestions[number - 1]
        return None