"""Content chunker for splitting messages into 230-char chunks."""

from dataclasses import dataclass


@dataclass
class ContentChunker:
    """Splits content into message-sized chunks with page indicators."""

    max_size: int = 230

    def chunk(self, content: str) -> list[str]:
        """
        Split content into chunks that fit within max_size.

        For single-chunk content, no page indicator is added.
        For multi-chunk content, each chunk ends with [n/total].

        Args:
            content: The content to split.

        Returns:
            List of chunks, each <= max_size characters.
        """
        content = content.strip()
        if not content:
            return []

        # First, check if content fits in a single chunk
        if len(content) <= self.max_size:
            return [content]

        # Need multiple chunks - calculate overhead for page indicators
        # Format: " [n/m]" where n and m can be 1-2 digits
        # Worst case: " [99/99]" = 9 characters
        raw_chunks = self._split_content(content)

        # Now add page indicators
        total = len(raw_chunks)
        result = []
        for i, chunk in enumerate(raw_chunks, 1):
            indicator = f" [{i}/{total}]"
            result.append(f"{chunk}{indicator}")

        return result

    def _split_content(self, content: str) -> list[str]:
        """
        Split content into raw chunks without page indicators.

        Tries to split at word boundaries when possible.
        """
        # Reserve space for longest possible indicator: " [99/99]" = 9 chars
        indicator_reserve = 9
        effective_max = self.max_size - indicator_reserve

        if effective_max <= 0:
            raise ValueError(f"max_size must be > {indicator_reserve}")

        chunks = []
        remaining = content

        while remaining:
            if len(remaining) <= effective_max:
                chunks.append(remaining)
                break

            # Find a good split point
            split_point = self._find_split_point(remaining, effective_max)
            chunk = remaining[:split_point].rstrip()
            chunks.append(chunk)
            remaining = remaining[split_point:].lstrip()

        return chunks

    def _find_split_point(self, text: str, max_len: int) -> int:
        """
        Find the best point to split text at or before max_len.

        Prefers splitting at word boundaries (spaces, newlines).
        Falls back to hard split if no good boundary found.
        """
        if len(text) <= max_len:
            return len(text)

        # Look for last space or newline within max_len
        search_text = text[:max_len]

        # Try newline first (natural break)
        last_newline = search_text.rfind("\n")
        if last_newline > max_len // 2:
            return last_newline + 1

        # Try space
        last_space = search_text.rfind(" ")
        if last_space > max_len // 2:
            return last_space + 1

        # No good break point - hard split at max_len
        return max_len
