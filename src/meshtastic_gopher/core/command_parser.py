"""Command parser for interpreting user input."""

from abc import ABC
from dataclasses import dataclass


class Command(ABC):
    """Base class for all commands."""

    pass


@dataclass(frozen=True)
class SelectCommand(Command):
    """Command to select an item by number."""

    index: int


@dataclass(frozen=True)
class BackCommand(Command):
    """Command to go back to parent directory."""

    pass


@dataclass(frozen=True)
class NextCommand(Command):
    """Command to get the next page of content."""

    pass


@dataclass(frozen=True)
class HomeCommand(Command):
    """Command to go to the root directory."""

    pass


@dataclass(frozen=True)
class HelpCommand(Command):
    """Command to display help information."""

    pass


@dataclass(frozen=True)
class InvalidCommand(Command):
    """Represents an invalid or unrecognized command."""

    original_input: str
    reason: str = "Unknown command"


class CommandParser:
    """Parses user input strings into Command objects."""

    # Maximum valid selection number (menus won't have 100+ items)
    MAX_SELECTION = 99

    # Command mappings
    BACK_COMMANDS = {"b", "back"}
    NEXT_COMMANDS = {"n", "next"}
    HOME_COMMANDS = {"h", "home"}
    HELP_COMMANDS = {"?", "help"}

    def parse(self, input_str: str) -> Command:
        """
        Parse a user input string into a Command object.

        Args:
            input_str: The raw input string from the user.

        Returns:
            A Command object representing the parsed input.
        """
        # Normalize input
        cleaned = input_str.strip().lower()

        if not cleaned:
            return InvalidCommand(
                original_input=input_str, reason="Empty input"
            )

        # Check for navigation commands
        if cleaned in self.BACK_COMMANDS:
            return BackCommand()

        if cleaned in self.NEXT_COMMANDS:
            return NextCommand()

        if cleaned in self.HOME_COMMANDS:
            return HomeCommand()

        if cleaned in self.HELP_COMMANDS:
            return HelpCommand()

        # Try to parse as number
        try:
            number = int(cleaned)
            if number < 1:
                return InvalidCommand(
                    original_input=input_str,
                    reason="Selection must be positive",
                )
            if number > self.MAX_SELECTION:
                return InvalidCommand(
                    original_input=input_str,
                    reason=f"Selection must be <= {self.MAX_SELECTION}",
                )
            return SelectCommand(index=number)
        except ValueError:
            pass

        return InvalidCommand(
            original_input=input_str, reason="Unknown command"
        )
