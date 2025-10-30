"""
Python Import Extractor

Extracts and resolves Python import statements to project files.
"""

import re
from pathlib import Path


class PythonImportExtractor:
    """
    Extracts imports from Python source files.

    Supports:
    - import x.y.z
    - from x.y.z import Foo
    - from x.y import z

    Resolves to:
    - x/y/z.py (file)
    - x/y/z/__init__.py (package)
    """

    # Compile regex patterns once for performance
    _from_import_pattern = re.compile(r'^\s*from\s+([\w.]+)\s+import', re.MULTILINE)
    _import_pattern = re.compile(r'^\s*import\s+([\w.]+)', re.MULTILINE)

    def extract_imports(self, file_path: Path) -> list[str]:
        """
        Extract all import statements from a Python file.

        Args:
            file_path: Path to Python source file

        Returns:
            List of module paths (e.g., ['app.services.user_service', 'app.models'])
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return []

        imports = []

        # Extract "from x.y.z import ..." statements
        imports.extend(self._from_import_pattern.findall(content))

        # Extract "import x.y.z" statements
        imports.extend(self._import_pattern.findall(content))

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
        Resolve a Python import to a file path.

        Tries (in order):
        1. x/y/z.py (module file)
        2. x/y/z/__init__.py (package)

        Args:
            import_path: Python module path (e.g., 'app.services.user_service')
            project_root: Project root directory

        Returns:
            Resolved Path if file exists, None otherwise
        """
        # Convert dotted path to file path: app.services.user -> app/services/user
        file_path = import_path.replace('.', '/')

        # Try as module file: app/services/user.py
        module_file = project_root / f"{file_path}.py"
        if module_file.exists() and module_file.is_file():
            return module_file

        # Try as package: app/services/user/__init__.py
        package_file = project_root / file_path / "__init__.py"
        if package_file.exists() and package_file.is_file():
            return package_file

        return None

    def is_project_import(self, import_path: str, project_root: Path) -> bool:
        """
        Check if import is from the project (vs external library/stdlib).

        Strategy: If we can resolve it to a file in project_root, it's a project import.

        Args:
            import_path: Python module path
            project_root: Project root directory

        Returns:
            True if import resolves to a file in the project
        """
        return self.resolve_to_file(import_path, project_root) is not None
