"""Session manager for handling multiple node sessions."""

import time
from dataclasses import dataclass
from .session import Session


@dataclass
class SessionEntry:
    """Internal entry storing session and metadata."""

    session: Session
    last_access: float  # Unix timestamp


class SessionManager:
    """Manages sessions for multiple nodes.

    Provides session storage with automatic timeout cleanup.
    """

    def __init__(self, timeout_seconds: int = 1800):
        """
        Initialize the session manager.

        Args:
            timeout_seconds: Seconds of inactivity before session expires.
                            Default is 30 minutes.
        """
        self._sessions: dict[str, SessionEntry] = {}
        self._timeout = timeout_seconds

    def get_session(self, node_id: str) -> Session:
        """
        Get or create a session for a node.

        If the node doesn't have a session, a new one is created.
        Accessing a session refreshes its last access time.

        Args:
            node_id: The Meshtastic node ID (e.g., "!abcd1234").

        Returns:
            The session for this node.
        """
        if node_id not in self._sessions:
            self._sessions[node_id] = SessionEntry(
                session=Session(),
                last_access=time.time(),
            )
        else:
            # Refresh timestamp on access
            self._sessions[node_id].last_access = time.time()

        return self._sessions[node_id].session

    def update_session(self, node_id: str, session: Session) -> None:
        """
        Update the session for a node.

        Also refreshes the last access time.

        Args:
            node_id: The Meshtastic node ID.
            session: The new session state.
        """
        self._sessions[node_id] = SessionEntry(
            session=session,
            last_access=time.time(),
        )

    def remove_session(self, node_id: str) -> None:
        """
        Remove a node's session.

        Args:
            node_id: The Meshtastic node ID.
        """
        self._sessions.pop(node_id, None)

    def cleanup_expired(self) -> int:
        """
        Remove expired sessions.

        Returns:
            Number of sessions removed.
        """
        now = time.time()
        expired = [
            node_id
            for node_id, entry in self._sessions.items()
            if now - entry.last_access > self._timeout
        ]

        for node_id in expired:
            del self._sessions[node_id]

        return len(expired)

    def session_count(self) -> int:
        """Get the number of active sessions."""
        return len(self._sessions)

    def list_nodes(self) -> list[str]:
        """Get list of all node IDs with active sessions."""
        return list(self._sessions.keys())
