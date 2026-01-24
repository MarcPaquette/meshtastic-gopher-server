"""GopherServer - Main orchestrator for the Meshtastic Gopher Server."""

import logging

from .interfaces import ContentProvider, MessageTransport
from .core import (
    CommandParser,
    SelectCommand,
    BackCommand,
    NextCommand,
    AllCommand,
    HomeCommand,
    HelpCommand,
    InvalidCommand,
    ContentChunker,
    MenuRenderer,
    Session,
    SessionManager,
)
from .config import Config

logger = logging.getLogger(__name__)


class GopherServer:
    """Main server orchestrating all components.

    Handles incoming messages, processes commands, and sends responses.
    Uses dependency injection for content provider and transport.
    """

    HELP_TEXT = """Gopher Server Help:
[num] - Select item
b - Back to parent
h - Home (root)
n - Next page
a - All pages
? - This help"""

    def __init__(
        self,
        content_provider: ContentProvider,
        transport: MessageTransport,
        config: Config | None = None,
    ):
        """
        Initialize the Gopher server.

        Args:
            content_provider: Provider for accessing content (files/dirs).
            transport: Transport for sending/receiving messages.
            config: Server configuration (uses defaults if None).
        """
        self.content_provider = content_provider
        self.transport = transport
        self.config = config or Config()

        # Initialize components
        self.parser = CommandParser()
        self.chunker = ContentChunker(max_size=self.config.max_message_size)
        self.renderer = MenuRenderer()
        self.session_manager = SessionManager(
            timeout_seconds=self.config.session_timeout_minutes * 60
        )

        # Register message handler
        self.transport.on_message(self._handle_message)

    def start(self) -> None:
        """Start the server by connecting to transport."""
        logger.info("Starting Gopher server...")
        self.transport.connect()
        logger.info("Server started and listening for messages")

    def stop(self) -> None:
        """Stop the server by disconnecting transport."""
        logger.info("Stopping Gopher server...")
        self.transport.disconnect()
        logger.info("Server stopped")

    def _handle_message(self, node_id: str, message: str) -> None:
        """
        Handle an incoming message from a node.

        Args:
            node_id: The sender's node ID.
            message: The message text.
        """
        logger.info(f"[{node_id}] Received: {message!r}")

        try:
            # Get or create session for this node
            session = self.session_manager.get_session(node_id)

            # Parse the command
            command = self.parser.parse(message)
            logger.info(f"[{node_id}] Command: {command.__class__.__name__}")

            # Process command and get response + updated session
            response, new_session = self._process_command(command, session)

            # Update session
            self.session_manager.update_session(node_id, new_session)

            # Send response(s)
            self._send_response(node_id, response, new_session)

        except Exception as e:
            logger.error(f"[{node_id}] Error: {e}")
            self._send_error(node_id, str(e))

    def _process_command(
        self, command, session: Session
    ) -> tuple[str, Session]:
        """
        Process a command and return response with updated session.

        Args:
            command: The parsed command.
            session: The current session state.

        Returns:
            Tuple of (response_text, updated_session).
        """
        if isinstance(command, HelpCommand):
            logger.debug("Showing help text")
            return self.HELP_TEXT, session

        if isinstance(command, InvalidCommand):
            logger.debug(f"Invalid command: {command.original_input}")
            return f"Unknown command: {command.original_input}\nSend ? for help", session

        if isinstance(command, HomeCommand):
            logger.debug("Navigating to home")
            new_session = session.navigate_home()
            return self._show_directory(new_session)

        if isinstance(command, BackCommand):
            logger.debug(f"Navigating back from {session.current_path}")
            new_session = session.navigate_back()
            return self._show_directory(new_session)

        if isinstance(command, NextCommand):
            return self._handle_next(session)

        if isinstance(command, AllCommand):
            return self._handle_all(session)

        if isinstance(command, SelectCommand):
            return self._handle_select(command.index, session)

        return "Unknown command type", session

    def _show_directory(self, session: Session) -> tuple[str, Session]:
        """
        Show the current directory listing.

        Args:
            session: The session with current path.

        Returns:
            Tuple of (rendered_menu, updated_session).
        """
        path = session.current_path
        logger.info(f"Listing directory: {path}")

        if not self.content_provider.exists(path):
            logger.warning(f"Path not found: {path}")
            return f"Path not found: {path}", session.navigate_home()

        if not self.content_provider.is_directory(path):
            # It's a file - read and display it
            return self._show_file(path, session)

        # List directory and sort (dirs first, then files, alphabetically)
        entries = self.content_provider.list_directory(path)
        dirs = sorted([e for e in entries if e.is_dir], key=lambda e: e.name.lower())
        files = sorted([e for e in entries if not e.is_dir], key=lambda e: e.name.lower())
        sorted_entries = dirs + files

        logger.debug(f"Directory has {len(dirs)} dirs, {len(files)} files")

        new_session = session.set_listing(sorted_entries)

        # Render menu (renderer expects already sorted entries for consistency)
        menu = self.renderer.render(sorted_entries, current_path=path)

        return menu, new_session

    def _show_file(self, path: str, session: Session) -> tuple[str, Session]:
        """
        Show file contents (with pagination if needed).

        Args:
            path: Path to the file.
            session: Current session.

        Returns:
            Tuple of (content/first_chunk, updated_session).
        """
        logger.info(f"Reading file: {path}")
        content = self.content_provider.read_file(path)
        chunks = self.chunker.chunk(content)

        if not chunks:
            logger.debug("File is empty")
            return "(empty file)", session

        # Single chunk or few chunks - send all
        if len(chunks) <= self.config.auto_send_threshold:
            logger.info(f"Sending file in {len(chunks)} chunk(s) (auto-send)")
            return "\n---\n".join(chunks), session.clear_pagination()

        # Many chunks - paginate
        logger.info(f"File requires pagination: {len(chunks)} pages")
        new_session = session.start_pagination(chunks)
        first_chunk = chunks[0]
        # Send first chunk, then navigation hint as separate message to avoid overflow
        return f"{first_chunk}\n---\n[n=next, a=all]", new_session

    def _handle_next(self, session: Session) -> tuple[str, Session]:
        """
        Handle next page command.

        Args:
            session: Current session.

        Returns:
            Tuple of (next_chunk, updated_session).
        """
        if not session.has_pagination():
            logger.debug("Next requested but no active pagination")
            return "No content to page through", session

        new_session = session.advance_pagination()
        page_num = new_session.pagination.current_page + 1
        total = new_session.pagination.total_pages()
        logger.info(f"Sending page {page_num}/{total}")

        chunk = new_session.pagination.current_chunk()
        if chunk is None:
            return "End of content", new_session.clear_pagination()

        if new_session.pagination.has_next():
            return f"{chunk}\n---\n[n=next, a=all]", new_session
        else:
            logger.info("Reached end of pagination")
            return f"{chunk}\n---\n[End]", new_session.clear_pagination()

    def _handle_all(self, session: Session) -> tuple[str, Session]:
        """
        Handle all pages command - send all remaining pages.

        Args:
            session: Current session.

        Returns:
            Tuple of (all_remaining_chunks, updated_session).
        """
        if not session.has_pagination():
            logger.debug("All requested but no active pagination")
            return "No content to page through", session

        # Collect all remaining chunks
        remaining_chunks = []
        current_session = session

        while current_session.has_pagination():
            current_session = current_session.advance_pagination()
            chunk = current_session.pagination.current_chunk()
            if chunk:
                remaining_chunks.append(chunk)
            if not current_session.pagination.has_next():
                break

        if not remaining_chunks:
            return "End of content", session.clear_pagination()

        logger.info(f"Sending all remaining {len(remaining_chunks)} page(s)")

        # Add [End] marker to last chunk
        remaining_chunks[-1] = f"{remaining_chunks[-1]}\n---\n[End]"

        # Join with delimiter for _send_response to split and send separately
        return "\n---\n".join(remaining_chunks), current_session.clear_pagination()

    def _handle_select(self, index: int, session: Session) -> tuple[str, Session]:
        """
        Handle selection of a numbered item.

        Args:
            index: The 1-based index selected.
            session: Current session.

        Returns:
            Tuple of (response, updated_session).
        """
        entry = session.get_entry_at(index)

        if entry is None:
            logger.debug(f"Invalid selection: {index}")
            return f"Invalid selection: {index}", session

        # Resolve the full path
        new_path = session.resolve_path(entry.name)
        logger.info(f"Selected [{index}]: {entry.name} ({'dir' if entry.is_dir else 'file'})")

        if entry.is_dir:
            # Navigate into directory
            new_session = session.navigate_to(new_path)
            return self._show_directory(new_session)
        else:
            # Show file
            return self._show_file(new_path, session)

    def _send_response(self, node_id: str, response: str, session: Session) -> None:
        """
        Send response message(s) to a node.

        All responses are chunked if they exceed max_message_size.
        Each message waits for ACK before sending the next (with retry on timeout).

        Args:
            node_id: Target node ID.
            response: Response text.
            session: Current session (for context).
        """
        # For paginated auto-send content, split by our delimiter first
        if "\n---\n" in response:
            parts = response.split("\n---\n")
        else:
            parts = [response]

        # Collect all messages to send
        messages = []
        for part in parts:
            if len(part) <= self.config.max_message_size:
                messages.append(part)
            else:
                # Chunk oversized messages
                messages.extend(self.chunker.chunk(part))

        # Send messages, waiting for ACK before each subsequent message
        logger.info(f"[{node_id}] Sending {len(messages)} message(s)")
        timeout = self.config.ack_timeout_seconds
        for i, message in enumerate(messages):
            preview = message[:50].replace('\n', ' ')
            logger.debug(f"[{node_id}] Message {i+1}/{len(messages)} ({len(message)} chars): {preview}...")
            success = self.transport.send_with_retry(node_id, message, timeout=timeout)
            if success:
                logger.debug(f"[{node_id}] Message {i+1}/{len(messages)} delivered")
            else:
                logger.warning(f"[{node_id}] Message {i+1}/{len(messages)} failed after retry")

    def _send_error(self, node_id: str, error: str) -> None:
        """Send error message to a node."""
        message = f"Error: {error}"
        if len(message) <= self.config.max_message_size:
            self.transport.send(node_id, message)
        else:
            # Truncate long error messages to fit
            max_error_len = self.config.max_message_size - len("Error: ...")
            self.transport.send(node_id, f"Error: {error[:max_error_len]}...")

    def send_welcome(self, node_id: str) -> None:
        """
        Send welcome message with root directory listing.

        Args:
            node_id: Target node ID.
        """
        session = self.session_manager.get_session(node_id)
        response, new_session = self._show_directory(session)
        self.session_manager.update_session(node_id, new_session)
        self._send_response(node_id, response, new_session)
