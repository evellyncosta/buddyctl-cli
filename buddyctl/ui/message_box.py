"""
Reusable message box system for CLI output.

Provides formatted message boxes with colors and emojis for different message types.
Inspired by fix-24 implementation in stackspot_chain.py.
"""

from enum import Enum
from typing import Optional


class BoxType(Enum):
    """Message box types with associated colors and emojis."""
    SUCCESS = ("✅", "\033[92m")  # Green
    ERROR = ("❌", "\033[91m")    # Red
    WARNING = ("⚠️", "\033[93m")  # Yellow
    INFO = ("ℹ️", "\033[94m")     # Blue


class MessageBox:
    """
    Utility class for printing formatted message boxes to the console.

    All methods are static and can be used without instantiation.

    Example:
        MessageBox.success("Diff aplicado com sucesso", "Arquivo: test.py")
        MessageBox.error("Falha ao aplicar diff", "Erro: File not found")
        MessageBox.warning("Tentando novamente", "Tentativa 2/3")
    """

    # Box formatting constants
    BOX_WIDTH = 62
    BOX_CHAR = "*"
    RESET_COLOR = "\033[0m"

    @staticmethod
    def _format_box(
        message: str,
        box_type: BoxType,
        details: Optional[str] = None
    ) -> str:
        """
        Format a message box with the specified type.

        Args:
            message: Main message to display
            box_type: Type of box (SUCCESS, ERROR, WARNING, INFO)
            details: Optional additional details (shown on second line)

        Returns:
            Formatted box string with ANSI color codes
        """
        emoji, color_code = box_type.value

        # Build box content
        separator = MessageBox.BOX_CHAR * MessageBox.BOX_WIDTH
        main_line = f"  {emoji} {message}"

        # Build box content lines
        lines = [
            f"\n{separator}",
            main_line
        ]

        if details:
            lines.append(f"  {details}")

        lines.append(f"{separator}\n")

        # Join and apply color
        box_content = "\n".join(lines)
        return f"{color_code}{box_content}{MessageBox.RESET_COLOR}"

    @staticmethod
    def success(message: str, details: Optional[str] = None) -> None:
        """
        Print a success message box (green with ✅).

        Args:
            message: Main success message
            details: Optional additional details

        Example:
            MessageBox.success("DIFF APLICADO COM SUCESSO", "Arquivo: calculator.py")
        """
        box = MessageBox._format_box(message, BoxType.SUCCESS, details)
        print(box)

    @staticmethod
    def error(message: str, details: Optional[str] = None) -> None:
        """
        Print an error message box (red with ❌).

        Args:
            message: Main error message
            details: Optional additional details

        Example:
            MessageBox.error("ERRO: Falha ao aplicar diff", "Erro: File not found")
        """
        box = MessageBox._format_box(message, BoxType.ERROR, details)
        print(box)

    @staticmethod
    def warning(message: str, details: Optional[str] = None) -> None:
        """
        Print a warning message box (yellow with ⚠️).

        Args:
            message: Main warning message
            details: Optional additional details

        Example:
            MessageBox.warning("RETRY: Tentando novamente (2/3)", "Razão: JSON truncado")
        """
        box = MessageBox._format_box(message, BoxType.WARNING, details)
        print(box)

    @staticmethod
    def info(message: str, details: Optional[str] = None) -> None:
        """
        Print an info message box (blue with ℹ️).

        Args:
            message: Main info message
            details: Optional additional details

        Example:
            MessageBox.info("Processando arquivo", "Arquivo: test.py")
        """
        box = MessageBox._format_box(message, BoxType.INFO, details)
        print(box)

    @staticmethod
    def print_box(
        message: str,
        box_type: str = "info",
        details: Optional[str] = None
    ) -> None:
        """
        Generic method to print a message box of any type.

        Args:
            message: Main message to display
            box_type: Type of box ("success", "error", "warning", "info")
            details: Optional additional details

        Example:
            MessageBox.print_box("Processing...", "info", "File: test.py")
        """
        box_type_map = {
            "success": BoxType.SUCCESS,
            "error": BoxType.ERROR,
            "warning": BoxType.WARNING,
            "info": BoxType.INFO
        }

        box_enum = box_type_map.get(box_type.lower(), BoxType.INFO)
        box = MessageBox._format_box(message, box_enum, details)
        print(box)


__all__ = ["MessageBox", "BoxType"]
