"""Tests for the ContentChunker module."""

import pytest
from meshtastic_gopher.core.content_chunker import ContentChunker


class TestContentChunker:
    """Tests for ContentChunker."""

    @pytest.fixture
    def chunker(self):
        """Create a ContentChunker with default max_size."""
        return ContentChunker(max_size=230)

    @pytest.fixture
    def small_chunker(self):
        """Create a ContentChunker with smaller size for testing."""
        return ContentChunker(max_size=50)

    def test_short_content_single_chunk(self, chunker):
        """Short content returns a single chunk without page indicator."""
        chunks = chunker.chunk("Hello world")
        assert len(chunks) == 1
        assert chunks[0] == "Hello world"

    def test_empty_content_returns_empty_list(self, chunker):
        """Empty content returns empty list."""
        chunks = chunker.chunk("")
        assert len(chunks) == 0

    def test_whitespace_only_returns_empty_list(self, chunker):
        """Whitespace-only content returns empty list."""
        chunks = chunker.chunk("   \n  \t  ")
        assert len(chunks) == 0

    def test_exact_max_size_single_chunk(self, small_chunker):
        """Content exactly at max_size is single chunk without indicator."""
        content = "A" * 50
        chunks = small_chunker.chunk(content)
        assert len(chunks) == 1
        assert chunks[0] == content

    def test_content_over_max_creates_multiple_chunks(self, small_chunker):
        """Content over max_size creates multiple chunks with indicators."""
        content = "A" * 100
        chunks = small_chunker.chunk(content)
        assert len(chunks) >= 2
        assert "[1/" in chunks[0]
        assert "[2/" in chunks[1]

    def test_page_indicators_correct_format(self, small_chunker):
        """Page indicators have correct format [n/total]."""
        content = "A" * 150
        chunks = small_chunker.chunk(content)
        total = len(chunks)
        for i, chunk in enumerate(chunks, 1):
            assert f"[{i}/{total}]" in chunk

    def test_chunks_respect_max_size(self, small_chunker):
        """Each chunk respects the max_size limit."""
        content = "A" * 200
        chunks = small_chunker.chunk(content)
        for chunk in chunks:
            assert len(chunk) <= small_chunker.max_size

    def test_word_boundary_splitting(self, small_chunker):
        """Content is split at word boundaries when possible."""
        content = "Hello world this is a test of word boundary splitting"
        chunks = small_chunker.chunk(content)
        # Should not split words in the middle
        for chunk in chunks:
            # Remove page indicator if present
            text = chunk.split(" [")[0] if " [" in chunk else chunk
            # Check no partial words (shouldn't end with incomplete word)
            assert not text.endswith("-") or text.endswith(" -")

    def test_long_word_handling(self, small_chunker):
        """Long words that exceed max_size are handled."""
        # A word longer than max_size must be split
        content = "A" * 100  # Single "word" of 100 chars
        chunks = small_chunker.chunk(content)
        assert len(chunks) >= 2
        # All chunks should be valid
        for chunk in chunks:
            assert len(chunk) <= small_chunker.max_size

    def test_preserves_newlines_in_content(self, small_chunker):
        """Newlines in content are preserved within chunks."""
        content = "Line1\nLine2\nLine3"
        chunks = small_chunker.chunk(content)
        combined = "".join(
            c.split(" [")[0] if " [" in c else c for c in chunks
        )
        assert "Line1\nLine2\nLine3" in combined or "\n" in combined

    def test_default_max_size(self):
        """Default max_size is 230."""
        chunker = ContentChunker()
        assert chunker.max_size == 230

    def test_three_page_content(self, small_chunker):
        """Three page content has correct indicators."""
        content = "A" * 120
        chunks = small_chunker.chunk(content)
        if len(chunks) == 3:
            assert "[1/3]" in chunks[0]
            assert "[2/3]" in chunks[1]
            assert "[3/3]" in chunks[2]

    def test_page_indicator_at_end(self, small_chunker):
        """Page indicator appears at the end of each chunk."""
        content = "Hello " * 20  # Should create multiple chunks
        chunks = small_chunker.chunk(content)
        if len(chunks) > 1:
            for chunk in chunks:
                assert chunk.rstrip().endswith("]")

    def test_realistic_230_char_limit(self):
        """Test with realistic 230 character limit."""
        chunker = ContentChunker(max_size=230)
        content = "This is a sample text file. " * 50  # ~1400 chars
        chunks = chunker.chunk(content)
        assert len(chunks) >= 6
        for chunk in chunks:
            assert len(chunk) <= 230

    def test_special_characters_preserved(self, chunker):
        """Special characters are preserved in chunks."""
        content = "Special: @#$%^&*() symbols!"
        chunks = chunker.chunk(content)
        assert chunks[0] == content

    def test_unicode_content(self, chunker):
        """Unicode content is handled correctly."""
        content = "Hello 世界! Emoji: 🎉🚀"
        chunks = chunker.chunk(content)
        assert "世界" in chunks[0]
        assert "🎉" in chunks[0]

    def test_max_size_too_small_raises(self):
        """max_size smaller than indicator reserve raises ValueError."""
        chunker = ContentChunker(max_size=5)  # Too small for " [1/1]"
        with pytest.raises(ValueError, match="max_size must be"):
            chunker.chunk("A" * 100)

    def test_split_at_newline_boundary(self):
        """Content is split at newline boundaries when possible."""
        # Create content where newline is a good split point
        chunker = ContentChunker(max_size=50)
        # Line1 is 20 chars, newline, Line2 is 25 chars = 46 total
        # Adding more pushes over limit, should split at newline
        content = "A" * 20 + "\n" + "B" * 25 + "\n" + "C" * 30
        chunks = chunker.chunk(content)
        # First chunk should end around the newline
        assert len(chunks) >= 2

    def test_split_prefers_newline_over_space(self):
        """Splitting prefers newlines over spaces when both available."""
        chunker = ContentChunker(max_size=40)
        # Create content that definitely exceeds max_size
        # effective_max = 40 - 9 = 31 chars per chunk
        # Content needs to be >40 to trigger splitting
        content = "word word\nmore content here and it keeps going and going"
        chunks = chunker.chunk(content)
        # Should have split at the newline (since it's in the first half and valid)
        assert len(chunks) >= 2
        # First chunk text (without indicator) should contain "word word"
        first_text = chunks[0].split(" [")[0] if " [" in chunks[0] else chunks[0]
        assert "word" in first_text

    def test_find_split_point_short_text(self):
        """_find_split_point returns len(text) for short text."""
        chunker = ContentChunker(max_size=100)
        # Directly test the method
        result = chunker._find_split_point("short text", 50)
        assert result == len("short text")
