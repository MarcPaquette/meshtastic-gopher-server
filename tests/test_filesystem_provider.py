"""Tests for the FilesystemProvider module."""

import pytest
from pathlib import Path
from meshtastic_gopher.providers.filesystem_provider import FilesystemProvider
from meshtastic_gopher.interfaces import Entry


class TestFilesystemProvider:
    """Tests for FilesystemProvider."""

    def test_init_with_string_path(self, temp_content_dir):
        """Can initialize with string path."""
        provider = FilesystemProvider(str(temp_content_dir))
        assert provider.root == temp_content_dir

    def test_init_with_path_object(self, temp_content_dir):
        """Can initialize with Path object."""
        provider = FilesystemProvider(temp_content_dir)
        assert provider.root == temp_content_dir

    def test_exists_file(self, temp_content_dir):
        """exists returns True for existing file."""
        provider = FilesystemProvider(temp_content_dir)
        assert provider.exists("/welcome.txt") is True

    def test_exists_directory(self, temp_content_dir):
        """exists returns True for existing directory."""
        provider = FilesystemProvider(temp_content_dir)
        assert provider.exists("/documents") is True

    def test_exists_nonexistent(self, temp_content_dir):
        """exists returns False for nonexistent path."""
        provider = FilesystemProvider(temp_content_dir)
        assert provider.exists("/nonexistent.txt") is False

    def test_exists_root(self, temp_content_dir):
        """exists returns True for root."""
        provider = FilesystemProvider(temp_content_dir)
        assert provider.exists("/") is True

    def test_is_directory_true(self, temp_content_dir):
        """is_directory returns True for directories."""
        provider = FilesystemProvider(temp_content_dir)
        assert provider.is_directory("/documents") is True

    def test_is_directory_false_for_file(self, temp_content_dir):
        """is_directory returns False for files."""
        provider = FilesystemProvider(temp_content_dir)
        assert provider.is_directory("/welcome.txt") is False

    def test_is_directory_root(self, temp_content_dir):
        """is_directory returns True for root."""
        provider = FilesystemProvider(temp_content_dir)
        assert provider.is_directory("/") is True

    def test_is_directory_nonexistent(self, temp_content_dir):
        """is_directory returns False for nonexistent path."""
        provider = FilesystemProvider(temp_content_dir)
        assert provider.is_directory("/nonexistent") is False

    def test_list_directory_root(self, temp_content_dir):
        """list_directory returns entries for root."""
        provider = FilesystemProvider(temp_content_dir)
        entries = provider.list_directory("/")
        names = [e.name for e in entries]
        assert "documents" in names
        assert "welcome.txt" in names

    def test_list_directory_subdirectory(self, temp_content_dir):
        """list_directory works for subdirectories."""
        provider = FilesystemProvider(temp_content_dir)
        entries = provider.list_directory("/documents")
        names = [e.name for e in entries]
        assert "readme.txt" in names
        assert "subfolder" in names

    def test_list_directory_entries_have_correct_is_dir(self, temp_content_dir):
        """Entries have correct is_dir flag."""
        provider = FilesystemProvider(temp_content_dir)
        entries = provider.list_directory("/")
        entries_dict = {e.name: e for e in entries}
        assert entries_dict["documents"].is_dir is True
        assert entries_dict["welcome.txt"].is_dir is False

    def test_list_directory_empty(self, temp_content_dir):
        """list_directory returns empty list for empty directory."""
        # Create an empty directory
        empty_dir = temp_content_dir / "empty"
        empty_dir.mkdir()
        provider = FilesystemProvider(temp_content_dir)
        entries = provider.list_directory("/empty")
        assert entries == []

    def test_list_directory_nonexistent_raises(self, temp_content_dir):
        """list_directory raises for nonexistent directory."""
        provider = FilesystemProvider(temp_content_dir)
        with pytest.raises(FileNotFoundError):
            provider.list_directory("/nonexistent")

    def test_list_directory_file_raises(self, temp_content_dir):
        """list_directory raises for file path."""
        provider = FilesystemProvider(temp_content_dir)
        with pytest.raises(NotADirectoryError):
            provider.list_directory("/welcome.txt")

    def test_read_file(self, temp_content_dir):
        """read_file returns file content."""
        provider = FilesystemProvider(temp_content_dir)
        content = provider.read_file("/welcome.txt")
        assert content == "Welcome to the Gopher server!"

    def test_read_file_nested(self, temp_content_dir):
        """read_file works for nested files."""
        provider = FilesystemProvider(temp_content_dir)
        content = provider.read_file("/documents/subfolder/nested.txt")
        assert content == "Nested file content"

    def test_read_file_nonexistent_raises(self, temp_content_dir):
        """read_file raises for nonexistent file."""
        provider = FilesystemProvider(temp_content_dir)
        with pytest.raises(FileNotFoundError):
            provider.read_file("/nonexistent.txt")

    def test_read_file_directory_raises(self, temp_content_dir):
        """read_file raises for directory path."""
        provider = FilesystemProvider(temp_content_dir)
        with pytest.raises(IsADirectoryError):
            provider.read_file("/documents")

    def test_path_traversal_blocked(self, temp_content_dir):
        """Path traversal attempts are blocked."""
        provider = FilesystemProvider(temp_content_dir)
        # Try to escape root with ..
        with pytest.raises((FileNotFoundError, ValueError)):
            provider.read_file("/../../../etc/passwd")

    def test_hidden_files_excluded(self, temp_content_dir):
        """Hidden files (starting with .) are excluded."""
        # Create a hidden file
        (temp_content_dir / ".hidden").write_text("secret")
        provider = FilesystemProvider(temp_content_dir)
        entries = provider.list_directory("/")
        names = [e.name for e in entries]
        assert ".hidden" not in names

    def test_list_directory_returns_entry_objects(self, temp_content_dir):
        """list_directory returns Entry objects."""
        provider = FilesystemProvider(temp_content_dir)
        entries = provider.list_directory("/")
        for entry in entries:
            assert isinstance(entry, Entry)
            assert isinstance(entry.name, str)
            assert isinstance(entry.is_dir, bool)
