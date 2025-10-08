"""Interactive CLI shell for buddyctl."""

import sys
import os
from typing import Dict, Callable, List, Optional, Any
from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from pathlib import Path

from .auth import StackSpotAuth, AuthenticationError
from .config import BuddyConfig, ConfigurationError
from .agent_validator import AgentValidator, AgentValidationError
from .banner import display_banner
from .chat_client import ChatClient
from .file_indexer import FileIndexer
from .autosuggestion import AutoSuggestionHandler
from .file_autocomplete import EnhancedFileAutoCompleter
from .visual_suggestions import VisualSuggestionDisplay
# Enhanced input module is available but not directly used in interactive shell


class InteractiveShell:
    """Interactive shell for buddyctl commands."""
    
    def __init__(self):
        self.auth = StackSpotAuth()
        self.config = BuddyConfig()
        self.validator = AgentValidator(self.auth)
        self.chat_client = ChatClient(self.auth, self.config)
        self.commands: Dict[str, Callable] = {}
        self.running = True

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
                print_formatted_text(HTML("<ansigreen>✨ File autocompletion enabled! Type @ to reference files</ansigreen>"))
                print_formatted_text(HTML("<ansigreen>   • Use TAB for autocompletion</ansigreen>"))
                print_formatted_text(HTML("<ansigreen>   • Type @ followed by filename or path</ansigreen>"))
            else:
                print_formatted_text(HTML("<ansiyellow>⚠️ File indexing failed - file autocompletion may be limited</ansiyellow>"))
        except Exception as e:
            print_formatted_text(HTML(f"<ansiyellow>⚠️ File indexing error: {e}</ansiyellow>"))

    def _get_command_completer(self) -> WordCompleter:
        """Create command completer."""
        command_list = [f"/{cmd}" for cmd in self.commands.keys()] if hasattr(self, 'commands') else []
        if not command_list:  # Fallback for initial setup
            command_list = ["/help", "/exit", "/quit", "/status", "/agent-default", "/clear"]
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
            if hasattr(self, 'session') and self.session.app and self.session.app.current_buffer:
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
            'help': self._cmd_help,
            'exit': self._cmd_exit,
            'quit': self._cmd_exit,
            'status': self._cmd_status,
            'agent-default': self._cmd_agent_default,
            'clear': self._cmd_clear,
        }
    
    def _get_prompt_text(self) -> str:
        """Generate dynamic prompt text with status indicators."""
        auth_status = self.auth.get_auth_status()
        config_status = self.config.get_config_status()
        
        # Auth indicator
        auth_icon = "✅" if auth_status["authenticated"] else "❌"
        
        # Agent indicator
        agent_icon = "🤖" if config_status["has_default_agent"] else "❓"
        
        return f"buddyctl {auth_icon}{agent_icon}> "
    
    
    def _parse_command(self, user_input: str) -> tuple[Optional[str], List[str]]:
        """Parse user input into command and arguments."""
        user_input = user_input.strip()
        
        if not user_input.startswith('/'):
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
            'help': 'Show this help message',
            'exit/quit': 'Exit the interactive shell',
            'status': 'Show current authentication and agent status',
            'agent-default': 'Set the default agent ID',
            'clear': 'Clear the screen',
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
            print_formatted_text(HTML(f"✅ <ansigreen>Authentication: {auth_status['status']}</ansigreen> (Realm: {auth_status['realm']})"))
        else:
            realm_info = f" (Realm: {auth_status['realm']})" if auth_status['realm'] else ""
            print_formatted_text(HTML(f"❌ <ansired>Authentication: {auth_status['status']}</ansired>{realm_info}"))
        
        # Agent status
        if config_status["has_default_agent"]:
            print_formatted_text(HTML(f"🤖 <ansigreen>Default Agent: {config_status['default_agent_id']}</ansigreen>"))
        else:
            print_formatted_text(HTML("🤖 <ansiyellow>Default Agent: Not configured</ansiyellow>"))
        
        print()
    
    def _cmd_agent_default(self, args: List[str]) -> None:
        """Set default agent ID."""
        if not args:
            print_formatted_text(HTML("<ansired>Error: Agent ID required</ansired>"))
            print_formatted_text(HTML("Usage: <ansiblue>/agent-default &lt;agent_id&gt;</ansiblue>"))
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
        os.system('clear' if os.name == 'posix' else 'cls')
        # Redisplay banner after clearing
        display_banner(self.auth, self.config)
    
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
        """Send a chat message to the configured agent."""
        # Get default agent ID
        agent_id = self.config.get_default_agent_id()

        if not agent_id:
            print_formatted_text(HTML(
                "<ansired>No default agent configured. Use <ansiblue>/agent-default &lt;id&gt;</ansiblue> to set one.</ansired>"
            ))
            return

        # Process file references
        processed_message = self._process_file_references(message)
        if processed_message is None:
            return  # Error occurred during file processing
        
        try:
            # Show loading indicator
            print_formatted_text(HTML("<ansicyan>🤖 buddyctl:</ansicyan> <ansiyellow>⏳ Pensando...</ansiyellow>"), end="")
            
            # Collect response chunks
            response_chunks = []
            first_chunk = True
            
            def on_message_chunk(chunk: str):
                """Handle each chunk of the streaming response."""
                nonlocal first_chunk
                
                response_chunks.append(chunk)
                
                # Clear loading indicator on first chunk and show buddyctl label
                if first_chunk:
                    print("\r", end="")  # Clear current line
                    print_formatted_text(HTML("<ansicyan>🤖 buddyctl:</ansicyan> "), end="")
                    first_chunk = False
                
                print(chunk, end="", flush=True)
            
            # Send the chat message with streaming
            self.chat_client.chat_stream(agent_id, processed_message, on_message_chunk)
            
            # Add final newline
            print()
            
        except ValueError as e:
            print_formatted_text(HTML(f"<ansired>Error: {e}</ansired>"))
        except AuthenticationError as e:
            print_formatted_text(HTML(f"<ansired>Authentication error: {e}</ansired>"))
            print_formatted_text(HTML("Try checking your credentials and configuration."))
        except Exception as e:
            # Clear loading indicator
            print("\r", end="")

            # Check if it's a streaming-specific error
            error_str = str(e)
            if "streaming response content" in error_str or "status 403" in error_str or "status 401" in error_str:
                # Handle authentication/permission errors
                if "403" in error_str or "Forbidden" in error_str:
                    print_formatted_text(HTML("<ansired>❌ Access forbidden. Please check:</ansired>"))
                    print_formatted_text(HTML("  • Your API credentials are valid"))
                    print_formatted_text(HTML("  • You have permission to use this agent"))
                    print_formatted_text(HTML("  • Your account/realm is properly configured"))
                    print()
                    print_formatted_text(HTML("<ansiyellow>💡 Tip: Try re-authenticating or contact your administrator</ansiyellow>"))
                    return
                elif "401" in error_str or "Unauthorized" in error_str:
                    print_formatted_text(HTML("<ansired>❌ Authentication failed. Your session may have expired.</ansired>"))
                    print_formatted_text(HTML("<ansiyellow>💡 Tip: Try logging in again</ansiyellow>"))
                    return

                # Try fallback for other streaming errors
                print_formatted_text(HTML("<ansiyellow>⚠️ Streaming failed. Trying non-streaming mode...</ansiyellow>"))
            else:
                print_formatted_text(HTML(f"<ansired>Chat error: {e}</ansired>"))
                print_formatted_text(HTML("<ansiyellow>Trying fallback non-streaming mode...</ansiyellow>"))

            # Fallback to non-streaming
            try:
                # Show loading for fallback
                print_formatted_text(HTML("<ansicyan>🤖 buddyctl:</ansicyan> <ansiyellow>⏳ Processando...</ansiyellow>"), end="")
                response = self.chat_client.chat_non_stream(agent_id, processed_message)
                print("\r", end="")  # Clear loading
                print_formatted_text(HTML(f"<ansicyan>🤖 buddyctl:</ansicyan> {response.message}"))
            except Exception as fallback_error:
                print("\r", end="")  # Clear loading
                error_str = str(fallback_error)
                if "403" in error_str or "Forbidden" in error_str:
                    print_formatted_text(HTML("<ansired>❌ Fallback também falhou: Acesso negado</ansired>"))
                    print_formatted_text(HTML("<ansiyellow>Por favor verifique suas credenciais e permissões.</ansiyellow>"))
                elif "401" in error_str:
                    print_formatted_text(HTML("<ansired>❌ Fallback também falhou: Autenticação expirada</ansired>"))
                    print_formatted_text(HTML("<ansiyellow>Por favor faça login novamente.</ansiyellow>"))
                else:
                    print_formatted_text(HTML(f"<ansired>❌ Fallback também falhou: {fallback_error}</ansired>"))

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
            for file_path, content in file_contents.items():
                if content is not None:
                    # Show which file was loaded
                    file_size = len(content.encode('utf-8'))
                    size_str = self._format_file_size(file_size)
                    print_formatted_text(HTML(f"  • <ansiblue>@{file_path}</ansiblue> ({size_str})"))

                    # Add file content to message
                    file_section = f"\n\n--- Content of @{file_path} ---\n{content}\n--- End of @{file_path} ---"
                    enhanced_message += file_section
                    loaded_files.append(file_path)
                else:
                    print_formatted_text(HTML(f"  • <ansired>@{file_path} (failed to load)</ansired>"))

            if loaded_files:
                print_formatted_text(HTML(f"<ansigreen>✅ Loaded {len(loaded_files)} file(s)</ansigreen>"))
                print()

            return enhanced_message

        except Exception as e:
            print_formatted_text(HTML(f"<ansired>❌ Error processing file references: {e}</ansired>"))
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
    
    def run(self) -> None:
        """Run the interactive shell."""
        # Display initial banner
        display_banner(self.auth, self.config)
        
        print_formatted_text(HTML("<ansicyan>Welcome to buddyctl interactive shell!</ansicyan>"))
        print_formatted_text(HTML("• Type any message to chat with your agent"))
        print_formatted_text(HTML("• Type <ansiblue>/help</ansiblue> for commands or <ansiblue>/exit</ansiblue> to quit"))
        print()
        
        while self.running:
            try:
                # Get user input with enhanced autocompletion if available
                user_input = self._get_user_input()
                
                if not user_input.strip():
                    continue
                
                # Check if it's a command (starts with /) or a chat message
                if user_input.startswith('/'):
                    # Parse and execute command
                    command, args = self._parse_command(user_input)
                    
                    if command is None:
                        print_formatted_text(HTML("<ansiyellow>Commands must start with '/' (e.g., /help)</ansiyellow>"))
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