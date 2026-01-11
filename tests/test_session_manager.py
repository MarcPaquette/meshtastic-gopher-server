"""Tests for the SessionManager module."""

import pytest
import time
from meshtastic_gopher.core.session_manager import SessionManager
from meshtastic_gopher.core.session import Session


class TestSessionManager:
    """Tests for SessionManager."""

    def test_get_session_creates_new(self):
        """get_session creates a new session for unknown node."""
        manager = SessionManager()
        session = manager.get_session("!node1")
        assert isinstance(session, Session)
        assert session.current_path == "/"

    def test_get_session_returns_existing(self):
        """get_session returns existing session."""
        manager = SessionManager()

        # Get initial session
        session1 = manager.get_session("!node1")

        # Modify and update
        session2 = session1.navigate_to("/documents")
        manager.update_session("!node1", session2)

        # Get again - should have the update
        session3 = manager.get_session("!node1")
        assert session3.current_path == "/documents"

    def test_update_session(self):
        """update_session stores new session state."""
        manager = SessionManager()

        session = Session(current_path="/test")
        manager.update_session("!node1", session)

        retrieved = manager.get_session("!node1")
        assert retrieved.current_path == "/test"

    def test_different_nodes_different_sessions(self):
        """Different nodes have independent sessions."""
        manager = SessionManager()

        # Set up node1
        session1 = manager.get_session("!node1").navigate_to("/a")
        manager.update_session("!node1", session1)

        # Set up node2
        session2 = manager.get_session("!node2").navigate_to("/b")
        manager.update_session("!node2", session2)

        # Verify independence
        assert manager.get_session("!node1").current_path == "/a"
        assert manager.get_session("!node2").current_path == "/b"

    def test_remove_session(self):
        """remove_session deletes a node's session."""
        manager = SessionManager()

        # Create session
        manager.get_session("!node1")

        # Remove it
        manager.remove_session("!node1")

        # Get should create fresh session
        session = manager.get_session("!node1")
        assert session.current_path == "/"

    def test_remove_nonexistent_session(self):
        """remove_session does nothing for unknown node."""
        manager = SessionManager()
        manager.remove_session("!unknown")  # Should not raise

    def test_cleanup_expired_sessions(self):
        """cleanup removes sessions older than timeout."""
        # Use 0 second timeout for testing
        manager = SessionManager(timeout_seconds=0)

        # Create session
        manager.get_session("!node1")

        # Wait briefly
        time.sleep(0.01)

        # Cleanup should remove it
        removed = manager.cleanup_expired()
        assert removed == 1

        # Session should be fresh
        assert "!node1" not in manager._sessions

    def test_cleanup_keeps_active_sessions(self):
        """cleanup keeps sessions that aren't expired."""
        # Use long timeout
        manager = SessionManager(timeout_seconds=3600)

        # Create session
        manager.get_session("!node1")

        # Cleanup should not remove it
        removed = manager.cleanup_expired()
        assert removed == 0
        assert "!node1" in manager._sessions

    def test_update_session_refreshes_timestamp(self):
        """Updating a session refreshes its last access time."""
        manager = SessionManager(timeout_seconds=1)

        # Create session
        session = manager.get_session("!node1")

        # Wait a bit
        time.sleep(0.5)

        # Update session - should refresh timestamp
        manager.update_session("!node1", session.navigate_to("/test"))

        # Wait a bit more (total > 1 second from creation but < 1 from update)
        time.sleep(0.6)

        # Cleanup should not remove it (was updated recently)
        removed = manager.cleanup_expired()
        assert removed == 0

    def test_get_session_refreshes_timestamp(self):
        """Getting a session refreshes its last access time."""
        manager = SessionManager(timeout_seconds=1)

        # Create session
        manager.get_session("!node1")

        # Wait a bit
        time.sleep(0.5)

        # Get session - should refresh timestamp
        manager.get_session("!node1")

        # Wait a bit more
        time.sleep(0.6)

        # Cleanup should not remove it
        removed = manager.cleanup_expired()
        assert removed == 0

    def test_session_count(self):
        """session_count returns number of active sessions."""
        manager = SessionManager()

        assert manager.session_count() == 0

        manager.get_session("!node1")
        assert manager.session_count() == 1

        manager.get_session("!node2")
        assert manager.session_count() == 2

        manager.remove_session("!node1")
        assert manager.session_count() == 1

    def test_list_nodes(self):
        """list_nodes returns all node IDs with sessions."""
        manager = SessionManager()

        manager.get_session("!node1")
        manager.get_session("!node2")

        nodes = manager.list_nodes()
        assert set(nodes) == {"!node1", "!node2"}
