"""Filesystem-based content provider."""

from pathlib import Path
from ..interfaces import ContentProvider, Entry


class FilesystemProvider(ContentProvider):
    """Content provider that reads from the local filesystem.

    Serves files and directories from a root directory, providing
    a safe, sandboxed view of the filesystem.
    """

    def __init__(self, root_path: str | Path):
        """
        Initialize with root directory path.

        Args:
            root_path: The root directory to serve content from.
        """
        self.root = Path(root_path).resolve()
        if not self.root.is_dir():
            raise ValueError(f"Root path must be a directory: {root_path}")

    def _resolve_path(self, path: str) -> Path:
        """
        Resolve a virtual path to a real filesystem path.

        Prevents path traversal attacks by ensuring the resolved
        path is within the root directory.

        Args:
            path: Virtual path (e.g., "/documents/file.txt")

        Returns:
            Resolved Path object within root.

        Raises:
            ValueError: If path escapes root directory.
        """
        # Normalize path - remove leading slash for joining
        clean_path = path.lstrip("/")

        if not clean_path:
            return self.root

        # Resolve and check it's within root
        resolved = (self.root / clean_path).resolve()

        # Security check: ensure path is within root
        try:
            resolved.relative_to(self.root)
        except ValueError:
            raise ValueError(f"Path escapes root directory: {path}")

        return resolved

    def list_directory(self, path: str) -> list[Entry]:
        """
        List entries in a directory.

        Args:
            path: Virtual path to the directory.

        Returns:
            List of Entry objects for directory contents.

        Raises:
            FileNotFoundError: If directory doesn't exist.
            NotADirectoryError: If path is not a directory.
        """
        resolved = self._resolve_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        if not resolved.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        entries = []
        for item in resolved.iterdir():
            # Skip hidden files
            if item.name.startswith("."):
                continue

            entries.append(Entry(name=item.name, is_dir=item.is_dir()))

        return entries

    def read_file(self, path: str) -> str:
        """
        Read the contents of a file.

        Args:
            path: Virtual path to the file.

        Returns:
            File contents as string.

        Raises:
            FileNotFoundError: If file doesn't exist.
            IsADirectoryError: If path is a directory.
        """
        resolved = self._resolve_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if resolved.is_dir():
            raise IsADirectoryError(f"Is a directory: {path}")

        return resolved.read_text()

    def exists(self, path: str) -> bool:
        """
        Check if a path exists.

        Args:
            path: Virtual path to check.

        Returns:
            True if path exists, False otherwise.
        """
        try:
            resolved = self._resolve_path(path)
            return resolved.exists()
        except ValueError:
            return False

    def is_directory(self, path: str) -> bool:
        """
        Check if a path is a directory.

        Args:
            path: Virtual path to check.

        Returns:
            True if path is a directory, False otherwise.
        """
        try:
            resolved = self._resolve_path(path)
            return resolved.is_dir()
        except ValueError:
            return False
