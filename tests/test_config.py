"""Tests for the configuration module."""

import pytest
import tempfile
from pathlib import Path
from meshtastic_gopher.config import Config, load_config


class TestConfig:
    """Tests for Config dataclass."""

    def test_default_values(self):
        """Config has sensible defaults."""
        config = Config()
        assert config.root_directory == "~/gopher-content"
        assert config.max_message_size == 230
        assert config.auto_send_threshold == 3
        assert config.connection_type == "serial"
        assert config.device is None
        assert config.session_timeout_minutes == 30

    def test_custom_values(self):
        """Config accepts custom values."""
        config = Config(
            root_directory="/custom/path",
            max_message_size=200,
            auto_send_threshold=5,
            connection_type="ble",
            device="AA:BB:CC:DD:EE:FF",
            session_timeout_minutes=60,
        )
        assert config.root_directory == "/custom/path"
        assert config.max_message_size == 200
        assert config.connection_type == "ble"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_from_yaml_file(self):
        """Load config from YAML file."""
        yaml_content = """
gopher:
  root_directory: /tmp/gopher
  max_message_size: 220
  auto_send_threshold: 4

meshtastic:
  connection_type: tcp
  device: 192.168.1.100

session:
  timeout_minutes: 45
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            config = load_config(f.name)

            assert config.root_directory == "/tmp/gopher"
            assert config.max_message_size == 220
            assert config.auto_send_threshold == 4
            assert config.connection_type == "tcp"
            assert config.device == "192.168.1.100"
            assert config.session_timeout_minutes == 45

    def test_load_partial_config(self):
        """Load config with partial values (rest use defaults)."""
        yaml_content = """
gopher:
  root_directory: /tmp/test
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            config = load_config(f.name)

            assert config.root_directory == "/tmp/test"
            # Rest should be defaults
            assert config.max_message_size == 230
            assert config.connection_type == "serial"

    def test_load_empty_file(self):
        """Load config from empty file uses defaults."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()

            config = load_config(f.name)

            assert config.root_directory == "~/gopher-content"
            assert config.max_message_size == 230

    def test_load_nonexistent_file_raises(self):
        """Loading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")

    def test_expand_home_directory(self):
        """Home directory is expanded in root_directory."""
        yaml_content = """
gopher:
  root_directory: ~/my-gopher
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            config = load_config(f.name)
            expanded = config.get_root_path()

            assert "~" not in str(expanded)
            assert expanded.name == "my-gopher"

    def test_get_root_path_returns_path_object(self):
        """get_root_path returns Path object."""
        config = Config(root_directory="/tmp/test")
        path = config.get_root_path()
        assert isinstance(path, Path)
        assert str(path) == "/tmp/test"
