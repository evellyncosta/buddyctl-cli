"""
Kotlin/Java Import Extractor

Extracts and resolves Kotlin and Java import statements to project files.
"""

import re
from pathlib import Path


class KotlinImportExtractor:
    """
    Extracts imports from Kotlin/Java source files.

    Supports:
    - import com.example.Foo
    - import com.example.service.*

    Resolves to:
    - src/main/kotlin/com/example/Foo.kt
    - src/main/java/com/example/Foo.java
    - src/com/example/Foo.kt (alternative structure)
    """

    # Compile regex pattern once for performance
    # Matches: import com.example.Foo or import com.example.*
    _import_pattern = re.compile(r'^\s*import\s+([\w.]+?)(?:\.\*)?(?:\s|;|$)', re.MULTILINE)

    def extract_imports(self, file_path: Path) -> list[str]:
        """
        Extract all import statements from a Kotlin/Java file.

        Args:
            file_path: Path to Kotlin/Java source file

        Returns:
            List of import paths (e.g., ['com.example.service.UserService', 'com.example.model.User'])
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return []

        # Extract import statements
        imports = self._import_pattern.findall(content)

        # Remove duplicates while preserving order
        seen = set()
        unique_imports = []
        for imp in imports:
            if imp not in seen:
                seen.add(imp)
                unique_imports.append(imp)

        return unique_imports

    def resolve_to_file(self, import_path: str, project_root: Path) -> Path | None:
        """
        Resolve a Kotlin/Java import to a file path.

        Tries multiple convention patterns:
        1. src/main/kotlin/com/example/Foo.kt (Kotlin Maven/Gradle)
        2. src/main/java/com/example/Foo.java (Java Maven/Gradle)
        3. src/com/example/Foo.kt (alternative)
        4. src/com/example/Foo.java (alternative)
        5. Any subdirectory containing the package structure (e.g., .doc/test-kotlin/com/example/Foo.kt)

        Args:
            import_path: Java package path (e.g., 'com.example.service.UserService')
            project_root: Project root directory

        Returns:
            Resolved Path if file exists, None otherwise
        """
        # Convert dotted path to file path: com.example.UserService -> com/example/UserService
        file_path = import_path.replace('.', '/')

        # Try common Kotlin/Java project structures
        search_paths = [
            # Kotlin (Maven/Gradle)
            project_root / "src" / "main" / "kotlin" / f"{file_path}.kt",
            # Java (Maven/Gradle)
            project_root / "src" / "main" / "java" / f"{file_path}.java",
            # Alternative structures
            project_root / "src" / f"{file_path}.kt",
            project_root / "src" / f"{file_path}.java",
            # Root level (less common)
            project_root / f"{file_path}.kt",
            project_root / f"{file_path}.java",
        ]

        for path in search_paths:
            if path.exists() and path.is_file():
                return path

        # Fallback: Search for the file anywhere in the project using glob
        # This handles custom directory structures like .doc/test-kotlin/
        # Only search for the filename pattern to improve performance
        for ext in ['.kt', '.java']:
            # Use glob to find any matching file with the correct package structure
            pattern = f"**/{file_path}{ext}"
            matches = list(project_root.glob(pattern))
            if matches:
                # Return the first match (there should typically be only one)
                return matches[0]

        return None

    def is_project_import(self, import_path: str, project_root: Path) -> bool:
        """
        Check if import is from the project (vs external library/stdlib).

        Strategy: If we can resolve it to a file in project_root, it's a project import.
        This automatically filters out:
        - kotlin.* (stdlib)
        - java.* (stdlib)
        - org.springframework.* (external library)
        - etc.

        Args:
            import_path: Java package path
            project_root: Project root directory

        Returns:
            True if import resolves to a file in the project
        """
        return self.resolve_to_file(import_path, project_root) is not None
