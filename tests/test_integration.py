"""Integration tests for GopherServer."""

import pytest
from unittest.mock import Mock
from meshtastic_gopher.server import GopherServer
from meshtastic_gopher.providers import FilesystemProvider
from meshtastic_gopher.config import Config


class MockTransport:
    """Mock transport for testing."""

    def __init__(self):
        self._callbacks = []
        self.sent_messages = []
        self._connected = False

    def send(self, node_id: str, message: str, want_ack: bool = False) -> None:
        self.sent_messages.append((node_id, message))

    def send_with_retry(self, node_id: str, message: str, timeout: float = 30.0) -> bool:
        """Mock send with retry - always succeeds in tests."""
        self.sent_messages.append((node_id, message))
        return True

    def on_message(self, callback) -> None:
        self._callbacks.append(callback)

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def simulate_message(self, node_id: str, message: str) -> None:
        """Simulate receiving a message."""
        for callback in self._callbacks:
            callback(node_id, message)


class TestGopherServerIntegration:
    """Integration tests for GopherServer."""

    @pytest.fixture
    def server(self, temp_content_dir):
        """Create a server with mock transport and real filesystem provider."""
        provider = FilesystemProvider(temp_content_dir)
        transport = MockTransport()
        config = Config(
            root_directory=str(temp_content_dir),
            max_message_size=230,
            auto_send_threshold=3,
        )
        server = GopherServer(provider, transport, config)
        return server, transport

    def test_welcome_shows_root_directory(self, server):
        """send_welcome shows root directory listing."""
        srv, transport = server
        srv.start()

        srv.send_welcome("!node1")

        assert len(transport.sent_messages) == 1
        node_id, message = transport.sent_messages[0]
        assert node_id == "!node1"
        assert "documents/" in message
        assert "welcome.txt" in message

    def test_help_command(self, server):
        """? command shows help."""
        srv, transport = server
        srv.start()

        transport.simulate_message("!node1", "?")

        assert len(transport.sent_messages) == 1
        _, message = transport.sent_messages[0]
        assert "Help" in message
        assert "Back" in message or "b" in message

    def test_select_directory(self, server):
        """Selecting a directory navigates into it."""
        srv, transport = server
        srv.start()

        # First get the root listing
        srv.send_welcome("!node1")
        transport.sent_messages.clear()

        # Select documents (should be item 1 since dirs are first)
        transport.simulate_message("!node1", "1")

        _, message = transport.sent_messages[0]
        assert "readme.txt" in message or "subfolder" in message

    def test_select_file(self, server):
        """Selecting a file shows its content."""
        srv, transport = server
        srv.start()

        # Get root listing
        srv.send_welcome("!node1")
        transport.sent_messages.clear()

        # Find welcome.txt index (it's a file so after dirs)
        # In root: documents/ (dir), welcome.txt (file)
        # So welcome.txt is item 2
        transport.simulate_message("!node1", "2")

        _, message = transport.sent_messages[0]
        assert "Welcome to the Gopher server!" in message

    def test_back_navigation(self, server):
        """b command navigates back."""
        srv, transport = server
        srv.start()

        # Navigate into documents
        srv.send_welcome("!node1")
        transport.simulate_message("!node1", "1")  # Enter documents
        transport.sent_messages.clear()

        # Go back
        transport.simulate_message("!node1", "b")

        _, message = transport.sent_messages[0]
        # Should be back at root
        assert "[/]" in message

    def test_home_navigation(self, server):
        """h command navigates to root."""
        srv, transport = server
        srv.start()

        # Navigate deep
        srv.send_welcome("!node1")
        transport.simulate_message("!node1", "1")  # Enter documents
        transport.simulate_message("!node1", "1")  # Enter subfolder
        transport.sent_messages.clear()

        # Go home
        transport.simulate_message("!node1", "h")

        _, message = transport.sent_messages[0]
        assert "[/]" in message

    def test_invalid_selection(self, server):
        """Invalid selection shows error."""
        srv, transport = server
        srv.start()

        srv.send_welcome("!node1")
        transport.sent_messages.clear()

        transport.simulate_message("!node1", "99")

        _, message = transport.sent_messages[0]
        assert "Invalid selection" in message

    def test_unknown_command(self, server):
        """Unknown command shows error with help hint."""
        srv, transport = server
        srv.start()

        transport.simulate_message("!node1", "xyz")

        _, message = transport.sent_messages[0]
        assert "Unknown command" in message
        assert "?" in message  # Help hint

    def test_pagination_long_file(self, server, temp_content_dir):
        """Long files are paginated."""
        # The fixture creates a file with 500 chars
        srv, transport = server
        srv.start()

        # Navigate to documents
        srv.send_welcome("!node1")
        transport.simulate_message("!node1", "1")  # Enter documents
        transport.sent_messages.clear()

        # Select long_file.txt (should be item after subfolder dir)
        # In documents: subfolder/ (dir), long_file.txt, readme.txt (files alphabetically)
        transport.simulate_message("!node1", "2")  # long_file.txt

        _, message = transport.sent_messages[0]
        # Should indicate more pages
        assert "[1/" in message or "n=next" in message.lower()

    def test_pagination_next(self, server, temp_content_dir):
        """n command shows next page."""
        # Create a very long file that will definitely require pagination
        (temp_content_dir / "documents" / "very_long.txt").write_text("B" * 2000)

        srv, transport = server
        srv.start()

        # Navigate to and select very long file
        srv.send_welcome("!node1")
        transport.simulate_message("!node1", "1")  # Enter documents
        transport.sent_messages.clear()

        # Select very_long.txt (files are sorted alphabetically: long_file, readme, subfolder, very_long)
        # Actually dirs first: subfolder/ then files: long_file.txt, readme.txt, very_long.txt
        # So very_long.txt is item 4
        transport.simulate_message("!node1", "4")  # very_long.txt

        # Verify we got pagination - first message has content, second has nav hint
        messages = [m for _, m in transport.sent_messages]
        combined = " ".join(messages)
        assert "[1/" in combined and "n=next" in combined.lower()

        transport.sent_messages.clear()

        # Get next page
        transport.simulate_message("!node1", "n")

        _, message = transport.sent_messages[0]
        assert "[2/" in message or "BBB" in message

    def test_separate_sessions_per_node(self, server):
        """Different nodes have independent sessions."""
        srv, transport = server
        srv.start()

        # Node 1 navigates into documents
        srv.send_welcome("!node1")
        transport.simulate_message("!node1", "1")

        # Node 2 starts fresh
        srv.send_welcome("!node2")

        # Find the message sent to node2
        node2_messages = [m for n, m in transport.sent_messages if n == "!node2"]
        assert len(node2_messages) > 0
        # Node 2 should see root directory
        assert "[/]" in node2_messages[-1]

    def test_case_insensitive_commands(self, server):
        """Commands are case insensitive."""
        srv, transport = server
        srv.start()

        transport.simulate_message("!node1", "H")  # Uppercase home

        _, message = transport.sent_messages[0]
        assert "[/]" in message or "documents" in message

    def test_pagination_all(self, server, temp_content_dir):
        """a command sends all remaining pages."""
        # Create a very long file that will require multiple pages
        (temp_content_dir / "documents" / "very_long.txt").write_text("C" * 2000)

        srv, transport = server
        srv.start()

        # Navigate to and select very long file
        srv.send_welcome("!node1")
        transport.simulate_message("!node1", "1")  # Enter documents
        transport.sent_messages.clear()

        # Select very_long.txt (dirs first: subfolder/, then files: long_file.txt, readme.txt, very_long.txt)
        transport.simulate_message("!node1", "4")  # very_long.txt

        # Verify we got pagination with both n=next and a=all options
        messages = [m for _, m in transport.sent_messages]
        combined = " ".join(messages)
        assert "n=next" in combined.lower()
        assert "a=all" in combined.lower()

        transport.sent_messages.clear()

        # Send 'a' to get all remaining pages
        transport.simulate_message("!node1", "a")

        # Should receive multiple messages with all remaining content
        messages = [m for _, m in transport.sent_messages]
        assert len(messages) >= 1

        # Last message should have [End] marker
        combined = " ".join(messages)
        assert "[End]" in combined

        # Should contain file content
        assert "CCC" in combined

    def test_all_command_no_pagination(self, server):
        """a command when not paginating shows error."""
        srv, transport = server
        srv.start()

        # Send 'a' without being in pagination
        transport.simulate_message("!node1", "a")

        _, message = transport.sent_messages[0]
        assert "No content to page through" in message

    def test_all_command_uppercase(self, server, temp_content_dir):
        """A command (uppercase) also sends all remaining pages."""
        (temp_content_dir / "documents" / "very_long.txt").write_text("D" * 2000)

        srv, transport = server
        srv.start()

        srv.send_welcome("!node1")
        transport.simulate_message("!node1", "1")  # Enter documents
        transport.simulate_message("!node1", "4")  # very_long.txt
        transport.sent_messages.clear()

        # Send uppercase 'A'
        transport.simulate_message("!node1", "A")

        messages = [m for _, m in transport.sent_messages]
        combined = " ".join(messages)
        assert "[End]" in combined


