"""Menu renderer for directory listings."""

from ..interfaces import Entry


class MenuRenderer:
    """Renders directory listings as numbered menus."""

    def render(
        self,
        entries: list[Entry],
        current_path: str | None = None,
        include_hints: bool = False,
        max_entries: int | None = None,
    ) -> str:
        """
        Render a list of entries as a numbered menu.

        Directories are listed first (with trailing /), then files.
        Both are sorted alphabetically within their category.

        Args:
            entries: List of Entry objects to render.
            current_path: Optional path to show as header.
            include_hints: Whether to include navigation hints.
            max_entries: Maximum entries to show (None for all).

        Returns:
            Formatted menu string.
        """
        if not entries:
            return "(empty)"

        # Sort: directories first, then files, alphabetically within each
        dirs = sorted([e for e in entries if e.is_dir], key=lambda e: e.name.lower())
        files = sorted([e for e in entries if not e.is_dir], key=lambda e: e.name.lower())
        sorted_entries = dirs + files

        # Apply max_entries limit
        truncated = False
        if max_entries is not None and len(sorted_entries) > max_entries:
            sorted_entries = sorted_entries[:max_entries]
            truncated = True

        lines = []

        # Add header if path provided
        if current_path:
            lines.append(f"[{current_path}]")

        # Render each entry with number
        for i, entry in enumerate(sorted_entries, 1):
            name = f"{entry.name}/" if entry.is_dir else entry.name
            lines.append(f"{i}. {name}")

        # Add truncation indicator
        if truncated:
            lines.append("(more...)")

        # Add navigation hints
        if include_hints:
            lines.append("")
            lines.append("b=back h=home ?=help")

        return "\n".join(lines)
