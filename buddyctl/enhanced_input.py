"""Enhanced input handler with real-time file autocompletion."""

import sys
from typing import Optional, Callable, List, Dict, Any
from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.formatted_text import HTML

from .file_indexer import FileIndexer
from .autosuggestion import AutoSuggestionHandler
from .visual_suggestions import VisualSuggestionDisplay


class EnhancedInteractiveInput:
    """Enhanced input with real-time file autocompletion suggestions."""

    def __init__(self, file_indexer: FileIndexer, prompt_text: str = "> "):
        """Initialize enhanced interactive input.

        Args:
            file_indexer: File indexer for suggestions
            prompt_text: Prompt text to display
        """
        self.file_indexer = file_indexer
        self.suggestion_handler = AutoSuggestionHandler(file_indexer)
        self.visual_display = VisualSuggestionDisplay(self.suggestion_handler)
        self.prompt_text = prompt_text
        self.last_text = ""
        self.last_cursor_pos = 0

        # Create key bindings
        self.bindings = self._create_key_bindings()

    def _create_key_bindings(self) -> KeyBindings:
        """Create key bindings for enhanced input."""
        bindings = KeyBindings()

        # Create condition as lambda for prompt_toolkit compatibility
        has_suggestions_condition = Condition(lambda: self._has_file_suggestions())

        # Number selection (1-9)
        for i in range(1, 10):
            @bindings.add(str(i), filter=has_suggestions_condition)
            def _(event, number=i):
                self._handle_number_selection(event, number)

        # ESC to hide suggestions
        @bindings.add(Keys.Escape)
        def _(event):
            self.visual_display.hide_suggestions()

        # TAB for first suggestion
        @bindings.add(Keys.Tab, filter=has_suggestions_condition)
        def _(event):
            suggestions = self.visual_display.get_current_suggestions()
            if suggestions:
                self._apply_suggestion(event, suggestions[0])

        return bindings

    def _has_file_suggestions(self) -> bool:
        """Check if we have file suggestions visible."""
        return self.visual_display.is_visible and len(self.visual_display.current_suggestions) > 0

    def _handle_number_selection(self, event, number: int):
        """Handle selection by number key."""
        suggestion = self.visual_display.select_suggestion_by_number(number)
        if suggestion:
            self._apply_suggestion(event, suggestion)

    def _apply_suggestion(self, event, suggestion: Dict[str, Any]):
        """Apply selected suggestion to the buffer."""
        buffer = event.app.current_buffer
        text = buffer.text
        cursor_pos = buffer.cursor_position

        # Apply suggestion using the handler
        new_text, new_cursor_pos = self.suggestion_handler.apply_suggestion(
            text, cursor_pos, suggestion
        )

        # Update buffer
        buffer.text = new_text
        buffer.cursor_position = new_cursor_pos

        # Hide suggestions after selection
        self.visual_display.hide_suggestions()

    def _on_text_changed(self, buffer: Buffer):
        """Handle text changes in the buffer."""
        text = buffer.text
        cursor_pos = buffer.cursor_position

        # Only process if text or cursor position changed significantly
        if text != self.last_text or abs(cursor_pos - self.last_cursor_pos) > 0:
            self._update_suggestions(text, cursor_pos)
            self.last_text = text
            self.last_cursor_pos = cursor_pos

    def _update_suggestions(self, text: str, cursor_pos: int):
        """Update suggestions based on current input."""
        # Check if we're in a file reference context
        file_query = self.suggestion_handler.extract_file_query(text, cursor_pos)

        if file_query:
            # Show suggestions
            self.visual_display.show_suggestions(text, cursor_pos)
        else:
            # Hide suggestions if not in file context
            self.visual_display.hide_suggestions()

    def prompt(self, message: str = "") -> str:
        """Get input with real-time suggestions.

        Args:
            message: Optional prompt message

        Returns:
            User input string
        """
        prompt_text = message or self.prompt_text

        # Create session with our key bindings
        session = PromptSession(
            message=prompt_text,
            key_bindings=self.bindings,
        )

        # Hook into buffer changes
        def on_buffer_changed(buffer):
            self._on_text_changed(buffer)

        # Get the result
        try:
            result = session.prompt()
            # Make sure to hide suggestions when done
            self.visual_display.hide_suggestions()
            return result
        except (KeyboardInterrupt, EOFError):
            self.visual_display.hide_suggestions()
            raise


