"""Configuration handling for the Meshtastic Gopher Server."""

from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class Config:
    """Configuration settings for the Gopher server.

    Attributes:
        root_directory: Directory containing gopher content.
        max_message_size: Maximum characters per message.
        auto_send_threshold: Pages threshold for auto-send vs pagination.
        connection_type: Meshtastic connection type (serial, ble, tcp).
        device: Device path, BLE address, or hostname.
        session_timeout_minutes: Session inactivity timeout.
    """

    root_directory: str = "~/gopher-content"
    max_message_size: int = 230
    auto_send_threshold: int = 3
    connection_type: str = "serial"
    device: str | None = None
    session_timeout_minutes: int = 30

    def get_root_path(self) -> Path:
        """Get root directory as expanded Path object."""
        return Path(self.root_directory).expanduser()


def load_config(path: str | Path) -> Config:
    """
    Load configuration from a YAML file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        Config object with loaded values.

    Raises:
        FileNotFoundError: If config file doesn't exist.
    """
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    # Extract sections
    gopher = data.get("gopher", {})
    meshtastic = data.get("meshtastic", {})
    session = data.get("session", {})

    return Config(
        root_directory=gopher.get("root_directory", Config.root_directory),
        max_message_size=gopher.get("max_message_size", Config.max_message_size),
        auto_send_threshold=gopher.get("auto_send_threshold", Config.auto_send_threshold),
        connection_type=meshtastic.get("connection_type", Config.connection_type),
        device=meshtastic.get("device", Config.device),
        session_timeout_minutes=session.get("timeout_minutes", Config.session_timeout_minutes),
    )
