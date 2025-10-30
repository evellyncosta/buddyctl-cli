"""File indexing system for efficient file autocompletion."""

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
import atexit


class FileIndexer:
    """System for indexing project files and providing fast autocompletion."""

    # Directories to ignore during indexing
    IGNORED_DIRS = {
        ".git",
        ".hg",
        ".svn",
        ".bzr",  # VCS
        "node_modules",
        "__pycache__",
        ".pytest_cache",  # Dependencies/cache
        "build",
        "dist",
        "target",
        ".cargo",  # Build outputs
        ".venv",
        "venv",
        "env",
        ".env",  # Virtual environments
        ".idea",
        ".vscode",
        ".vs",  # IDEs
        "coverage",
        ".coverage",
        ".nyc_output",  # Coverage
        ".DS_Store",
        "Thumbs.db",  # OS files
        ".tmp",
        "tmp",
        "temp",  # Temp directories
    }

    # File extensions to ignore
    IGNORED_EXTENSIONS = {
        ".pyc",
        ".pyo",
        ".pyd",
        ".so",
        ".dll",
        ".dylib",  # Compiled
        ".exe",
        ".bat",
        ".cmd",
        ".com",  # Executables
        ".log",
        ".pid",
        ".lock",
        ".tmp",  # Temp/log files
        ".swp",
        ".swo",
        "~",  # Editor temp files
    }

    def __init__(self, root_path: Optional[str] = None):
        """Initialize the file indexer.

        Args:
            root_path: Root directory to index. Defaults to current working directory.
        """
        self.root_path = Path(root_path or os.getcwd()).resolve()
        self.index_file: Optional[Path] = None
        self.file_tree: Optional[Dict[str, Any]] = None

        # Register cleanup on exit
        atexit.register(self.cleanup)

    def _should_ignore_dir(self, dir_name: str) -> bool:
        """Check if a directory should be ignored during indexing."""
        return dir_name.startswith(".") or dir_name in self.IGNORED_DIRS

    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if a file should be ignored during indexing."""
        # Hidden files (starting with .)
        if file_path.name.startswith("."):
            return True

        # Check extension
        if file_path.suffix.lower() in self.IGNORED_EXTENSIONS:
            return True

        # Very large files (> 50MB)
        try:
            if file_path.stat().st_size > 50 * 1024 * 1024:
                return True
        except (OSError, FileNotFoundError):
            return True

        return False

    def _build_file_tree(self, path: Path, relative_to: Path) -> Dict[str, Any]:
        """Recursively build file tree structure.

        Args:
            path: Current path being processed
            relative_to: Root path for relative calculations

        Returns:
            Dictionary representing the file/directory structure
        """
        try:
            if path.is_file():
                if self._should_ignore_file(path):
                    return None

                return {
                    "name": path.name,
                    "type": "file",
                    "path": str(path.relative_to(relative_to)),
                }

            elif path.is_dir():
                if self._should_ignore_dir(path.name):
                    return None

                children = []
                try:
                    for child_path in sorted(path.iterdir()):
                        child_tree = self._build_file_tree(child_path, relative_to)
                        if child_tree is not None:
                            children.append(child_tree)
                except (PermissionError, OSError):
                    # Skip directories we can't read
                    return None

                return {
                    "name": path.name,
                    "type": "folder",
                    "path": str(path.relative_to(relative_to)),
                    "children": children,
                }

        except (OSError, PermissionError):
            return None

        return None

    def build_index(self) -> bool:
        """Build the file index and save to temporary file.

        Returns:
            True if indexing was successful, False otherwise
        """
        try:
            print(f"🔍 Indexing files in {self.root_path}...")

            # Build the file tree
            self.file_tree = self._build_file_tree(self.root_path, self.root_path)

            if self.file_tree is None:
                print("❌ Failed to build file tree")
                return False

            # Create temporary file for the index
            fd, temp_path = tempfile.mkstemp(suffix=".json", prefix="buddyctl_index_")
            self.index_file = Path(temp_path)

            # Write index to file
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.file_tree, f, indent=2, ensure_ascii=False)

            # Count indexed items
            total_files = self._count_files(self.file_tree)
            print(f"✅ Indexed {total_files} files/directories")

            return True

        except Exception as e:
            print(f"❌ Failed to build file index: {e}")
            return False

    def _count_files(self, tree: Dict[str, Any]) -> int:
        """Count total files and directories in the tree."""
        count = 1  # Count current item
        if tree.get("type") == "folder" and "children" in tree:
            for child in tree["children"]:
                count += self._count_files(child)
        return count

    def get_suggestions(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get file suggestions based on query.

        Args:
            query: Search query (can include partial path)
            max_results: Maximum number of results to return

        Returns:
            List of file/directory suggestions
        """
        if not self.file_tree:
            return []

        query = query.strip()

        # Handle root query
        if not query or query == "/":
            return self._get_root_suggestions(max_results)

        # Handle directory navigation
        if query.endswith("/"):
            return self._get_directory_contents(query[:-1], max_results)

        # Handle path-based search
        if "/" in query:
            return self._get_path_suggestions(query, max_results)

        # Handle simple name search
        return self._get_name_suggestions(query, max_results)

    def _get_root_suggestions(self, max_results: int) -> List[Dict[str, Any]]:
        """Get suggestions for root directory."""
        if not self.file_tree or "children" not in self.file_tree:
            return []

        suggestions = []

        # Add directories first, then files
        children = self.file_tree["children"]
        dirs = [c for c in children if c.get("type") == "folder"]
        files = [c for c in children if c.get("type") == "file"]

        for item in (dirs + files)[:max_results]:
            suggestions.append(
                {
                    "name": item["name"],
                    "type": item["type"],
                    "path": item["path"],
                    "display": item["name"] + ("/" if item["type"] == "folder" else ""),
                }
            )

        return suggestions

    def _get_directory_contents(self, dir_path: str, max_results: int) -> List[Dict[str, Any]]:
        """Get contents of a specific directory."""
        target_dir = self._find_directory(dir_path)
        if not target_dir or "children" not in target_dir:
            return []

        suggestions = []
        children = target_dir["children"]

        # Sort: directories first, then files
        dirs = [c for c in children if c.get("type") == "folder"]
        files = [c for c in children if c.get("type") == "file"]

        for item in (dirs + files)[:max_results]:
            full_path = f"{dir_path}/{item['name']}"
            suggestions.append(
                {
                    "name": item["name"],
                    "type": item["type"],
                    "path": item["path"],
                    "display": full_path + ("/" if item["type"] == "folder" else ""),
                }
            )

        return suggestions

    def _get_path_suggestions(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Get suggestions for path-based queries."""
        parts = query.split("/")
        dir_parts = parts[:-1]
        name_part = parts[-1].lower()

        # Find the target directory
        dir_path = "/".join(dir_parts) if dir_parts else ""
        target_dir = self._find_directory(dir_path) if dir_path else self.file_tree

        if not target_dir or "children" not in target_dir:
            return []

        # Filter children by name prefix
        suggestions = []
        children = target_dir["children"]

        # Sort: directories first, then files
        dirs = [
            c
            for c in children
            if c.get("type") == "folder" and c["name"].lower().startswith(name_part)
        ]
        files = [
            c
            for c in children
            if c.get("type") == "file" and c["name"].lower().startswith(name_part)
        ]

        base_path = "/".join(dir_parts) if dir_parts else ""

        for item in (dirs + files)[:max_results]:
            full_path = f"{base_path}/{item['name']}" if base_path else item["name"]
            suggestions.append(
                {
                    "name": item["name"],
                    "type": item["type"],
                    "path": item["path"],
                    "display": full_path + ("/" if item["type"] == "folder" else ""),
                }
            )

        return suggestions

    def _get_name_suggestions(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Get suggestions based on file/directory name."""
        query_lower = query.lower()
        suggestions = []

        def search_recursive(node: Dict[str, Any], current_path: str = ""):
            if len(suggestions) >= max_results:
                return

            # Check if current item matches
            if node["name"].lower().startswith(query_lower):
                display_path = f"{current_path}/{node['name']}" if current_path else node["name"]
                suggestions.append(
                    {
                        "name": node["name"],
                        "type": node["type"],
                        "path": node["path"],
                        "display": display_path + ("/" if node["type"] == "folder" else ""),
                    }
                )

            # Search children
            if node.get("type") == "folder" and "children" in node:
                child_path = f"{current_path}/{node['name']}" if current_path else node["name"]
                for child in node["children"]:
                    search_recursive(child, child_path)

        if self.file_tree:
            # Search in root children first
            if "children" in self.file_tree:
                for child in self.file_tree["children"]:
                    search_recursive(child)

        # Sort: directories first, then files
        dirs = [s for s in suggestions if s["type"] == "folder"]
        files = [s for s in suggestions if s["type"] == "file"]

        return (dirs + files)[:max_results]

    def _find_directory(self, path: str) -> Optional[Dict[str, Any]]:
        """Find a directory node by path."""
        if not path or not self.file_tree:
            return self.file_tree

        parts = [p for p in path.split("/") if p]
        current = self.file_tree

        for part in parts:
            if not current or "children" not in current:
                return None

            # Find child with matching name
            found = False
            for child in current["children"]:
                if child["name"] == part and child["type"] == "folder":
                    current = child
                    found = True
                    break

            if not found:
                return None

        return current

    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in the index."""
        full_path = self.root_path / file_path
        return full_path.exists() and full_path.is_file()

    def get_file_content(self, file_path: str, max_size: int = 1024 * 1024) -> Optional[str]:
        """Get content of a file if it exists and is not too large.

        Args:
            file_path: Relative path to the file
            max_size: Maximum file size to read (default 1MB)

        Returns:
            File content or None if file doesn't exist/too large
        """
        full_path = self.root_path / file_path

        try:
            if not full_path.exists() or not full_path.is_file():
                return None

            # Check file size
            if full_path.stat().st_size > max_size:
                return None

            # Read file content
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        except (OSError, PermissionError, UnicodeDecodeError):
            return None

    def add_files_to_index(self, file_paths: List[str]) -> bool:
        """
        Add new files to existing index incrementally.

        This is a performance optimization to avoid full reindex on small changes.

        Args:
            file_paths: List of file paths (relative or absolute) to add

        Returns:
            True if incremental update succeeded, False if full reindex needed
        """
        if not self.file_tree:
            return False

        try:
            for file_path_str in file_paths:
                file_path = Path(file_path_str)

                # Convert to absolute path if needed
                if not file_path.is_absolute():
                    abs_path = (self.root_path / file_path).resolve()
                else:
                    abs_path = file_path.resolve()

                # Skip if should be ignored
                if self._should_ignore_file(abs_path):
                    continue

                # Add to tree structure
                self._add_file_to_tree(abs_path, self.root_path)

            return True

        except Exception as e:
            print(f"⚠️ Incremental update failed: {e}")
            return False

    def _add_file_to_tree(self, file_path: Path, root_path: Path) -> None:
        """
        Add a single file to the existing tree structure.

        Navigates the tree to find the correct parent directory and inserts the file.
        Creates intermediate directory nodes if needed.
        """
        rel_path = file_path.relative_to(root_path)
        parts = rel_path.parts

        # Navigate to parent directory in tree
        current = self.file_tree
        for part in parts[:-1]:  # All except file name
            # Find or create directory node
            found = False
            if "children" in current:
                for child in current["children"]:
                    if child["name"] == part and child["type"] == "folder":
                        current = child
                        found = True
                        break

            if not found:
                # Create missing directory node
                new_dir = {
                    "name": part,
                    "type": "folder",
                    "path": str(Path(current.get("path", "")) / part),
                    "children": []
                }
                if "children" not in current:
                    current["children"] = []
                current["children"].append(new_dir)
                current = new_dir

        # Add file to parent directory
        file_node = {
            "name": parts[-1],
            "type": "file",
            "path": str(rel_path)
        }

        if "children" not in current:
            current["children"] = []

        # Check if file already exists in index
        existing = [c for c in current["children"] if c["name"] == parts[-1]]
        if not existing:
            current["children"].append(file_node)
            # Keep children sorted (dirs first, then files)
            current["children"].sort(key=lambda x: (x["type"] != "folder", x["name"]))

    def cleanup(self):
        """Clean up temporary files."""
        if self.index_file and self.index_file.exists():
            try:
                self.index_file.unlink()
            except OSError:
                pass
