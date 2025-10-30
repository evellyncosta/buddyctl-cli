"""Interactive CLI shell for buddyctl."""

import logging
from typing import Dict, Callable, List, Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from pathlib import Path

from ..core.auth import StackSpotAuth, AuthenticationError
from ..core.config import BuddyConfig, ConfigurationError
from .agent_validator import AgentValidator, AgentValidationError
from ..core.provider_validator import ProviderValidator
from ..core.provider_registry import ProviderRegistry
from ..core.providers import ProviderManager
from ..ui.banner import display_banner
from ..utils.file_indexer import FileIndexer
from ..ui.autosuggestion import AutoSuggestionHandler
from ..utils.file_autocomplete import EnhancedFileAutoCompleter
from ..ui.visual_suggestions import VisualSuggestionDisplay

# Enhanced input module is available but not directly used in interactive shell


class InteractiveShell:
    """Interactive shell for buddyctl commands."""

    def __init__(self):
        self.auth = StackSpotAuth()
        self.config = BuddyConfig()
        self.validator = AgentValidator(self.auth)
        self.provider_validator = ProviderValidator(self.config)
        self.provider_manager = ProviderManager(self.config, auth=self.auth)
        self.commands: Dict[str, Callable] = {}
        self.running = True

        # Initialize default provider configuration
        self.config.initialize_default_providers()

        # Logging
        self.logger = logging.getLogger(__name__)

        # Initialize file indexing system
        self.file_indexer = FileIndexer()
        self.suggestion_handler = AutoSuggestionHandler(self.file_indexer)
        self.visual_display = VisualSuggestionDisplay(self.suggestion_handler)

        # Real-time suggestions will be handled by the completer

        # Setup prompt session with history
        history_file = Path.home() / ".buddyctl" / "history"
        history_file.parent.mkdir(exist_ok=True, mode=0o700)

        # Create enhanced completer
        command_completer = self._get_command_completer()
        self.file_completer = EnhancedFileAutoCompleter(self.file_indexer, command_completer)

        # Setup key bindings for number selection
        self.bindings = self._create_key_bindings()

        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=self.file_completer,
            key_bindings=self.bindings,
        )

        # Register built-in commands
        self._register_builtin_commands()

        # Build file index on startup
        self._initialize_file_index()

    def _initialize_file_index(self):
        """Initialize the file indexing system."""
        try:
            success = self.file_indexer.build_index()
            if success:
                print_formatted_text(
                    HTML(
                        "<ansigreen>✨ File autocompletion enabled! Type @ to reference files</ansigreen>"
                    )
                )
                print_formatted_text(HTML("<ansigreen>   • Use TAB for autocompletion</ansigreen>"))
                print_formatted_text(
                    HTML("<ansigreen>   • Type @ followed by filename or path</ansigreen>")
                )
            else:
                print_formatted_text(
                    HTML(
                        "<ansiyellow>⚠️ File indexing failed - file autocompletion may be limited</ansiyellow>"
                    )
                )
        except Exception as e:
            print_formatted_text(HTML(f"<ansiyellow>⚠️ File indexing error: {e}</ansiyellow>"))

    def _get_command_completer(self) -> WordCompleter:
        """Create command completer."""
        command_list = (
            [f"/{cmd}" for cmd in self.commands.keys()] if hasattr(self, "commands") else []
        )
        if not command_list:  # Fallback for initial setup
            command_list = ["/help", "/exit", "/quit", "/status", "/agent-default", "/clear", "/provider"]
        return WordCompleter(command_list, ignore_case=True)

    def _create_key_bindings(self) -> KeyBindings:
        """Create key bindings for enhanced functionality."""
        bindings = KeyBindings()

        # We'll handle number selection in a simpler way without filters for now
        # The complex filtering approach has issues with prompt_toolkit integration
        # This feature can be enhanced later with a different approach

        return bindings

    def _in_file_completion_mode(self) -> bool:
        """Check if we're currently in file completion mode."""
        try:
            if hasattr(self, "session") and self.session.app and self.session.app.current_buffer:
                text = self.session.app.current_buffer.text
                cursor_pos = self.session.app.current_buffer.cursor_position
                return self.suggestion_handler.extract_file_query(text, cursor_pos) is not None
        except:
            pass
        return False

    def _handle_number_selection(self, event, number: int):
        """Handle number-based file selection."""
        try:
            buffer = event.app.current_buffer
            text = buffer.text
            cursor_pos = buffer.cursor_position

            # Get current suggestions
            suggestions = self.file_completer.get_current_suggestions()
            if 1 <= number <= len(suggestions):
                selected = suggestions[number - 1]

                # Apply the suggestion
                new_text, new_cursor_pos = self.suggestion_handler.apply_suggestion(
                    text, cursor_pos, selected
                )

                # Update buffer
                buffer.text = new_text
                buffer.cursor_position = new_cursor_pos

        except Exception:
            pass  # Ignore errors in number selection

    def _register_builtin_commands(self):
        """Register built-in shell commands."""
        self.commands = {
            "help": self._cmd_help,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
            "status": self._cmd_status,
            "agent-default": self._cmd_agent_default,
            "clear": self._cmd_clear,
            "provider": self._cmd_provider,
        }

    def _get_prompt_text(self) -> str:
        """Generate dynamic prompt text with status indicators."""
        auth_status = self.auth.get_auth_status()
        config_status = self.config.get_config_status()

        # Auth indicator
        auth_icon = "✅" if auth_status["authenticated"] else "❌"

        # Agent indicator
        agent_icon = "🤖" if config_status["has_default_agent"] else "❓"

        # Provider indicator
        current_provider = config_status.get("current_provider", "stackspot")
        provider_status = self.provider_validator.get_provider_status(current_provider)
        if provider_status["implemented"] and provider_status["has_credentials"]:
            provider_icon = "🔮"
        elif provider_status["implemented"]:
            provider_icon = "⚠️"
        else:
            provider_icon = "❓"

        return f"buddyctl {auth_icon}{provider_icon}{agent_icon}> "

    def _parse_command(self, user_input: str) -> tuple[Optional[str], List[str]]:
        """Parse user input into command and arguments."""
        user_input = user_input.strip()

        if not user_input.startswith("/"):
            return None, []

        # Remove leading '/' and split
        parts = user_input[1:].split()

        if not parts:
            return None, []

        command = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        return command, args

    def _cmd_help(self, args: List[str]) -> None:
        """Show available commands."""
        print_formatted_text(HTML("<b>Available Commands:</b>"))
        print()

        commands_help = {
            "help": "Show this help message",
            "exit/quit": "Exit the interactive shell",
            "status": "Show current authentication and agent status",
            "agent-default": "Set the default agent ID",
            "provider": "List or change LLM provider",
            "clear": "Clear the screen",
        }

        for cmd, desc in commands_help.items():
            print_formatted_text(HTML(f"  <ansigreen>/{cmd}</ansigreen> - {desc}"))
        print()

    def _cmd_exit(self, args: List[str]) -> None:
        """Exit the shell."""
        print_formatted_text(HTML("<ansiyellow>Goodbye! 👋</ansiyellow>"))
        self.running = False

    def _cmd_status(self, args: List[str]) -> None:
        """Show current status."""
        auth_status = self.auth.get_auth_status()
        config_status = self.config.get_config_status()

        print_formatted_text(HTML("<b>Current Status:</b>"))
        print()

        # Authentication status
        if auth_status["authenticated"]:
            print_formatted_text(
                HTML(
                    f"✅ <ansigreen>Authentication: {auth_status['status']}</ansigreen> (Realm: {auth_status['realm']})"
                )
            )
        else:
            realm_info = f" (Realm: {auth_status['realm']})" if auth_status["realm"] else ""
            print_formatted_text(
                HTML(f"❌ <ansired>Authentication: {auth_status['status']}</ansired>{realm_info}")
            )

        # LLM Provider status
        current_provider = config_status.get("current_provider", "stackspot")
        provider_status = self.provider_validator.get_provider_status(current_provider)

        if provider_status["exists"]:
            provider_icon = "🔮"
            if provider_status["implemented"]:
                creds_status = "✓" if provider_status["has_credentials"] else "⚠️ missing credentials"
                print_formatted_text(
                    HTML(
                        f"{provider_icon} <ansigreen>LLM Provider: {provider_status['display_name']}</ansigreen> ({creds_status})"
                    )
                )
            else:
                print_formatted_text(
                    HTML(
                        f"{provider_icon} <ansiyellow>LLM Provider: {provider_status['display_name']} (not implemented)</ansiyellow>"
                    )
                )
        else:
            print_formatted_text(
                HTML(f"🔮 <ansired>LLM Provider: {current_provider} (unknown)</ansired>")
            )

        # Agent status
        if config_status["has_default_agent"]:
            print_formatted_text(
                HTML(f"🤖 <ansigreen>Default Agent: {config_status['default_agent_id']}</ansigreen>")
            )
        else:
            print_formatted_text(HTML("🤖 <ansiyellow>Default Agent: Not configured</ansiyellow>"))

        print()

    def _cmd_agent_default(self, args: List[str]) -> None:
        """Set default agent ID."""
        if not args:
            print_formatted_text(HTML("<ansired>Error: Agent ID required</ansired>"))
            print_formatted_text(
                HTML("Usage: <ansiblue>/agent-default &lt;agent_id&gt;</ansiblue>")
            )
            return

        agent_id = args[0]

        try:
            # Validate agent ID
            self.validator.validate_agent(agent_id, check_existence=False)
            self.config.set_default_agent_id(agent_id)
            print_formatted_text(HTML(f"<ansigreen>✓ Default agent set to: {agent_id}</ansigreen>"))
        except (ConfigurationError, AgentValidationError) as e:
            print_formatted_text(HTML(f"<ansired>Error: {e}</ansired>"))

    def _cmd_clear(self, args: List[str]) -> None:
        """Clear the screen."""
        import os

        os.system("clear" if os.name == "posix" else "cls")
        # Redisplay banner after clearing
        display_banner(self.auth, self.config)

    def _cmd_provider(self, args: List[str]) -> None:
        """List or change LLM provider."""
        # If no arguments, show interactive selection
        if not args:
            self._show_provider_selection()
            return

        # If argument provided, try to set that provider
        provider_name = args[0].lower()
        self._set_provider(provider_name)

    def _show_provider_selection(self) -> None:
        """Show interactive provider selection menu."""
        providers = self.provider_validator.list_providers(include_unimplemented=True)
        current_provider = self.config.get_current_provider()

        print_formatted_text(HTML("<b>Available LLM Providers:</b>"))
        print()

        for idx, provider in enumerate(providers, 1):
            # Build status indicators
            indicators = []

            if provider["is_current"]:
                indicators.append("<ansigreen>current</ansigreen>")

            if provider["implemented"]:
                indicators.append("<ansigreen>✓</ansigreen>")
            else:
                indicators.append("<ansiyellow>not implemented</ansiyellow>")

            if provider["has_credentials"]:
                indicators.append("<ansigreen>credentials OK</ansigreen>")
            elif provider["implemented"]:
                indicators.append("<ansired>missing credentials</ansired>")

            status = " - " + ", ".join(indicators) if indicators else ""

            # Show provider
            prefix = "→ " if provider["is_current"] else "  "
            print_formatted_text(
                HTML(
                    f"{prefix}<ansiblue>{idx}. {provider['display_name']}</ansiblue> {status}"
                )
            )

            # Show description
            if provider.get("description"):
                print_formatted_text(HTML(f"     {provider['description']}"))

            # Show missing credentials if any
            if provider["missing_credentials"] and provider["implemented"]:
                missing = ", ".join(provider["missing_credentials"])
                print_formatted_text(HTML(f"     <ansiyellow>Missing: {missing}</ansiyellow>"))

            print()

        print_formatted_text(
            HTML("<ansicyan>Use: /provider &lt;name&gt; to switch</ansicyan>")
        )
        print_formatted_text(
            HTML(
                "<ansicyan>Available names: stackspot, openai, anthropic, google, ollama</ansicyan>"
            )
        )

    def _set_provider(self, provider_name: str) -> None:
        """Set the LLM provider."""
        # Validate and set
        success, message = self.provider_validator.validate_and_set_provider(provider_name)

        if success:
            provider_info = ProviderRegistry.get_provider(provider_name)
            if message:
                # Warning about missing credentials
                print_formatted_text(HTML(f"<ansiyellow>⚠️  {message}</ansiyellow>"))
            print_formatted_text(
                HTML(
                    f"<ansigreen>✓ LLM provider set to: {provider_info.display_name}</ansigreen>"
                )
            )
        else:
            # Error
            print_formatted_text(HTML(f"<ansired>✗ Error: {message}</ansired>"))

    def _execute_command(self, command: str, args: List[str]) -> None:
        """Execute a parsed command."""
        if command not in self.commands:
            print_formatted_text(HTML(f"<ansired>Unknown command: /{command}</ansired>"))
            print_formatted_text(HTML("Type <ansiblue>/help</ansiblue> for available commands."))
            return

        try:
            self.commands[command](args)
        except Exception as e:
            print_formatted_text(HTML(f"<ansired>Error executing command: {e}</ansired>"))

    def _send_chat_message(self, message: str) -> None:
        """Send a chat message using the current provider (tools sempre disponíveis)."""
        # Process file references
        processed_message = self._process_file_references(message)
        if processed_message is None:
            return  # Error occurred during file processing

        try:
            # Get tools (sempre disponíveis - Feature 17)
            from ..integrations.langchain.tools import read_file, apply_diff
            tools = [read_file, apply_diff]

            # Get provider adapter (Feature 17)
            current_provider = self.config.get_current_provider()
            provider_adapter = self.provider_manager.get_adapter(current_provider)

            # Set file indexer for NEW_FILE support (Feature 29)
            if hasattr(provider_adapter, 'set_file_indexer'):
                provider_adapter.set_file_indexer(self.file_indexer)

            # Get executor with tools (SEMPRE, transparente)
            # Provider adapter decide internamente se usa Judge Agent, ReAct, ou native tools
            executor = provider_adapter.get_model_with_tools(tools=tools)

            # Feature 27: Enrich with dependencies (automatic multi-file support)
            # Check if executor is StackSpotChain and has enrich_with_dependencies method
            enriched_message = processed_message
            try:
                from pathlib import Path
                from ..integrations.langchain.chains.stackspot_chain import StackSpotChain

                if isinstance(executor, StackSpotChain):
                    # Try to enrich with dependencies
                    project_root = Path.cwd()
                    enriched_message = executor.enrich_with_dependencies(
                        processed_message,
                        project_root=project_root
                    )

                    # Log if dependencies were added
                    if len(enriched_message) > len(processed_message):
                        added_chars = len(enriched_message) - len(processed_message)
                        print_formatted_text(
                            HTML(f"<ansicyan>🔗 Detected dependencies (+{added_chars} chars context)</ansicyan>")
                        )
            except Exception as e:
                # If enrichment fails, just use original message
                self.logger.debug(f"Dependency enrichment failed (using original message): {e}")

            # Log request
            from ..core.logging import log_agent_request, log_agent_response
            log_agent_request(self.logger, f"{current_provider} executor", enriched_message)

            # Show loading indicator
            print_formatted_text(
                HTML("<ansicyan>🤖 buddyctl:</ansicyan> <ansiyellow>🤔 Pensando...</ansiyellow>")
            )

            # Execute (unified interface - Feature 17)
            result = executor.invoke(enriched_message)

            # Log response
            log_agent_response(self.logger, f"{current_provider} executor", result["output"])

            # Clear loading indicator and show result
            print("\r", end="")
            print_formatted_text(HTML("<ansigreen>✅ buddyctl:</ansigreen>"))
            print(result["output"])
            print()

        except RuntimeError as e:
            # ProviderManager wraps errors with mapped messages
            print("\r", end="")  # Clear loading indicator
            print_formatted_text(HTML(f"<ansired>❌ {e}</ansired>"))

            # Check for specific error patterns to provide helpful tips
            error_str = str(e)
            if "agent_id" in error_str.lower() and "not configured" in error_str.lower():
                print_formatted_text(
                    HTML("<ansiyellow>💡 Tip: Use /agent-default <id> to configure an agent</ansiyellow>")
                )
            elif "not available" in error_str.lower() or "credentials" in error_str.lower():
                print_formatted_text(
                    HTML("<ansiyellow>💡 Tip: Check your credentials and authentication</ansiyellow>")
                )
        except ValueError as e:
            # Configuration or validation errors
            print("\r", end="")
            print_formatted_text(HTML(f"<ansired>❌ Error: {e}</ansired>"))
        except Exception as e:
            # Unexpected errors
            print("\r", end="")
            print_formatted_text(HTML(f"<ansired>❌ Unexpected error: {e}</ansired>"))
            print_formatted_text(
                HTML("<ansiyellow>Please check your configuration and try again.</ansiyellow>")
            )

    def _process_file_references(self, message: str) -> Optional[str]:
        """Process file references in the message and load file contents.

        Args:
            message: Original message with potential file references

        Returns:
            Processed message with file contents or None if error occurred
        """
        # Check for file references
        file_references = self.suggestion_handler.get_file_references(message)

        if not file_references:
            return message  # No file references to process

        # Validate all file references
        errors = self.suggestion_handler.validate_file_references(message)
        if errors:
            print_formatted_text(HTML("<ansired>❌ File reference errors:</ansired>"))
            for error in errors:
                print_formatted_text(HTML(f"  • {error}"))

                # Suggest similar files for non-existent ones
                if "File not found:" in error:
                    file_path = error.replace("File not found: @", "")
                    similar_files = self.suggestion_handler.suggest_similar_files(file_path)
                    if similar_files:
                        print_formatted_text(HTML("    <ansiyellow>💡 Did you mean:</ansiyellow>"))
                        for similar in similar_files[:3]:
                            print_formatted_text(HTML(f"      • @{similar}"))

            print()
            return None

        # Load file contents
        try:
            file_contents = self.suggestion_handler.load_referenced_files(message)
            loaded_files = []

            print_formatted_text(HTML("<ansigreen>📁 Loading referenced files:</ansigreen>"))

            # Build enhanced message with file contents
            enhanced_message = message

            # Import formatter
            from ..integrations.langchain.context_formatter import format_file_with_line_numbers_safe

            for file_path, content in file_contents.items():
                if content is not None:
                    # Show which file was loaded
                    file_size = len(content.encode("utf-8"))
                    size_str = self._format_file_size(file_size)
                    print_formatted_text(
                        HTML(f"  • <ansiblue>@{file_path}</ansiblue> ({size_str})")
                    )

                    # Add file content to message WITH LINE NUMBERS
                    formatted_content = format_file_with_line_numbers_safe(file_path)
                    file_section = f"\n\n{formatted_content}"
                    enhanced_message += file_section
                    loaded_files.append(file_path)
                else:
                    print_formatted_text(
                        HTML(f"  • <ansired>@{file_path} (failed to load)</ansired>")
                    )

            if loaded_files:
                print_formatted_text(
                    HTML(f"<ansigreen>✅ Loaded {len(loaded_files)} file(s)</ansigreen>")
                )
                print()

            return enhanced_message

        except Exception as e:
            print_formatted_text(
                HTML(f"<ansired>❌ Error processing file references: {e}</ansired>")
            )
            return None

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def _get_user_input(self) -> str:
        """Get user input using enhanced input when available."""
        try:
            # Always use the session with file completer
            return self.session.prompt(self._get_prompt_text())
        except Exception as e:
            # If enhanced input fails, fallback to simple input
            print_formatted_text(HTML(f"<ansiyellow>⚠️ Input error: {e}</ansiyellow>"))
            return input(self._get_prompt_text())

    def _check_default_agent_configuration(self) -> None:
        """
        Check if default agent is configured and warn user if not.

        This validates BEFORE user tries to send messages, providing
        better UX by showing configuration requirements upfront.
        """
        config_status = self.config.get_config_status()

        if not config_status["has_default_agent"]:
            # Show prominent warning
            print_formatted_text(HTML("<ansiyellow>⚠️  WARNING: No default agent configured!</ansiyellow>"))
            print()
            print_formatted_text(HTML("    To use buddyctl, you need to configure a default agent ID."))
            print()
            print_formatted_text(HTML("    <b>Options:</b>"))
            print_formatted_text(HTML("    1. Set via command:  <ansiblue>/agent-default &lt;your-agent-id&gt;</ansiblue>"))
            print_formatted_text(HTML("    2. Set via env var: <ansiblue>export STACKSPOT_CODER_ID=&lt;your-agent-id&gt;</ansiblue>"))
            print()
            print_formatted_text(HTML("    You can still use commands like <ansiblue>/help</ansiblue> and <ansiblue>/status</ansiblue> without an agent."))
            print()

    def run(self) -> None:
        """Run the interactive shell."""
        # Attempt to ensure valid authentication before displaying banner
        # This proactively refreshes expired tokens for better UX
        try:
            self.auth.get_valid_token()
        except Exception:
            # Don't fail if auth doesn't work - just show the status
            pass

        # Display initial banner
        display_banner(self.auth, self.config)

        # Validate default agent configuration
        self._check_default_agent_configuration()

        print_formatted_text(HTML("<ansicyan>Welcome to buddyctl interactive shell!</ansicyan>"))
        print_formatted_text(HTML("• Type any message to chat with your agent"))
        print_formatted_text(
            HTML(
                "• Type <ansiblue>/help</ansiblue> for commands or <ansiblue>/exit</ansiblue> to quit"
            )
        )
        print()

        while self.running:
            try:
                # Get user input with enhanced autocompletion if available
                user_input = self._get_user_input()

                if not user_input.strip():
                    continue

                # Check if it's a command (starts with /) or a chat message
                if user_input.startswith("/"):
                    # Parse and execute command
                    command, args = self._parse_command(user_input)

                    if command is None:
                        print_formatted_text(
                            HTML(
                                "<ansiyellow>Commands must start with '/' (e.g., /help)</ansiyellow>"
                            )
                        )
                        continue

                    self._execute_command(command, args)
                else:
                    # It's a chat message - send to agent
                    self._send_chat_message(user_input)

            except KeyboardInterrupt:
                # Handle Ctrl+C gracefully
                print_formatted_text(HTML("\n<ansiyellow>Use /exit to quit</ansiyellow>"))
                continue
            except EOFError:
                # Handle Ctrl+D
                break

        print()  # Add final newline
