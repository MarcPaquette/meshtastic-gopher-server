"""Abstract interfaces for the Meshtastic Gopher Server."""

from .content_provider import ContentProvider, Entry
from .message_transport import MessageTransport

__all__ = ["ContentProvider", "Entry", "MessageTransport"]
