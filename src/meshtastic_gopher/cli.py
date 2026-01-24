"""Command-line interface for the Meshtastic Gopher Server."""

import argparse
import logging
import signal
import sys
from dataclasses import replace

from .config import Config, load_config
from .providers import FilesystemProvider
from .transport import MeshtasticTransport
from .server import GopherServer


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Meshtastic Gopher Server - Serve content over mesh radio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Use default config
  %(prog)s -c config.yaml           # Use specific config file
  %(prog)s -r ~/gopher-content      # Specify content directory
  %(prog)s --serial /dev/ttyUSB0    # Use specific serial port
  %(prog)s --ble AA:BB:CC:DD:EE:FF  # Use Bluetooth device
  %(prog)s --tcp 192.168.1.100      # Use TCP connection
""",
    )

    parser.add_argument(
        "-c", "--config",
        metavar="FILE",
        help="Path to YAML configuration file",
    )

    parser.add_argument(
        "-r", "--root",
        metavar="DIR",
        help="Root directory for gopher content",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    # Connection options (mutually exclusive)
    conn_group = parser.add_mutually_exclusive_group()
    conn_group.add_argument(
        "--serial",
        metavar="PORT",
        nargs="?",
        const="auto",
        help="Use serial connection (default: auto-detect)",
    )
    conn_group.add_argument(
        "--ble",
        metavar="ADDRESS",
        help="Use Bluetooth LE connection",
    )
    conn_group.add_argument(
        "--tcp",
        metavar="HOST",
        help="Use TCP connection",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)

    # Load configuration
    if args.config:
        try:
            config = load_config(args.config)
        except FileNotFoundError:
            logger.error(f"Config file not found: {args.config}")
            return 1
    else:
        config = Config()

    # Override config with command line arguments
    if args.root:
        config = replace(config, root_directory=args.root)

    if args.serial is not None:
        device = None if args.serial == "auto" else args.serial
        config = replace(config, connection_type="serial", device=device)
    elif args.ble:
        config = replace(config, connection_type="ble", device=args.ble)
    elif args.tcp:
        config = replace(config, connection_type="tcp", device=args.tcp)

    # Validate root directory
    root_path = config.get_root_path()
    if not root_path.exists():
        logger.error(f"Content directory does not exist: {root_path}")
        logger.info("Create the directory and add some content, or specify a different path with -r")
        return 1

    if not root_path.is_dir():
        logger.error(f"Content path is not a directory: {root_path}")
        return 1

    # Create components
    try:
        provider = FilesystemProvider(root_path)
        transport = MeshtasticTransport(
            connection_type=config.connection_type,
            device=config.device,
        )
        server = GopherServer(provider, transport, config)
    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        return 1

    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start server
    logger.info("Starting Gopher server...")
    logger.info(f"  Content directory: {root_path}")
    logger.info(f"  Connection: {config.connection_type}" + (f" ({config.device})" if config.device else ""))
    logger.info(f"  Max message size: {config.max_message_size}")

    try:
        server.start()
        logger.info("Server running. Press Ctrl+C to stop.")

        # Keep running
        signal.pause()

    except Exception as e:
        logger.error(f"Server error: {e}")
        return 1
    finally:
        server.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
