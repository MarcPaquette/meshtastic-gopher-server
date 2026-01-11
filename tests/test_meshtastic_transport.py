"""Tests for the MeshtasticTransport module."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from meshtastic_gopher.transport.meshtastic_transport import MeshtasticTransport


class TestMeshtasticTransport:
    """Tests for MeshtasticTransport."""

    def test_init_serial_default(self):
        """Initialize with serial connection type by default."""
        transport = MeshtasticTransport()
        assert transport.connection_type == "serial"
        assert transport.device is None

    def test_init_serial_with_device(self):
        """Initialize serial with specific device."""
        transport = MeshtasticTransport(connection_type="serial", device="/dev/ttyUSB0")
        assert transport.connection_type == "serial"
        assert transport.device == "/dev/ttyUSB0"

    def test_init_ble(self):
        """Initialize with BLE connection type."""
        transport = MeshtasticTransport(connection_type="ble", device="AA:BB:CC:DD:EE:FF")
        assert transport.connection_type == "ble"
        assert transport.device == "AA:BB:CC:DD:EE:FF"

    def test_init_tcp(self):
        """Initialize with TCP connection type."""
        transport = MeshtasticTransport(connection_type="tcp", device="192.168.1.100")
        assert transport.connection_type == "tcp"
        assert transport.device == "192.168.1.100"

    def test_on_message_registers_callback(self):
        """on_message registers callback."""
        transport = MeshtasticTransport()
        callback = Mock()
        transport.on_message(callback)
        assert callback in transport._callbacks

    def test_multiple_callbacks_registered(self):
        """Multiple callbacks can be registered."""
        transport = MeshtasticTransport()
        cb1 = Mock()
        cb2 = Mock()
        transport.on_message(cb1)
        transport.on_message(cb2)
        assert cb1 in transport._callbacks
        assert cb2 in transport._callbacks

    @patch("meshtastic_gopher.transport.meshtastic_transport.serial_interface")
    def test_connect_serial(self, mock_serial):
        """Connect creates serial interface."""
        mock_interface = MagicMock()
        mock_serial.SerialInterface.return_value = mock_interface

        transport = MeshtasticTransport(connection_type="serial", device="/dev/ttyUSB0")
        transport.connect()

        mock_serial.SerialInterface.assert_called_once_with(devPath="/dev/ttyUSB0")
        assert transport._interface is mock_interface

    @patch("meshtastic_gopher.transport.meshtastic_transport.serial_interface")
    def test_connect_serial_auto_detect(self, mock_serial):
        """Connect serial with auto-detect (no device specified)."""
        mock_interface = MagicMock()
        mock_serial.SerialInterface.return_value = mock_interface

        transport = MeshtasticTransport(connection_type="serial")
        transport.connect()

        mock_serial.SerialInterface.assert_called_once_with(devPath=None)

    @patch("meshtastic_gopher.transport.meshtastic_transport.ble_interface")
    def test_connect_ble(self, mock_ble):
        """Connect creates BLE interface."""
        mock_interface = MagicMock()
        mock_ble.BLEInterface.return_value = mock_interface

        transport = MeshtasticTransport(connection_type="ble", device="AA:BB:CC:DD:EE:FF")
        transport.connect()

        mock_ble.BLEInterface.assert_called_once_with(address="AA:BB:CC:DD:EE:FF")

    @patch("meshtastic_gopher.transport.meshtastic_transport.tcp_interface")
    def test_connect_tcp(self, mock_tcp):
        """Connect creates TCP interface."""
        mock_interface = MagicMock()
        mock_tcp.TCPInterface.return_value = mock_interface

        transport = MeshtasticTransport(connection_type="tcp", device="192.168.1.100")
        transport.connect()

        mock_tcp.TCPInterface.assert_called_once_with(hostname="192.168.1.100")

    @patch("meshtastic_gopher.transport.meshtastic_transport.serial_interface")
    def test_disconnect(self, mock_serial):
        """Disconnect closes interface."""
        mock_interface = MagicMock()
        mock_serial.SerialInterface.return_value = mock_interface

        transport = MeshtasticTransport()
        transport.connect()
        transport.disconnect()

        mock_interface.close.assert_called_once()
        assert transport._interface is None

    def test_disconnect_when_not_connected(self):
        """Disconnect does nothing when not connected."""
        transport = MeshtasticTransport()
        transport.disconnect()  # Should not raise

    @patch("meshtastic_gopher.transport.meshtastic_transport.serial_interface")
    def test_send_message(self, mock_serial):
        """send transmits message to node."""
        mock_interface = MagicMock()
        mock_serial.SerialInterface.return_value = mock_interface

        transport = MeshtasticTransport()
        transport.connect()
        transport.send("!abcd1234", "Hello mesh!")

        mock_interface.sendText.assert_called_once()
        call_args = mock_interface.sendText.call_args
        assert call_args[0][0] == "Hello mesh!"
        assert call_args[1]["destinationId"] == "!abcd1234"

    def test_send_not_connected_raises(self):
        """send raises when not connected."""
        transport = MeshtasticTransport()
        with pytest.raises(RuntimeError):
            transport.send("!abcd1234", "Hello")

    @patch("meshtastic_gopher.transport.meshtastic_transport.serial_interface")
    def test_handle_received_message(self, mock_serial):
        """Received messages trigger callbacks."""
        mock_interface = MagicMock()
        mock_serial.SerialInterface.return_value = mock_interface

        transport = MeshtasticTransport()
        callback = Mock()
        transport.on_message(callback)
        transport.connect()

        # Simulate receiving a message
        packet = {
            "fromId": "!abcd1234",
            "decoded": {"text": "Hello server!"},
        }
        transport._handle_receive(packet, mock_interface)

        callback.assert_called_once_with("!abcd1234", "Hello server!")

    @patch("meshtastic_gopher.transport.meshtastic_transport.serial_interface")
    def test_handle_non_text_message_ignored(self, mock_serial):
        """Non-text messages are ignored."""
        mock_interface = MagicMock()
        mock_serial.SerialInterface.return_value = mock_interface

        transport = MeshtasticTransport()
        callback = Mock()
        transport.on_message(callback)
        transport.connect()

        # Simulate receiving a non-text packet (e.g., position)
        packet = {
            "fromId": "!abcd1234",
            "decoded": {"position": {"latitude": 0, "longitude": 0}},
        }
        transport._handle_receive(packet, mock_interface)

        callback.assert_not_called()

    @patch("meshtastic_gopher.transport.meshtastic_transport.serial_interface")
    def test_multiple_callbacks_called(self, mock_serial):
        """All registered callbacks are called on message."""
        mock_interface = MagicMock()
        mock_serial.SerialInterface.return_value = mock_interface

        transport = MeshtasticTransport()
        cb1 = Mock()
        cb2 = Mock()
        transport.on_message(cb1)
        transport.on_message(cb2)
        transport.connect()

        packet = {
            "fromId": "!abcd1234",
            "decoded": {"text": "Test"},
        }
        transport._handle_receive(packet, mock_interface)

        cb1.assert_called_once_with("!abcd1234", "Test")
        cb2.assert_called_once_with("!abcd1234", "Test")

    def test_is_connected_false_initially(self):
        """is_connected returns False before connect."""
        transport = MeshtasticTransport()
        assert transport.is_connected() is False

    @patch("meshtastic_gopher.transport.meshtastic_transport.serial_interface")
    def test_is_connected_true_after_connect(self, mock_serial):
        """is_connected returns True after connect."""
        mock_interface = MagicMock()
        mock_serial.SerialInterface.return_value = mock_interface

        transport = MeshtasticTransport()
        transport.connect()
        assert transport.is_connected() is True

    @patch("meshtastic_gopher.transport.meshtastic_transport.serial_interface")
    def test_is_connected_false_after_disconnect(self, mock_serial):
        """is_connected returns False after disconnect."""
        mock_interface = MagicMock()
        mock_serial.SerialInterface.return_value = mock_interface

        transport = MeshtasticTransport()
        transport.connect()
        transport.disconnect()
        assert transport.is_connected() is False