class TestGopherServerEdgeCases:
    """Edge case tests for GopherServer."""

    @pytest.fixture
    def server(self, temp_content_dir):
        """Create a server with mock transport."""
        provider = FilesystemProvider(temp_content_dir)
        transport = MockTransport()
        config = Config(root_directory=str(temp_content_dir))
        server = GopherServer(provider, transport, config)
        return server, transport

    def test_empty_directory(self, server, temp_content_dir):
        """Empty directory shows appropriate message."""
        # Create empty dir
        (temp_content_dir / "empty").mkdir()

        srv, transport = server
        srv.start()

        srv.send_welcome("!node1")
        transport.simulate_message("!node1", "1")  # Assuming documents is first
        transport.sent_messages.clear()

        # Need to navigate to empty - it would be sorted
        # Let's just test the show_directory directly through a message

    def test_whitespace_message(self, server):
        """Whitespace-only message is handled."""
        srv, transport = server
        srv.start()

        transport.simulate_message("!node1", "   ")

        _, message = transport.sent_messages[0]
        assert "Unknown" in message or "help" in message.lower()

    def test_numeric_with_spaces(self, server):
        """Numbers with spaces are parsed correctly."""
        srv, transport = server
        srv.start()

        srv.send_welcome("!node1")
        transport.sent_messages.clear()

        transport.simulate_message("!node1", "  1  ")

        # Should work as selection 1
        _, message = transport.sent_messages[0]
        # Should not be an error
        assert "Invalid" not in message or "1" not in message


