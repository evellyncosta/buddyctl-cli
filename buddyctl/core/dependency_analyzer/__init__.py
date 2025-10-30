"""
Dependency Analyzer Module

Automatically detects and resolves file dependencies across multiple languages.
"""

from .base import ImportExtractor
from .python_extractor import PythonImportExtractor
from .kotlin_extractor import KotlinImportExtractor
from .factory import get_extractor, analyze_dependencies, get_supported_extensions

__all__ = [
    "ImportExtractor",
    "PythonImportExtractor",
    "KotlinImportExtractor",
    "get_extractor",
    "analyze_dependencies",
    "get_supported_extensions",
]
