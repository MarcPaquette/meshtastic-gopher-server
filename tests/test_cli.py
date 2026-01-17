"""Tests for the CLI module."""

import argparse
import logging
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from meshtastic_gopher.cli import setup_logging, parse_args, main


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_default_level_is_info(self):
        """Default logging level is INFO."""
        with patch("logging.basicConfig") as mock_config:
            setup_logging(verbose=False)
            mock_config.assert_called_once()
            assert mock_config.call_args[1]["level"] == logging.INFO

    def test_verbose_level_is_debug(self):
        """Verbose logging level is DEBUG."""
        with patch("logging.basicConfig") as mock_config:
            setup_logging(verbose=True)
            mock_config.assert_called_once()
            assert mock_config.call_args[1]["level"] == logging.DEBUG


class TestParseArgs:
    """Tests for parse_args function."""

    def test_no_args(self):
        """No arguments uses defaults."""
        with patch("sys.argv", ["meshtastic-gopher"]):
            args = parse_args()
            assert args.config is None
            assert args.root is None
            assert args.verbose is False
            assert args.serial is None
            assert args.ble is None
            assert args.tcp is None

    def test_config_file(self):
        """--config specifies config file."""
        with patch("sys.argv", ["meshtastic-gopher", "-c", "config.yaml"]):
            args = parse_args()
            assert args.config == "config.yaml"

    def test_root_directory(self):
        """--root specifies content directory."""
        with patch("sys.argv", ["meshtastic-gopher", "-r", "/path/to/content"]):
            args = parse_args()
            assert args.root == "/path/to/content"

    def test_verbose_flag(self):
        """--verbose enables verbose mode."""
        with patch("sys.argv", ["meshtastic-gopher", "-v"]):
            args = parse_args()
            assert args.verbose is True

    def test_serial_auto_detect(self):
        """--serial without port uses auto-detect."""
        with patch("sys.argv", ["meshtastic-gopher", "--serial"]):
            args = parse_args()
            assert args.serial == "auto"

    def test_serial_specific_port(self):
        """--serial with port uses specific port."""
        with patch("sys.argv", ["meshtastic-gopher", "--serial", "/dev/ttyUSB0"]):
            args = parse_args()
            assert args.serial == "/dev/ttyUSB0"

    def test_ble_connection(self):
        """--ble specifies BLE address."""
        with patch("sys.argv", ["meshtastic-gopher", "--ble", "AA:BB:CC:DD:EE:FF"]):
            args = parse_args()
            assert args.ble == "AA:BB:CC:DD:EE:FF"

    def test_tcp_connection(self):
        """--tcp specifies host."""
        with patch("sys.argv", ["meshtastic-gopher", "--tcp", "192.168.1.100"]):
            args = parse_args()
            assert args.tcp == "192.168.1.100"

    def test_connection_options_mutually_exclusive(self):
        """Connection options are mutually exclusive."""
        with patch("sys.argv", ["meshtastic-gopher", "--serial", "--ble", "AA:BB"]):
            with pytest.raises(SystemExit):
                parse_args()


class TestMain:
    """Tests for main function."""

    @pytest.fixture
    def temp_content(self, tmp_path):
        """Create temporary content directory."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "test.txt").write_text("Hello")
        return content_dir

    def test_config_file_not_found(self, tmp_path):
        """Returns 1 when config file not found."""
        with patch("sys.argv", ["meshtastic-gopher", "-c", "/nonexistent/config.yaml"]):
            result = main()
            assert result == 1

    def test_content_directory_not_found(self, tmp_path):
        """Returns 1 when content directory doesn't exist."""
        with patch("sys.argv", ["meshtastic-gopher", "-r", "/nonexistent/content"]):
            result = main()
            assert result == 1

    def test_content_path_not_directory(self, tmp_path):
        """Returns 1 when content path is a file, not directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("not a directory")

        with patch("sys.argv", ["meshtastic-gopher", "-r", str(file_path)]):
            result = main()
            assert result == 1

    @patch("meshtastic_gopher.cli.signal.signal")
    @patch("meshtastic_gopher.cli.signal.pause")
    @patch("meshtastic_gopher.cli.MeshtasticTransport")
    @patch("meshtastic_gopher.cli.GopherServer")
    def test_serial_auto_detect_config(self, mock_server, mock_transport, mock_pause, mock_signal, temp_content):
        """--serial without port sets device to None for auto-detect."""
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance

        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance

        # Make pause raise to exit the main loop
        mock_pause.side_effect = Exception("exit")

        with patch("sys.argv", ["meshtastic-gopher", "-r", str(temp_content), "--serial"]):
            main()

        mock_transport.assert_called_once_with(
            connection_type="serial",
            device=None,
        )

    @patch("meshtastic_gopher.cli.signal.signal")
    @patch("meshtastic_gopher.cli.signal.pause")
    @patch("meshtastic_gopher.cli.MeshtasticTransport")
    @patch("meshtastic_gopher.cli.GopherServer")
    def test_serial_specific_port_config(self, mock_server, mock_transport, mock_pause, mock_signal, temp_content):
        """--serial with port sets device to that port."""
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance

        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance

        mock_pause.side_effect = Exception("exit")

        with patch("sys.argv", ["meshtastic-gopher", "-r", str(temp_content), "--serial", "/dev/ttyUSB0"]):
            main()

        mock_transport.assert_called_once_with(
            connection_type="serial",
            device="/dev/ttyUSB0",
        )

    @patch("meshtastic_gopher.cli.signal.signal")
    @patch("meshtastic_gopher.cli.signal.pause")
    @patch("meshtastic_gopher.cli.MeshtasticTransport")
    @patch("meshtastic_gopher.cli.GopherServer")
    def test_ble_connection_config(self, mock_server, mock_transport, mock_pause, mock_signal, temp_content):
        """--ble sets connection type and device."""
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance

        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance

        mock_pause.side_effect = Exception("exit")

        with patch("sys.argv", ["meshtastic-gopher", "-r", str(temp_content), "--ble", "AA:BB:CC:DD:EE:FF"]):
            main()

        mock_transport.assert_called_once_with(
            connection_type="ble",
            device="AA:BB:CC:DD:EE:FF",
        )

    @patch("meshtastic_gopher.cli.signal.signal")
    @patch("meshtastic_gopher.cli.signal.pause")
    @patch("meshtastic_gopher.cli.MeshtasticTransport")
    @patch("meshtastic_gopher.cli.GopherServer")
    def test_tcp_connection_config(self, mock_server, mock_transport, mock_pause, mock_signal, temp_content):
        """--tcp sets connection type and device."""
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance

        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance

        mock_pause.side_effect = Exception("exit")

        with patch("sys.argv", ["meshtastic-gopher", "-r", str(temp_content), "--tcp", "192.168.1.100"]):
            main()

        mock_transport.assert_called_once_with(
            connection_type="tcp",
            device="192.168.1.100",
        )

    @patch("meshtastic_gopher.cli.signal.signal")
    @patch("meshtastic_gopher.cli.signal.pause")
    @patch("meshtastic_gopher.cli.MeshtasticTransport")
    @patch("meshtastic_gopher.cli.GopherServer")
    def test_config_file_loading(self, mock_server, mock_transport, mock_pause, mock_signal, temp_content, tmp_path):
        """Config file is loaded and used."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(f"""
