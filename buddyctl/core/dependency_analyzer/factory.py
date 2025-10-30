"""
Factory for Import Extractors

Automatically selects the appropriate extractor based on file extension.
"""

from pathlib import Path
from typing import Optional

from .base import ImportExtractor
from .python_extractor import PythonImportExtractor
from .kotlin_extractor import KotlinImportExtractor


# Extension to extractor mapping
_EXTRACTORS: dict[str, ImportExtractor] = {
    '.py': PythonImportExtractor(),
    '.kt': KotlinImportExtractor(),
    '.java': KotlinImportExtractor(),  # Reuse Kotlin extractor for Java
}


def get_extractor(file_path: Path) -> Optional[ImportExtractor]:
    """
    Get the appropriate import extractor for a file.

    Args:
        file_path: Path to the source file

    Returns:
        ImportExtractor instance if language is supported, None otherwise

    Example:
        >>> extractor = get_extractor(Path('UserController.kt'))
        >>> isinstance(extractor, KotlinImportExtractor)
        True
    """
    suffix = file_path.suffix.lower()
    return _EXTRACTORS.get(suffix)


def analyze_dependencies(
    file_path: Path,
    project_root: Path,
    max_depth: int = 1
) -> list[Path]:
    """
    Analyze a file and return its project dependencies.

    Args:
        file_path: Path to the file to analyze
        project_root: Root directory of the project
        max_depth: Maximum depth for transitive dependencies (1 = direct only)

    Returns:
        List of Path objects representing related files in the project

    Example:
        >>> deps = analyze_dependencies(
        ...     Path('src/UserController.kt'),
        ...     Path('/project/root')
        ... )
        >>> # Returns [Path('src/UserService.kt'), Path('src/UserRepository.kt')]
    """
    # Get appropriate extractor
    extractor = get_extractor(file_path)
    if not extractor:
        return []

    # Extract imports from file
    try:
        imports = extractor.extract_imports(file_path)
    except Exception:
        return []

    # Resolve to project files (with transitive support)
    related_files = []
    seen = {file_path}  # Avoid circular dependencies

    # Use BFS (breadth-first search) for transitive dependencies
    current_level = [file_path]

    for depth in range(max_depth):
        next_level = []

        for current_file in current_level:
            # Get extractor for current file
            current_extractor = get_extractor(current_file)
            if not current_extractor:
                continue

            # Extract imports from current file
            try:
                current_imports = current_extractor.extract_imports(current_file)
            except Exception:
                continue

            # Process each import
            for import_path in current_imports:
                # Check if it's a project import
                if not current_extractor.is_project_import(import_path, project_root):
                    continue

                # Resolve to file
                resolved_file = current_extractor.resolve_to_file(import_path, project_root)
                if resolved_file and resolved_file not in seen:
                    related_files.append(resolved_file)
                    seen.add(resolved_file)
                    next_level.append(resolved_file)  # Add for next depth level

        # Move to next level
        current_level = next_level

        # Stop if no more dependencies found
        if not next_level:
            break

    return related_files


def get_supported_extensions() -> list[str]:
    """
    Get list of supported file extensions.

    Returns:
        List of extensions (e.g., ['.py', '.kt', '.java'])
    """
    return list(_EXTRACTORS.keys())
