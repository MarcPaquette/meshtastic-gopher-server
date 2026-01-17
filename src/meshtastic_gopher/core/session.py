"""Session management for per-node state."""

from dataclasses import dataclass, replace
from ..interfaces import Entry


@dataclass(frozen=True)
class PaginationState:
    """Tracks pagination state for multi-page content."""

    chunks: tuple[str, ...] = ()
    current_page: int = 0

    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.current_page < len(self.chunks) - 1

    def current_chunk(self) -> str | None:
        """Get the current chunk, or None if no chunks."""
        if not self.chunks or self.current_page >= len(self.chunks):
            return None
        return self.chunks[self.current_page]

    def advance(self) -> "PaginationState":
        """Return new state advanced to next page."""
        if not self.has_next():
            return self
        return replace(self, current_page=self.current_page + 1)

    def total_pages(self) -> int:
        """Get total number of pages."""
        return len(self.chunks)


@dataclass(frozen=True)
class Session:
    """Per-node session state (immutable)."""

    current_path: str = "/"
    pagination: PaginationState | None = None
    last_listing: tuple[Entry, ...] = ()

    def navigate_to(self, path: str) -> "Session":
        """Navigate to a new path, clearing pagination."""
        return replace(self, current_path=path, pagination=None)

    def navigate_back(self) -> "Session":
        """Navigate to parent directory."""
        if self.current_path == "/":
            return self

        # Remove trailing slash if present and split
        path = self.current_path.rstrip("/")
        parts = path.rsplit("/", 1)

        if len(parts) == 1 or parts[0] == "":
            new_path = "/"
        else:
            new_path = parts[0]

        return replace(self, current_path=new_path, pagination=None, last_listing=())

    def navigate_home(self) -> "Session":
        """Navigate to root directory."""
        return Session()

    def set_listing(self, entries: list[Entry]) -> "Session":
        """Store the current directory listing."""
        return replace(self, last_listing=tuple(entries))

    def start_pagination(self, chunks: list[str]) -> "Session":
        """Start paginating through content."""
        return replace(self, pagination=PaginationState(chunks=tuple(chunks)))

    def advance_pagination(self) -> "Session":
        """Advance to next page."""
        if self.pagination is None:
            return self
        return replace(self, pagination=self.pagination.advance())

    def clear_pagination(self) -> "Session":
        """Clear pagination state."""
        return replace(self, pagination=None)

    def has_pagination(self) -> bool:
        """Check if currently paginating."""
        return self.pagination is not None

    def get_entry_at(self, index: int) -> Entry | None:
        """
        Get entry at 1-based index from last_listing.

        Returns None if index is invalid.
        """
        if index < 1 or index > len(self.last_listing):
            return None
        return self.last_listing[index - 1]

    def resolve_path(self, name: str) -> str:
        """Resolve a relative name to full path."""
        if self.current_path == "/":
            return f"/{name}"
        return f"{self.current_path}/{name}"