gopher:
  root_directory: {temp_content}
  max_message_size: 150
meshtastic:
  connection_type: tcp
  device: 10.0.0.1
""")

        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance

        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance

        mock_pause.side_effect = Exception("exit")

        with patch("sys.argv", ["meshtastic-gopher", "-c", str(config_file)]):
            main()

        mock_transport.assert_called_once_with(
            connection_type="tcp",
            device="10.0.0.1",
        )

    @patch("meshtastic_gopher.cli.signal.signal")
    @patch("meshtastic_gopher.cli.signal.pause")
    @patch("meshtastic_gopher.cli.MeshtasticTransport")
    @patch("meshtastic_gopher.cli.GopherServer")
    def test_command_line_overrides_config(self, mock_server, mock_transport, mock_pause, mock_signal, temp_content, tmp_path):
        """Command line arguments override config file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(f"""
gopher:
  root_directory: {temp_content}
meshtastic:
  connection_type: tcp
  device: 10.0.0.1
""")

        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance

        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance

        mock_pause.side_effect = Exception("exit")

        # Command line --serial should override config file's tcp
        with patch("sys.argv", ["meshtastic-gopher", "-c", str(config_file), "--serial", "/dev/ttyUSB1"]):
            main()

        mock_transport.assert_called_once_with(
            connection_type="serial",
            device="/dev/ttyUSB1",
        )

    @patch("meshtastic_gopher.cli.MeshtasticTransport")
    def test_transport_init_failure(self, mock_transport, temp_content):
        """Returns 1 when transport initialization fails."""
        mock_transport.side_effect = Exception("Connection failed")

        with patch("sys.argv", ["meshtastic-gopher", "-r", str(temp_content)]):
            result = main()
            assert result == 1

    @patch("meshtastic_gopher.cli.signal.signal")
    @patch("meshtastic_gopher.cli.signal.pause")
    @patch("meshtastic_gopher.cli.MeshtasticTransport")
    @patch("meshtastic_gopher.cli.GopherServer")
    def test_server_start_failure(self, mock_server, mock_transport, mock_pause, mock_signal, temp_content):
        """Returns 1 when server start fails."""
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance

        mock_server_instance = MagicMock()
        mock_server_instance.start.side_effect = Exception("Start failed")
        mock_server.return_value = mock_server_instance

        with patch("sys.argv", ["meshtastic-gopher", "-r", str(temp_content)]):
            result = main()
            assert result == 1

        # Server should be stopped even on failure
        mock_server_instance.stop.assert_called_once()

    @patch("meshtastic_gopher.cli.signal.signal")
    @patch("meshtastic_gopher.cli.signal.pause")
    @patch("meshtastic_gopher.cli.MeshtasticTransport")
    @patch("meshtastic_gopher.cli.GopherServer")
    def test_root_override(self, mock_server, mock_transport, mock_pause, mock_signal, temp_content, tmp_path):
        """--root overrides config root_directory."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
gopher:
  root_directory: /some/other/path
""")

        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance

        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance

        mock_pause.side_effect = Exception("exit")

        with patch("sys.argv", ["meshtastic-gopher", "-c", str(config_file), "-r", str(temp_content)]):
            main()

        # The server should have been created (not failed due to bad path)
        mock_server.assert_called_once()

    @patch("meshtastic_gopher.cli.signal.signal")
    @patch("meshtastic_gopher.cli.signal.pause")
    @patch("meshtastic_gopher.cli.MeshtasticTransport")
    @patch("meshtastic_gopher.cli.GopherServer")
    def test_server_stop_called_on_exit(self, mock_server, mock_transport, mock_pause, mock_signal, temp_content):
        """Server stop is called in finally block."""
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance

        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance

        mock_pause.side_effect = Exception("exit")

        with patch("sys.argv", ["meshtastic-gopher", "-r", str(temp_content)]):
            main()

        mock_server_instance.stop.assert_called_once()