class TestGopherServerLifecycle:
    """Tests for server start/stop lifecycle."""

    @pytest.fixture
    def server(self, temp_content_dir):
        """Create a server with mock transport."""
        provider = FilesystemProvider(temp_content_dir)
        transport = MockTransport()
        config = Config(root_directory=str(temp_content_dir))
        server = GopherServer(provider, transport, config)
        return server, transport

    def test_start_connects_transport(self, server):
        """start() connects the transport."""
        srv, transport = server
        assert not transport._connected

        srv.start()

        assert transport._connected

    def test_stop_disconnects_transport(self, server):
        """stop() disconnects the transport."""
        srv, transport = server
        srv.start()
        assert transport._connected

        srv.stop()

        assert not transport._connected


class TestGopherServerErrorHandling:
    """Tests for error handling in GopherServer."""

    @pytest.fixture
    def server(self, temp_content_dir):
        """Create a server with mock transport."""
        provider = FilesystemProvider(temp_content_dir)
        transport = MockTransport()
        config = Config(root_directory=str(temp_content_dir), max_message_size=200)
        server = GopherServer(provider, transport, config)
        return server, transport, temp_content_dir

    def test_exception_in_handler_sends_error(self, server):
        """Exception during message handling sends error to node."""
        srv, transport, temp_dir = server
        srv.start()

        # Navigate to root then delete a file to cause an error
        srv.send_welcome("!node1")

        # Mock the content provider to raise an exception
        original_exists = srv.content_provider.exists
        srv.content_provider.exists = Mock(side_effect=Exception("Test error"))

        transport.sent_messages.clear()
        transport.simulate_message("!node1", "1")

        # Should have sent an error message
        _, message = transport.sent_messages[0]
        assert "Error" in message

        # Restore
        srv.content_provider.exists = original_exists

    def test_send_error_truncates_long_errors(self, server):
        """_send_error truncates error messages that exceed max size."""
        srv, transport, _ = server
        srv.start()

        # Create a very long error message
        long_error = "X" * 500
        srv._send_error("!node1", long_error)

        _, message = transport.sent_messages[0]
        assert len(message) <= srv.config.max_message_size
        assert message.startswith("Error:")
        assert message.endswith("...")

    def test_send_error_short_message(self, server):
        """_send_error sends short messages as-is."""
        srv, transport, _ = server
        srv.start()

        srv._send_error("!node1", "Short error")

        _, message = transport.sent_messages[0]
        assert message == "Error: Short error"

    def test_path_not_found_returns_home(self, server):
        """Navigating to non-existent path returns to home."""
        srv, transport, temp_dir = server
        srv.start()

        # Get a session and manually set a bad path
        session = srv.session_manager.get_session("!node1")
        bad_session = session.navigate_to("/nonexistent/path")
        srv.session_manager.update_session("!node1", bad_session)

        transport.simulate_message("!node1", "h")  # Go home first to reset
        transport.sent_messages.clear()

        # Manually trigger showing a non-existent directory
        bad_session = session.navigate_to("/definitely/not/real")
        srv.session_manager.update_session("!node1", bad_session)

        # Send any command to trigger directory display
        transport.simulate_message("!node1", "b")

        messages = [m for _, m in transport.sent_messages]
        combined = " ".join(messages)
        # Should show "Path not found" or be back at root
        assert "not found" in combined.lower() or "[/]" in combined

    def test_empty_file_display(self, server):
        """Empty files show appropriate message."""
        srv, transport, temp_dir = server

        # Create empty file
        (temp_dir / "empty.txt").write_text("")

        srv.start()
        srv.send_welcome("!node1")
        transport.sent_messages.clear()

        # Find and select empty.txt
        # Root has: documents/, empty.txt, welcome.txt
        # empty.txt should be item 2 (after documents/)
        transport.simulate_message("!node1", "2")

        _, message = transport.sent_messages[0]
        assert "empty" in message.lower()

    def test_next_without_pagination(self, server):
        """'n' command without active pagination shows message."""
        srv, transport, _ = server
        srv.start()

        transport.simulate_message("!node1", "n")

        _, message = transport.sent_messages[0]
        assert "No content to page through" in message

    def test_pagination_end_clears_state(self, server):
        """Reaching end of pagination clears pagination state."""
        srv, transport, temp_dir = server

        # Create file with many pages (>3 to exceed auto_send_threshold)
        # max_message_size is 200, so 1000 chars = ~5 pages
        (temp_dir / "many_pages.txt").write_text("A" * 1000)

        srv.start()
        srv.send_welcome("!node1")
        transport.sent_messages.clear()

        # Select many_pages.txt (after documents/, before welcome.txt alphabetically)
        transport.simulate_message("!node1", "2")

        # Should be in pagination mode now
        session = srv.session_manager.get_session("!node1")
        assert session.has_pagination(), "File should trigger pagination mode"

        # Navigate to last page
        while session.has_pagination():
            transport.sent_messages.clear()
            transport.simulate_message("!node1", "n")
            session = srv.session_manager.get_session("!node1")

        # Check that last message had [End] marker
        messages = [m for _, m in transport.sent_messages]
        combined = " ".join(messages)
        assert "[End]" in combined

        # Pagination should be cleared
        assert not session.has_pagination()


