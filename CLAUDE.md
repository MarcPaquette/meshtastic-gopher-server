# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Test Commands

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/test_command_parser.py -v

# Run a specific test
pytest tests/test_command_parser.py::TestCommandParser::test_parse_single_digit_number -v

# Run with coverage
pytest --cov=meshtastic_gopher --cov-report=term-missing

# Run the server (requires Meshtastic device)
meshtastic-gopher -r ~/gopher-content --serial
```

## Architecture

This is a Gopher-like server for Meshtastic mesh networks. Users navigate directories and view files via numbered menus sent over mesh radio, with a ~230 character message limit.

### Core Design Pattern

The project uses **dependency injection** following SOLID principles. `GopherServer` (in `server.py`) is the main orchestrator that accepts abstract interfaces:

```
GopherServer
    ├── ContentProvider (interface) → FilesystemProvider (implementation)
    ├── MessageTransport (interface) → MeshtasticTransport (implementation)
    └── Core components (CommandParser, ContentChunker, MenuRenderer, SessionManager)
```

### Key Abstractions

- **`ContentProvider`** (`interfaces/content_provider.py`): ABC for content access. Implement this to serve content from sources other than filesystem.
- **`MessageTransport`** (`interfaces/message_transport.py`): ABC for message send/receive. Implement this for transports other than Meshtastic.

### Session Management

- `Session` (`core/session.py`): Immutable dataclass tracking per-node state (current path, pagination, directory listing). All mutations return new Session instances.
- `SessionManager` (`core/session_manager.py`): Maps node IDs to Sessions with timeout-based cleanup.

### Message Flow

1. `MeshtasticTransport` receives message → calls registered callback
2. `GopherServer._handle_message()` gets/creates session for node
3. `CommandParser` parses input into Command objects (SelectCommand, BackCommand, etc.)
4. `GopherServer._process_command()` executes command, returns (response, updated_session)
5. `ContentChunker` splits long content into 230-char chunks with `[1/3]` page indicators
6. Response sent via transport

### Important Constraint

Meshtastic messages are limited to ~230 characters. The `ContentChunker` handles this by splitting content at word boundaries and adding page indicators. The `auto_send_threshold` config controls when to auto-send all pages vs. require user to send 'n' for next page.
