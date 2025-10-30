"""
Base Protocol for Import Extractors

Defines the interface that all language-specific extractors must implement.
"""

from pathlib import Path
from typing import Protocol


class ImportExtractor(Protocol):
    """
    Protocol defining the interface for language-specific import extractors.

    Each language implementation must provide:
    1. Import extraction from source files
    2. Import-to-file path resolution
    3. Project import filtering (exclude external libraries)
    """

    def extract_imports(self, file_path: Path) -> list[str]:
        """
        Extract all import statements from a source file.

        Args:
            file_path: Path to the source file to analyze

        Returns:
            List of import paths/packages found in the file

        Example:
            Python: ['app.services.user_service', 'app.models.user']
            Kotlin: ['com.example.service.UserService', 'com.example.model.User']
        """
        ...

    def resolve_to_file(self, import_path: str, project_root: Path) -> Path | None:
        """
        Resolve an import path to a physical file in the project.

        Args:
            import_path: The import string to resolve
            project_root: Root directory of the project

        Returns:
            Path to the file if found, None if not resolvable

        Example:
            Python: 'app.services.user_service' -> 'app/services/user_service.py'
            Kotlin: 'com.example.UserService' -> 'src/main/kotlin/com/example/UserService.kt'
        """
        ...

    def is_project_import(self, import_path: str, project_root: Path) -> bool:
        """
        Determine if an import belongs to the project (vs external library).

        Args:
            import_path: The import string to check
            project_root: Root directory of the project

        Returns:
            True if import is from the project, False if external

        Strategy:
            An import is considered "project import" if it can be resolved
            to an existing file within project_root. This automatically excludes:
            - External libraries (not in project)
            - Standard library imports (not in project)
            - Invalid/missing imports
        """
        ...
