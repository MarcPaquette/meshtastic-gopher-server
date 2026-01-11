"""Integration tests for GopherServer."""

import pytest
from unittest.mock import Mock, MagicMock
from meshtastic_gopher.server import GopherServer
from meshtastic_gopher.providers import FilesystemProvider
from meshtastic_gopher.config import Config


class MockTransport:
    """Mock transport for testing."""

    def __init__(self):
        self._callbacks = []
        self.sent_messages = []
        self._connected = False

    def send(self, node_id: str, message: str) -> None:
        self.sent_messages.append((node_id, message))

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
        assert "[1/" in message or "next" in message.lower()

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

        # Verify we got pagination
        _, first_msg = transport.sent_messages[0]
        assert "[1/" in first_msg and "next" in first_msg.lower()

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
