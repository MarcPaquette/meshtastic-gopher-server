"""Abstract interface for message transport."""

from abc import ABC, abstractmethod
from typing import Callable


class MessageTransport(ABC):
    """Abstract interface for sending/receiving messages."""

    @abstractmethod
    def send(self, node_id: str, message: str) -> None:
        """Send a message to a specific node."""
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
