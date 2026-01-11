"""Tests for the MenuRenderer module."""

import pytest
from meshtastic_gopher.core.menu_renderer import MenuRenderer
from meshtastic_gopher.interfaces import Entry


class TestMenuRenderer:
    """Tests for MenuRenderer."""

    @pytest.fixture
    def renderer(self):
        """Create a MenuRenderer instance."""
        return MenuRenderer()

    @pytest.fixture
    def sample_entries(self):
        """Sample directory entries."""
        return [
            Entry(name="documents", is_dir=True),
            Entry(name="images", is_dir=True),
            Entry(name="readme.txt", is_dir=False),
            Entry(name="config.yaml", is_dir=False),
        ]

    def test_empty_directory(self, renderer):
        """Empty directory renders appropriate message."""
        result = renderer.render([])
        assert "empty" in result.lower() or len(result) == 0

    def test_single_file(self, renderer):
        """Single file renders with number 1."""
        entries = [Entry(name="readme.txt", is_dir=False)]
        result = renderer.render(entries)
        assert "1." in result
        assert "readme.txt" in result

    def test_single_directory(self, renderer):
        """Single directory renders with trailing slash."""
        entries = [Entry(name="docs", is_dir=True)]
        result = renderer.render(entries)
        assert "1." in result
        assert "docs/" in result

    def test_multiple_entries_numbered(self, renderer, sample_entries):
        """Multiple entries are numbered sequentially."""
        result = renderer.render(sample_entries)
        assert "1." in result
        assert "2." in result
        assert "3." in result
        assert "4." in result

    def test_directories_have_trailing_slash(self, renderer, sample_entries):
        """Directories are marked with trailing slash."""
        result = renderer.render(sample_entries)
        assert "documents/" in result
        assert "images/" in result

    def test_files_no_trailing_slash(self, renderer, sample_entries):
        """Files do not have trailing slash."""
        result = renderer.render(sample_entries)
        lines = result.strip().split("\n")
        # Find lines with files
        file_lines = [l for l in lines if "readme.txt" in l or "config.yaml" in l]
        for line in file_lines:
            # Should not end with slash (after the filename)
            assert not line.rstrip().endswith("txt/")
            assert not line.rstrip().endswith("yaml/")

    def test_entries_on_separate_lines(self, renderer, sample_entries):
        """Each entry is on a separate line."""
        result = renderer.render(sample_entries)
        lines = [l for l in result.strip().split("\n") if l.strip()]
        assert len(lines) == 4

    def test_directories_sorted_first(self, renderer):
        """Directories appear before files."""
        entries = [
            Entry(name="zebra.txt", is_dir=False),
            Entry(name="alpha", is_dir=True),
            Entry(name="aardvark.txt", is_dir=False),
            Entry(name="beta", is_dir=True),
        ]
        result = renderer.render(entries)
        lines = [l for l in result.strip().split("\n") if l.strip()]
        # First two should be directories
        assert "/" in lines[0]  # directory
        assert "/" in lines[1]  # directory
        # Last two should be files
        assert ".txt" in lines[2]
        assert ".txt" in lines[3]

    def test_alphabetical_within_categories(self, renderer):
        """Items are sorted alphabetically within dirs/files."""
        entries = [
            Entry(name="zebra.txt", is_dir=False),
            Entry(name="alpha", is_dir=True),
            Entry(name="aardvark.txt", is_dir=False),
            Entry(name="beta", is_dir=True),
        ]
        result = renderer.render(entries)
        lines = [l for l in result.strip().split("\n") if l.strip()]
        # Directories first, alphabetically
        assert "alpha/" in lines[0]
        assert "beta/" in lines[1]
        # Files next, alphabetically
        assert "aardvark.txt" in lines[2]
        assert "zebra.txt" in lines[3]

    def test_includes_navigation_hint(self, renderer, sample_entries):
        """Rendered output includes navigation hints."""
        result = renderer.render(sample_entries, include_hints=True)
        # Should mention how to navigate
        assert "b" in result.lower() or "back" in result.lower() or "select" in result.lower()

    def test_no_hints_by_default(self, renderer, sample_entries):
        """Navigation hints not included by default."""
        result = renderer.render(sample_entries)
        # Just entries, no extra hints
        lines = [l for l in result.strip().split("\n") if l.strip()]
        # Should only have 4 lines (the entries)
        assert len(lines) == 4

    def test_header_with_path(self, renderer, sample_entries):
        """Can include current path as header."""
        result = renderer.render(sample_entries, current_path="/documents")
        assert "/documents" in result or "documents" in result

    def test_special_characters_in_names(self, renderer):
        """Handles special characters in file/dir names."""
        entries = [
            Entry(name="my file (1).txt", is_dir=False),
            Entry(name="folder-name_v2", is_dir=True),
        ]
        result = renderer.render(entries)
        assert "my file (1).txt" in result
        assert "folder-name_v2/" in result

    def test_long_filename_not_truncated_by_default(self, renderer):
        """Long filenames are not truncated by default."""
        long_name = "this_is_a_very_long_filename_that_might_be_problematic.txt"
        entries = [Entry(name=long_name, is_dir=False)]
        result = renderer.render(entries)
        assert long_name in result

    def test_render_with_max_entries(self, renderer):
        """Can limit the number of entries shown."""
        entries = [Entry(name=f"file{i}.txt", is_dir=False) for i in range(20)]
        result = renderer.render(entries, max_entries=5)
        lines = [l for l in result.strip().split("\n") if l.strip() and l[0].isdigit()]
        assert len(lines) <= 5
        # Should indicate more entries exist
        assert "more" in result.lower() or "..." in result
