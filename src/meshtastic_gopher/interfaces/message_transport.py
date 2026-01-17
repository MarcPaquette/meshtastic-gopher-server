"""Abstract interface for message transport."""

from abc import ABC, abstractmethod
from typing import Callable


class MessageTransport(ABC):
    """Abstract interface for sending/receiving messages."""

    @abstractmethod
    def send(self, node_id: str, message: str, want_ack: bool = False) -> None:
        """Send a message to a specific node.

        Args:
            node_id: The destination node ID.
            message: The message text to send.
            want_ack: If True, request acknowledgment for reliable delivery.
        """
        pass

    @abstractmethod
    def send_with_retry(self, node_id: str, message: str, timeout: float = 30.0) -> bool:
        """Send a message and wait for ACK, with one retry on timeout.

        Args:
            node_id: The destination node ID.
            message: The message text to send.
            timeout: Maximum seconds to wait for ACK per attempt.

        Returns:
            True if ACK received (on first or retry attempt), False otherwise.
        """
        pass

    @abstractmethod
    def on_message(self, callback: Callable[[str, str], None]) -> None:
        """Register a callback for incoming messages.

        The callback receives (node_id, message).
        """
        pass

    @abstractmethod
    def connect(self) -> None:
        """Connect to the transport."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the transport."""
        pass
