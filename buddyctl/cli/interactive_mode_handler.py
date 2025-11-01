"""Interactive Mode Handler - Preview and review system for code modifications.

This handler provides a unified preview system used by ALL providers:
- StackSpot: System extracts blocks and calls this handler
- Google/OpenAI/Claude: LLM generates previews via dry_run, then calls this handler

The user sees the SAME UX regardless of provider.
"""

import difflib
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional
from pathlib import Path

from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import print_formatted_text
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table


class BlockAction(Enum):
    """Action to take for a modification block."""
    ACCEPT = "accept"
    REJECT = "reject"
    SKIP = "skip"


@dataclass
class BlockReviewResult:
    """Result of reviewing a single block."""
    block_index: int
    action: BlockAction
    reason: Optional[str] = None


@dataclass
class ModificationBlock:
    """Represents a single modification (SEARCH/REPLACE or NEW_FILE)."""
    block_type: str  # "search_replace" or "new_file"
    file_path: str
    search: Optional[str] = None  # For SEARCH/REPLACE
    replace: Optional[str] = None  # For SEARCH/REPLACE
    content: Optional[str] = None  # For NEW_FILE
    preview_diff: Optional[str] = None  # Unified diff preview


class InteractiveModeHandler:
    """
    Handler for interactive mode - shows previews and collects user decisions.

    This is the UNIFIED preview system used by all providers (StackSpot, Google, etc).
    The only difference is HOW the previews are generated:
    - StackSpot: System extracts blocks and generates previews manually
    - Others: LLM generates previews via tool calls with dry_run=True

    The user sees the SAME interface in both cases.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize interactive mode handler.

        Args:
            config: Configuration dict with display settings:
                    - show_diffs: bool (default True)
                    - show_line_numbers: bool (default True)
                    - color_diff: bool (default True)
                    - context_lines: int (default 3)
        """
        self.console = Console()
        self.config = config or {}

        # Display settings
        self.show_diffs = self.config.get("show_diffs", True)
        self.show_line_numbers = self.config.get("show_line_numbers", True)
        self.color_diff = self.config.get("color_diff", True)
        self.context_lines = self.config.get("context_lines", 3)

    def review_blocks(
        self,
        blocks: List[ModificationBlock],
        files_cache: Optional[Dict[str, str]] = None
    ) -> List[BlockReviewResult]:
        """
        Review modification blocks interactively.

        Shows each block with diff preview and asks user to accept/reject/skip.

        Args:
            blocks: List of ModificationBlock objects to review
            files_cache: Optional cache of file contents (for performance)

        Returns:
            List of BlockReviewResult with user decisions
        """
        if not blocks:
            return []

        results = []

        print_formatted_text(
            HTML(f"\n<b>📋 Interactive Review: {len(blocks)} modification(s) to review</b>\n")
        )

        for i, block in enumerate(blocks, 1):
            result = self._review_single_block(block, i, len(blocks), files_cache)
            results.append(result)

            # If user quit early, stop reviewing
            if result.reason == "quit":
                break

        return results

    def _review_single_block(
        self,
        block: ModificationBlock,
        block_num: int,
        total_blocks: int,
        files_cache: Optional[Dict[str, str]] = None
    ) -> BlockReviewResult:
        """Review a single modification block."""

        # Show block header
        self._show_block_header(block, block_num, total_blocks)

        # Show diff preview
        if block.block_type == "search_replace":
            self._show_search_replace_preview(block, files_cache)
        elif block.block_type == "new_file":
            self._show_new_file_preview(block)

        # Ask for decision
        action = self._prompt_for_action()

        if action == "quit":
            return BlockReviewResult(
                block_index=block_num - 1,
                action=BlockAction.REJECT,
                reason="quit"
            )

        # Map action to BlockAction
        action_map = {
            "accept": BlockAction.ACCEPT,
            "reject": BlockAction.REJECT,
            "skip": BlockAction.SKIP
        }

        block_action = action_map.get(action, BlockAction.REJECT)

        # Show confirmation
        self._show_action_confirmation(block_action, block_num)

        return BlockReviewResult(
            block_index=block_num - 1,
            action=block_action
        )

    def _show_block_header(
        self,
        block: ModificationBlock,
        block_num: int,
        total_blocks: int
    ) -> None:
        """Show header for a modification block."""
        file_name = Path(block.file_path).name if block.file_path else "unknown"
        block_type_label = "SEARCH/REPLACE" if block.block_type == "search_replace" else "NEW FILE"

        header = f"Block {block_num} of {total_blocks}: {file_name} ({block_type_label})"

        panel = Panel(
            header,
            style="bold cyan",
            expand=False
        )
        self.console.print(panel)
        print()

    def _show_search_replace_preview(
        self,
        block: ModificationBlock,
        files_cache: Optional[Dict[str, str]] = None
    ) -> None:
        """Show preview for SEARCH/REPLACE block."""
        print_formatted_text(HTML(f"<b>File:</b> {block.file_path}"))
        print()

        # Show diff
        if self.show_diffs:
            diff = self._generate_diff(
                block.search or "",
                block.replace or "",
                block.file_path
            )

            if self.color_diff:
                self._show_colored_diff(diff)
            else:
                print(diff)
        else:
            # Show SEARCH and REPLACE side by side
            print_formatted_text(HTML("<b>SEARCH:</b>"))
            print(block.search)
            print()
            print_formatted_text(HTML("<b>REPLACE:</b>"))
            print(block.replace)

        print()

    def _show_new_file_preview(self, block: ModificationBlock) -> None:
        """Show preview for NEW_FILE block."""
        print_formatted_text(HTML(f"<b>New File:</b> {block.file_path}"))
        print()

        # Show file content with syntax highlighting
        if block.content:
            # Determine language from file extension
            file_path = Path(block.file_path)
            extension_map = {
                ".py": "python",
                ".js": "javascript",
                ".kt": "kotlin",
                ".java": "java",
                ".go": "go",
                ".ts": "typescript",
                ".tsx": "typescript",
                ".jsx": "javascript"
            }
            language = extension_map.get(file_path.suffix, "text")

            syntax = Syntax(
                block.content,
                language,
                theme="monokai",
                line_numbers=self.show_line_numbers
            )
            self.console.print(syntax)

        print()

    def _generate_diff(
        self,
        search: str,
        replace: str,
        file_path: str
    ) -> str:
        """Generate unified diff between SEARCH and REPLACE."""
        search_lines = search.splitlines(keepends=True)
        replace_lines = replace.splitlines(keepends=True)

        diff = difflib.unified_diff(
            search_lines,
            replace_lines,
            fromfile=f"{file_path} (current)",
            tofile=f"{file_path} (proposed)",
            lineterm="",
            n=self.context_lines
        )

        return "\n".join(diff)

    def _show_colored_diff(self, diff: str) -> None:
        """Show colored diff output."""
        for line in diff.split("\n"):
            if line.startswith("+++") or line.startswith("---"):
                # File headers
                print_formatted_text(HTML(f"<b>{line}</b>"))
            elif line.startswith("@@"):
                # Hunk headers
                print_formatted_text(HTML(f"<ansicyan>{line}</ansicyan>"))
            elif line.startswith("+"):
                # Added lines
                print_formatted_text(HTML(f"<ansigreen>{line}</ansigreen>"))
            elif line.startswith("-"):
                # Removed lines
                print_formatted_text(HTML(f"<ansired>{line}</ansired>"))
            else:
                # Context lines
                print(line)

    def _prompt_for_action(self) -> str:
        """Prompt user for action on current block."""
        print_formatted_text(HTML("─" * 60))
        print_formatted_text(
            HTML(
                "<b>[a]</b>ccept  "
                "<b>[r]</b>eject  "
                "<b>[s]</b>kip  "
                "<b>[q]</b>uit review"
            )
        )

        while True:
            try:
                response = prompt("> ").strip().lower()

                if response in ["a", "accept"]:
                    return "accept"
                elif response in ["r", "reject"]:
                    return "reject"
                elif response in ["s", "skip"]:
                    return "skip"
                elif response in ["q", "quit"]:
                    return "quit"
                else:
                    print_formatted_text(
                        HTML("<ansiyellow>Invalid choice. Use a/r/s/q</ansiyellow>")
                    )
            except (KeyboardInterrupt, EOFError):
                return "quit"

    def _show_action_confirmation(self, action: BlockAction, block_num: int) -> None:
        """Show confirmation message for user action."""
        if action == BlockAction.ACCEPT:
            print_formatted_text(HTML(f"<ansigreen>✅ Block {block_num} accepted</ansigreen>"))
        elif action == BlockAction.REJECT:
            print_formatted_text(HTML(f"<ansired>❌ Block {block_num} rejected</ansired>"))
        elif action == BlockAction.SKIP:
            print_formatted_text(HTML(f"<ansiyellow>⏭️  Block {block_num} skipped</ansiyellow>"))
        print()

    def show_summary(self, results: List[BlockReviewResult]) -> None:
        """Show summary of review results."""
        if not results:
            return

        accepted = sum(1 for r in results if r.action == BlockAction.ACCEPT)
        rejected = sum(1 for r in results if r.action == BlockAction.REJECT)
        skipped = sum(1 for r in results if r.action == BlockAction.SKIP)

        # Create summary table
        table = Table(title="📊 REVIEW SUMMARY", show_header=False, box=None)
        table.add_column("Status", style="bold")
        table.add_column("Count")

        table.add_row("✅ Accepted", str(accepted), style="green")
        table.add_row("❌ Rejected", str(rejected), style="red")
        table.add_row("⏭️  Skipped", str(skipped), style="yellow")

        self.console.print(table)
        print()

    def confirm_apply(self, accepted_count: int) -> bool:
        """Ask user to confirm applying accepted modifications."""
        if accepted_count == 0:
            print_formatted_text(
                HTML("<ansiyellow>No modifications accepted. Nothing to apply.</ansiyellow>")
            )
            return False

        print_formatted_text(
            HTML(f"<b>Apply {accepted_count} accepted modification(s)?</b>")
        )
        print_formatted_text(
            HTML(
                "<b>[y]</b>es  "
                "<b>[n]</b>o"
            )
        )

        while True:
            try:
                response = prompt("> ").strip().lower()

                if response in ["y", "yes"]:
                    return True
                elif response in ["n", "no"]:
                    return False
                else:
                    print_formatted_text(
                        HTML("<ansiyellow>Invalid choice. Use y/n</ansiyellow>")
                    )
            except (KeyboardInterrupt, EOFError):
                return False


__all__ = ["InteractiveModeHandler", "BlockAction", "BlockReviewResult", "ModificationBlock"]
