"""Meshtastic-based message transport."""

from typing import Callable
from pubsub import pub

from meshtastic import serial_interface, tcp_interface, ble_interface

from ..interfaces import MessageTransport


class MeshtasticTransport(MessageTransport):
    """Message transport using Meshtastic mesh network.

    Supports Serial, BLE, and TCP connection types.
    """

    def __init__(self, connection_type: str = "serial", device: str | None = None):
        """
        Initialize the transport.

        Args:
            connection_type: Type of connection - "serial", "ble", or "tcp".
            device: Device path, BLE address, or hostname depending on type.
                   If None, will auto-detect for serial connections.
        """
        self.connection_type = connection_type
        self.device = device
        self._interface = None
        self._callbacks: list[Callable[[str, str], None]] = []

    def send(self, node_id: str, message: str) -> None:
        """
        Send a message to a specific node.

        Args:
            node_id: The destination node ID (e.g., "!abcd1234").
            message: The message text to send.

        Raises:
            RuntimeError: If not connected.
        """
        if self._interface is None:
            raise RuntimeError("Not connected. Call connect() first.")

        self._interface.sendText(message, destinationId=node_id)

    def on_message(self, callback: Callable[[str, str], None]) -> None:
        """
        Register a callback for incoming messages.

        The callback receives (node_id, message_text).

        Args:
            callback: Function to call when a message is received.
        """
        self._callbacks.append(callback)

    def connect(self) -> None:
        """
        Connect to the Meshtastic device.

        Creates the appropriate interface based on connection_type.
        """
        if self.connection_type == "serial":
            self._interface = serial_interface.SerialInterface(devPath=self.device)
        elif self.connection_type == "ble":
            self._interface = ble_interface.BLEInterface(address=self.device)
        elif self.connection_type == "tcp":
            self._interface = tcp_interface.TCPInterface(hostname=self.device)
        else:
            raise ValueError(f"Unknown connection type: {self.connection_type}")

        # Subscribe to text messages
        pub.subscribe(self._handle_receive, "meshtastic.receive.text")

    def disconnect(self) -> None:
        """Disconnect from the Meshtastic device."""
        if self._interface is not None:
            # Unsubscribe from messages
            try:
                pub.unsubscribe(self._handle_receive, "meshtastic.receive.text")
            except Exception:
                pass  # May not be subscribed

            self._interface.close()
            self._interface = None

    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._interface is not None

    def _handle_receive(self, packet: dict, interface) -> None:
        """
        Handle received packets from Meshtastic.

        Extracts text messages and calls registered callbacks.

        Args:
            packet: The received packet dictionary.
            interface: The Meshtastic interface (unused but required by pubsub).
        """
        # Extract sender and message
        from_id = packet.get("fromId")
        decoded = packet.get("decoded", {})
        text = decoded.get("text")

        if from_id and text:
            for callback in self._callbacks:
                try:
                    callback(from_id, text)
                except Exception:
                    # Don't let one callback failure break others
                    pass
