"""Visual suggestions display for real-time file autocompletion."""

import sys
from typing import List, Dict, Any, Optional
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl

from .autosuggestion import AutoSuggestionHandler


class VisualSuggestionDisplay:
    """Component for displaying real-time visual file suggestions."""

    def __init__(self, suggestion_handler: AutoSuggestionHandler):
        """Initialize the visual suggestion display.

        Args:
            suggestion_handler: Handler for file suggestions
        """
        self.suggestion_handler = suggestion_handler
        self.current_suggestions: List[Dict[str, Any]] = []
        self.is_visible = False

    def show_suggestions(self, text: str, cursor_pos: int) -> bool:
        """Show suggestions for current input.

        Args:
            text: Current input text
            cursor_pos: Current cursor position

        Returns:
            True if suggestions are displayed, False otherwise
        """
        # Get suggestions for current context
        suggestions = self.suggestion_handler.get_suggestions(text, cursor_pos, max_results=9)

        if not suggestions:
            self.hide_suggestions()
            return False

        self.current_suggestions = suggestions
        self._display_suggestions()
        self.is_visible = True
        return True

    def hide_suggestions(self):
        """Hide the suggestions display."""
        if self.is_visible:
            self._clear_suggestions()
            self.is_visible = False
            self.current_suggestions = []

    def _display_suggestions(self):
        """Display the current suggestions."""
        if not self.current_suggestions:
            return

        # Build the suggestion display
        lines = []
        lines.append("📁 File suggestions:")

        for i, suggestion in enumerate(self.current_suggestions, 1):
            icon = "📁" if suggestion["type"] == "folder" else "📄"
            name = suggestion["display"]
            color = "ansiblue" if suggestion["type"] == "folder" else "white"

            line = f"  <{color}>{i}. {icon} {name}</{color}>"
            lines.append(line)

        lines.append("")
        lines.append("<ansiyellow>💡 Press TAB to autocomplete, or type 1-9 to select</ansiyellow>")

        # Print the suggestions above the current line
        suggestion_text = "\n".join(lines)

        # Move cursor up, print suggestions, then move back down
        sys.stdout.write(f"\033[{len(lines)}A")  # Move cursor up
        sys.stdout.flush()

        print_formatted_text(HTML(suggestion_text))
        sys.stdout.flush()

    def _clear_suggestions(self):
        """Clear the displayed suggestions."""
        if not self.current_suggestions:
            return

        # Calculate how many lines to clear
        lines_to_clear = (
            len(self.current_suggestions) + 3
        )  # suggestions + header + tip + empty line

        # Move cursor up and clear lines
        for _ in range(lines_to_clear):
            sys.stdout.write("\033[1A")  # Move up one line
            sys.stdout.write("\033[2K")  # Clear entire line
        sys.stdout.flush()

    def select_suggestion_by_number(self, number: int) -> Optional[Dict[str, Any]]:
        """Select a suggestion by number.

        Args:
            number: Suggestion number (1-9)

        Returns:
            Selected suggestion or None if invalid
        """
        if 1 <= number <= len(self.current_suggestions):
            return self.current_suggestions[number - 1]
        return None

    def get_current_suggestions(self) -> List[Dict[str, Any]]:
        """Get current suggestions."""
        return self.current_suggestions.copy()


class EnhancedVisualSuggestionDisplay:
    """Enhanced version using prompt_toolkit's layout system."""

    def __init__(self, suggestion_handler: AutoSuggestionHandler):
        """Initialize enhanced visual suggestion display."""
        self.suggestion_handler = suggestion_handler
        self.current_suggestions: List[Dict[str, Any]] = []
        self.suggestion_window: Optional[Window] = None

    def create_suggestion_window(self) -> Window:
        """Create a window for displaying suggestions."""
        if not self.current_suggestions:
            content = ""
        else:
            lines = ["📁 File suggestions:"]

            for i, suggestion in enumerate(self.current_suggestions, 1):
                icon = "📁" if suggestion["type"] == "folder" else "📄"
                name = suggestion["display"]
                color = "ansiblue" if suggestion["type"] == "folder" else "white"
                line = f"  {i}. {icon} {name}"
                lines.append(line)

            lines.append("")
            lines.append("💡 Press TAB to autocomplete, or type 1-9 to select")
            content = "\n".join(lines)

        return Window(
            content=FormattedTextControl(
                text=content,
                focusable=False,
            ),
            height=min(len(self.current_suggestions) + 3, 10),  # Max 10 lines
            dont_extend_height=True,
        )

    def update_suggestions(self, text: str, cursor_pos: int) -> bool:
        """Update suggestions based on current input.

        Args:
            text: Current input text
            cursor_pos: Current cursor position

        Returns:
            True if suggestions were updated, False otherwise
        """
        suggestions = self.suggestion_handler.get_suggestions(text, cursor_pos, max_results=9)

        if suggestions != self.current_suggestions:
            self.current_suggestions = suggestions
            return True

        return False

    def has_suggestions(self) -> bool:
        """Check if there are current suggestions."""
        return len(self.current_suggestions) > 0

    def select_suggestion_by_number(self, number: int) -> Optional[Dict[str, Any]]:
        """Select a suggestion by number."""
        if 1 <= number <= len(self.current_suggestions):
            return self.current_suggestions[number - 1]
        return None


class SimpleInlineSuggestions:
    """Simple inline suggestions that appear below the input."""

    def __init__(self, suggestion_handler: AutoSuggestionHandler):
        """Initialize simple inline suggestions."""
        self.suggestion_handler = suggestion_handler
        self.last_suggestions_count = 0

    def show_suggestions_inline(self, text: str, cursor_pos: int):
        """Show suggestions inline below the current input."""
        suggestions = self.suggestion_handler.get_suggestions(text, cursor_pos, max_results=6)

        # Clear previous suggestions
        self._clear_previous_suggestions()

        if not suggestions:
            return

        # Display new suggestions
        print_formatted_text(HTML("<ansiyellow>📁 Files:</ansiyellow>"), end=" ")

        for i, suggestion in enumerate(suggestions, 1):
            icon = "📁" if suggestion["type"] == "folder" else "📄"
            name = suggestion["name"]
            color = "ansiblue" if suggestion["type"] == "folder" else "white"

            if i > 1:
                print_formatted_text(HTML(" | "), end="")

            print_formatted_text(HTML(f"<{color}>{i}.{icon}{name}</{color}>"), end="")

        print()  # New line
        self.last_suggestions_count = 1  # Track that we printed one line

    def _clear_previous_suggestions(self):
        """Clear previously displayed suggestions."""
        if self.last_suggestions_count > 0:
            # Move cursor up and clear the line
            sys.stdout.write(f"\033[{self.last_suggestions_count}A")
            for _ in range(self.last_suggestions_count):
                sys.stdout.write("\033[2K")  # Clear line
                if _ < self.last_suggestions_count - 1:
                    sys.stdout.write("\033[1B")  # Move down
            sys.stdout.write("\033[1A")  # Move back to input line
            sys.stdout.flush()
            self.last_suggestions_count = 0
