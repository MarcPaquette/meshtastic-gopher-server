# Meshtastic Gopher Server

A Gopher-like server for Meshtastic mesh networks. Navigate directories and view text files using simple numbered menus over mesh radio.

## Features

- **Menu-driven navigation** - Browse directories using numbered selections
- **Per-node sessions** - Each Meshtastic node has independent navigation state
- **Smart pagination** - Long content is split into ~200 character chunks to fit Meshtastic's message limits
- **ACK-based delivery** - Reliable message delivery with acknowledgment waiting and retry logic
- **Multiple connection types** - Serial/USB, Bluetooth LE, and TCP support
- **Filesystem-based content** - Serve any directory structure as gopher content

## Installation

```bash
# Clone the repository
git clone https://github.com/MarcPaquette/meshtastic-gopher-server.git
cd meshtastic-gopher-server

# Install with pip
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

## Quick Start

1. Create a content directory:
```bash
mkdir -p ~/gopher-content
echo "Welcome to my Gopher server!" > ~/gopher-content/welcome.txt
mkdir ~/gopher-content/documents
echo "This is a sample document." > ~/gopher-content/documents/readme.txt
```

2. Connect your Meshtastic device via USB and run:
```bash
meshtastic-gopher -r ~/gopher-content --serial
```

3. From another Meshtastic node, send any message to see the root directory listing, then use the commands below to navigate.

## User Commands

| Command | Description |
|---------|-------------|
| `1-99` | Select a numbered item |
| `b` or `back` | Go back to parent directory |
| `h` or `home` | Return to root directory |
| `n` or `next` | Show next page of content |
| `a` or `all` | Send all remaining pages |
| `?` or `help` | Display help message |

## Example Session

```
User sends: (any message)
Server responds:
  [/]
  1. documents/
  2. welcome.txt

User sends: 1
Server responds:
  [/documents]
  1. readme.txt

User sends: 1
Server responds:
  This is a sample document.

User sends: b
Server responds:
  [/documents]
  1. readme.txt

User sends: h
Server responds:
  [/]
  1. documents/
  2. welcome.txt
```

## Connection Options

```bash
# Serial - auto-detect device
meshtastic-gopher -r ~/gopher-content --serial

# Serial - specific port
meshtastic-gopher -r ~/gopher-content --serial /dev/ttyUSB0

# Bluetooth LE
meshtastic-gopher -r ~/gopher-content --ble AA:BB:CC:DD:EE:FF

# TCP/WiFi
meshtastic-gopher -r ~/gopher-content --tcp 192.168.1.100
```

## Configuration

You can use a YAML configuration file instead of command-line arguments:

```bash
meshtastic-gopher -c config.yaml
```

Example `config.yaml`:
```yaml
gopher:
  root_directory: ~/gopher-content
  max_message_size: 200
  auto_send_threshold: 3   # pages before requiring 'n' for next
  ack_timeout_seconds: 30  # timeout waiting for message ACK

meshtastic:
  connection_type: serial  # serial, ble, or tcp
  device: /dev/ttyUSB0     # or BLE address, or hostname

session:
  timeout_minutes: 30
```

See `config.example.yaml` for a full example.

## CLI Options

```
usage: meshtastic-gopher [-h] [-c FILE] [-r DIR] [-v]
                         [--serial [PORT] | --ble ADDRESS | --tcp HOST]

options:
  -h, --help            Show help message
  -c FILE, --config FILE
                        Path to YAML configuration file
  -r DIR, --root DIR    Root directory for gopher content
  -v, --verbose         Enable verbose logging
  --serial [PORT]       Use serial connection (default: auto-detect)
  --ble ADDRESS         Use Bluetooth LE connection
  --tcp HOST            Use TCP connection
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=meshtastic_gopher --cov-report=term-missing

# Run specific test file
pytest tests/test_command_parser.py -v
```

### Project Structure

```
src/meshtastic_gopher/
├── cli.py                  # Command-line interface
├── config.py               # Configuration handling
├── server.py               # Main GopherServer orchestrator
├── interfaces/             # Abstract base classes
│   ├── content_provider.py # ABC for content access
│   └── message_transport.py# ABC for messaging
├── providers/
│   └── filesystem_provider.py  # Filesystem content provider
├── transport/
│   └── meshtastic_transport.py # Meshtastic Serial/BLE/TCP
└── core/
    ├── command_parser.py   # Parse user input
    ├── content_chunker.py  # Split content into chunks
    ├── menu_renderer.py    # Render directory listings
    ├── session.py          # Per-node session state
    └── session_manager.py  # Manage multiple sessions
```

### Architecture

The project follows SOLID principles:

- **Single Responsibility**: Each class has one job
- **Open/Closed**: Extend via new providers or transports without modifying existing code
- **Liskov Substitution**: Any `ContentProvider` implementation works interchangeably
- **Interface Segregation**: Small, focused abstract base classes
- **Dependency Inversion**: `GopherServer` depends on abstractions, not concrete implementations

## License

MIT License