class TestGopherServerMessageDelivery:
    """Tests for message delivery and retry logic."""

    @pytest.fixture
    def server_with_failing_transport(self, temp_content_dir):
        """Create a server with a transport that can simulate failures."""
        provider = FilesystemProvider(temp_content_dir)

        class FailingTransport(MockTransport):
            def __init__(self):
                super().__init__()
                self.fail_next = False

            def send_with_retry(self, node_id: str, message: str, timeout: float = 30.0) -> bool:
                self.sent_messages.append((node_id, message))
                if self.fail_next:
                    self.fail_next = False
                    return False
                return True

        transport = FailingTransport()
        config = Config(root_directory=str(temp_content_dir))
        server = GopherServer(provider, transport, config)
        return server, transport

    def test_failed_message_delivery_continues(self, server_with_failing_transport):
        """Server continues sending remaining messages even if one fails."""
        srv, transport = server_with_failing_transport
        srv.start()

        # Create a long file that requires multiple messages
        # Manually trigger _send_response with multi-part content
        session = srv.session_manager.get_session("!node1")

        # Make first message fail
        transport.fail_next = True

        # Send a multi-part response
        srv._send_response("!node1", "Part1\n---\nPart2\n---\nPart3", session)

        # Should have attempted to send all 3 parts
        assert len(transport.sent_messages) == 3
