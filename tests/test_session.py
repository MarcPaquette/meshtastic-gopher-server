"""Tests for the Session module."""

from meshtastic_gopher.core.session import Session, PaginationState
from meshtastic_gopher.interfaces import Entry


class TestPaginationState:
    """Tests for PaginationState."""

    def test_default_values(self):
        """PaginationState has sensible defaults."""
        state = PaginationState()
        assert len(state.chunks) == 0
        assert state.current_page == 0

    def test_with_chunks(self):
        """PaginationState can be created with chunks."""
        chunks = ("Page 1", "Page 2", "Page 3")
        state = PaginationState(chunks=chunks, current_page=0)
        assert state.chunks == chunks
        assert state.current_page == 0

    def test_has_next_page(self):
        """has_next returns True when more pages exist."""
        state = PaginationState(chunks=("a", "b", "c"), current_page=0)
        assert state.has_next() is True

    def test_has_next_page_false_at_end(self):
        """has_next returns False on last page."""
        state = PaginationState(chunks=("a", "b", "c"), current_page=2)
        assert state.has_next() is False

    def test_has_next_empty_chunks(self):
        """has_next returns False for empty chunks."""
        state = PaginationState(chunks=(), current_page=0)
        assert state.has_next() is False

    def test_current_chunk(self):
        """current_chunk returns the chunk at current_page."""
        state = PaginationState(chunks=("a", "b", "c"), current_page=1)
        assert state.current_chunk() == "b"

    def test_current_chunk_empty(self):
        """current_chunk returns None for empty chunks."""
        state = PaginationState(chunks=(), current_page=0)
        assert state.current_chunk() is None

    def test_advance(self):
        """advance increments current_page."""
        state = PaginationState(chunks=("a", "b", "c"), current_page=0)
        new_state = state.advance()
        assert new_state.current_page == 1
        assert state.current_page == 0  # Original unchanged

    def test_advance_at_end(self):
        """advance at end stays at last page."""
        state = PaginationState(chunks=("a", "b"), current_page=1)
        new_state = state.advance()
        assert new_state.current_page == 1

    def test_total_pages(self):
        """total_pages returns number of chunks."""
        state = PaginationState(chunks=("a", "b", "c"))
        assert state.total_pages() == 3


class TestSession:
    """Tests for Session."""

    def test_default_values(self):
        """Session has sensible defaults."""
        session = Session()
        assert session.current_path == "/"
        assert session.pagination is None
        assert len(session.last_listing) == 0

    def test_with_custom_path(self):
        """Session can be created with custom path."""
        session = Session(current_path="/documents")
        assert session.current_path == "/documents"

    def test_navigate_to(self):
        """navigate_to creates new session with updated path."""
        session = Session(current_path="/")
        new_session = session.navigate_to("/documents")
        assert new_session.current_path == "/documents"
        assert session.current_path == "/"  # Original unchanged

    def test_navigate_to_clears_pagination(self):
        """navigate_to clears pagination state."""
        pagination = PaginationState(chunks=("a", "b"), current_page=0)
        session = Session(current_path="/", pagination=pagination)
        new_session = session.navigate_to("/documents")
        assert new_session.pagination is None

    def test_navigate_back(self):
        """navigate_back goes to parent directory."""
        session = Session(current_path="/documents/subfolder")
        new_session = session.navigate_back()
        assert new_session.current_path == "/documents"

    def test_navigate_back_from_root(self):
        """navigate_back from root stays at root."""
        session = Session(current_path="/")
        new_session = session.navigate_back()
        assert new_session.current_path == "/"

    def test_navigate_back_to_root(self):
        """navigate_back from first level goes to root."""
        session = Session(current_path="/documents")
        new_session = session.navigate_back()
        assert new_session.current_path == "/"

    def test_navigate_home(self):
        """navigate_home returns to root."""
        session = Session(current_path="/deep/nested/path")
        new_session = session.navigate_home()
        assert new_session.current_path == "/"

    def test_set_listing(self):
        """set_listing stores the current directory listing."""
        entries = [Entry(name="test.txt", is_dir=False)]
        session = Session()
        new_session = session.set_listing(entries)
        assert list(new_session.last_listing) == entries
        assert len(session.last_listing) == 0  # Original unchanged

    def test_start_pagination(self):
        """start_pagination creates pagination state."""
        session = Session()
        chunks = ["Page 1", "Page 2"]
        new_session = session.start_pagination(chunks)
        assert new_session.pagination is not None
        assert list(new_session.pagination.chunks) == chunks
        assert new_session.pagination.current_page == 0

    def test_advance_pagination(self):
        """advance_pagination moves to next page."""
        pagination = PaginationState(chunks=("a", "b", "c"), current_page=0)
        session = Session(pagination=pagination)
        new_session = session.advance_pagination()
        assert new_session.pagination.current_page == 1

    def test_advance_pagination_when_none(self):
        """advance_pagination does nothing when no pagination."""
        session = Session()
        new_session = session.advance_pagination()
        assert new_session.pagination is None

    def test_clear_pagination(self):
        """clear_pagination removes pagination state."""
        pagination = PaginationState(chunks=("a",), current_page=0)
        session = Session(pagination=pagination)
        new_session = session.clear_pagination()
        assert new_session.pagination is None

    def test_has_pagination(self):
        """has_pagination returns True when paginating."""
        pagination = PaginationState(chunks=("a",), current_page=0)
        session = Session(pagination=pagination)
        assert session.has_pagination() is True

    def test_has_pagination_false(self):
        """has_pagination returns False when not paginating."""
        session = Session()
        assert session.has_pagination() is False

    def test_get_entry_at_index(self):
        """get_entry_at returns entry from last_listing."""
        entries = (
            Entry(name="first.txt", is_dir=False),
            Entry(name="second.txt", is_dir=False),
        )
        session = Session(last_listing=entries)
        assert session.get_entry_at(1) == entries[0]
        assert session.get_entry_at(2) == entries[1]

    def test_get_entry_at_invalid_index(self):
        """get_entry_at returns None for invalid index."""
        entries = (Entry(name="only.txt", is_dir=False),)
        session = Session(last_listing=entries)
        assert session.get_entry_at(0) is None  # 0 is invalid (1-indexed)
        assert session.get_entry_at(2) is None  # Out of range

    def test_resolve_path(self):
        """resolve_path joins current path with relative path."""
        session = Session(current_path="/documents")
        assert session.resolve_path("file.txt") == "/documents/file.txt"

    def test_resolve_path_from_root(self):
        """resolve_path works from root."""
        session = Session(current_path="/")
        assert session.resolve_path("file.txt") == "/file.txt"