class RealTimeAutoCompleteInput:
    """Real-time autocomplete input using prompt_toolkit events."""

    def __init__(self, file_indexer: FileIndexer):
        """Initialize real-time autocomplete input."""
        self.file_indexer = file_indexer
        self.suggestion_handler = AutoSuggestionHandler(file_indexer)
        self.current_suggestions: List[Dict[str, Any]] = []

    def create_application(self, prompt_text: str = "> ") -> Application:
        """Create prompt_toolkit application with real-time suggestions."""

        # Create buffer
        buffer = Buffer(
            on_text_changed=self._on_text_changed,
            multiline=False,
        )

        # Create key bindings
        bindings = self._create_key_bindings()

        # Create layout
        input_window = Window(
            content=BufferControl(
                buffer=buffer,
                focusable=True,
            ),
            height=1,
        )

        suggestion_control = FormattedTextControl(
            text=self._get_suggestion_text,
            focusable=False,
        )

        suggestion_window = Window(
            content=suggestion_control,
            height=lambda: min(len(self.current_suggestions) + 2, 8) if self.current_suggestions else 0,
            dont_extend_height=True,
        )

        layout = Layout(
            HSplit([
                input_window,
                suggestion_window,
            ])
        )

        # Create application
        app = Application(
            layout=layout,
            key_bindings=bindings,
            full_screen=False,
        )

        return app

    def _create_key_bindings(self) -> KeyBindings:
        """Create key bindings for the application."""
        bindings = KeyBindings()

        # Number selection
        for i in range(1, 10):
            @bindings.add(str(i))
            def _(event, number=i):
                if self.current_suggestions and number <= len(self.current_suggestions):
                    suggestion = self.current_suggestions[number - 1]
                    self._apply_suggestion(event, suggestion)

        # TAB completion
        @bindings.add(Keys.Tab)
        def _(event):
            if self.current_suggestions:
                self._apply_suggestion(event, self.current_suggestions[0])

        # Enter to submit
        @bindings.add(Keys.ControlM)
        def _(event):
            event.app.exit(result=event.app.current_buffer.text)

        # Ctrl+C to cancel
        @bindings.add(Keys.ControlC)
        def _(event):
            event.app.exit(exception=KeyboardInterrupt())

        return bindings

    def _on_text_changed(self, buffer: Buffer):
        """Handle buffer text changes."""
        text = buffer.text
        cursor_pos = buffer.cursor_position

        # Update suggestions
        self.current_suggestions = self.suggestion_handler.get_suggestions(
            text, cursor_pos, max_results=8
        )

    def _get_suggestion_text(self) -> str:
        """Get formatted text for suggestions."""
        if not self.current_suggestions:
            return ""

        lines = ["📁 File suggestions:"]
        for i, suggestion in enumerate(self.current_suggestions, 1):
            icon = "📁" if suggestion['type'] == 'folder' else "📄"
            name = suggestion['display']
            color = "blue" if suggestion['type'] == 'folder' else "white"
            lines.append(f"  {i}. {icon} {name}")

        lines.append("💡 Press TAB or 1-9 to select")
        return "\n".join(lines)

    def _apply_suggestion(self, event, suggestion: Dict[str, Any]):
        """Apply suggestion to buffer."""
        buffer = event.app.current_buffer
        text = buffer.text
        cursor_pos = buffer.cursor_position

        new_text, new_cursor_pos = self.suggestion_handler.apply_suggestion(
            text, cursor_pos, suggestion
        )

        buffer.text = new_text
        buffer.cursor_position = new_cursor_pos

        # Clear suggestions after selection
        self.current_suggestions = []

    def prompt(self, message: str = "> ") -> str:
        """Run the input prompt.

        Args:
            message: Prompt message

        Returns:
            User input
        """
        app = self.create_application(message)
        return app.run()


class SimpleRealTimeInput:
    """Simplified real-time input with inline suggestions."""

    def __init__(self, file_indexer: FileIndexer):
        """Initialize simple real-time input."""
        self.file_indexer = file_indexer
        self.suggestion_handler = AutoSuggestionHandler(file_indexer)

    def input_with_suggestions(self, prompt_text: str = "> ") -> str:
        """Get input with inline suggestions.

        Args:
            prompt_text: Prompt text

        Returns:
            User input
        """
        print_formatted_text(HTML(f"<ansigreen>{prompt_text}</ansigreen>"), end="")

        result = ""
        while True:
            try:
                # Use simple input for now - this is a fallback implementation
                result = input()
                break
            except KeyboardInterrupt:
                print()
                raise
            except EOFError:
                break

        return result