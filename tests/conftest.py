"""Pytest configuration and fixtures."""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def temp_content_dir():
    """Create a temporary directory with sample gopher content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create directory structure
        (root / "documents").mkdir()
        (root / "documents" / "subfolder").mkdir()

        # Create some files
        (root / "welcome.txt").write_text("Welcome to the Gopher server!")
        (root / "documents" / "readme.txt").write_text(
            "This is a readme file with some content that explains things."
        )
        (root / "documents" / "long_file.txt").write_text(
            "A" * 500  # Long content for pagination testing
        )
        (root / "documents" / "subfolder" / "nested.txt").write_text(
            "Nested file content"
        )

        yield root


@pytest.fixture
def sample_directory_entries():
    """Sample directory entries for testing."""
    from meshtastic_gopher.interfaces import Entry
    return [
        Entry(name="documents", is_dir=True),
        Entry(name="images", is_dir=True),
        Entry(name="readme.txt", is_dir=False),
        Entry(name="config.yaml", is_dir=False),
    ]
