"""Abstract interface for content providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Entry:
    """Represents a directory entry (file or folder)."""

    name: str
    is_dir: bool


class ContentProvider(ABC):
    """Abstract interface for accessing gopher content."""

    @abstractmethod
    def list_directory(self, path: str) -> list[Entry]:
        """List entries in a directory."""
        pass

    @abstractmethod
    def read_file(self, path: str) -> str:
        """Read the contents of a file."""
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if a path exists."""
        pass

    @abstractmethod
    def is_directory(self, path: str) -> bool:
        """Check if a path is a directory."""
        pass
