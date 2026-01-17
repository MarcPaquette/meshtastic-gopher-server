"""Tests for the CommandParser module."""

import pytest
from meshtastic_gopher.core.command_parser import (
    CommandParser,
    Command,
    SelectCommand,
    BackCommand,
    NextCommand,
    AllCommand,
    HomeCommand,
    HelpCommand,
    InvalidCommand,
)


class TestCommandParser:
    """Tests for CommandParser."""

    @pytest.fixture
    def parser(self):
        """Create a CommandParser instance."""
        return CommandParser()

    def test_parse_single_digit_number(self, parser):
        """Parsing a single digit returns SelectCommand."""
        cmd = parser.parse("2")
        assert isinstance(cmd, SelectCommand)
        assert cmd.index == 2

    def test_parse_double_digit_number(self, parser):
        """Parsing a double digit number returns SelectCommand."""
        cmd = parser.parse("15")
        assert isinstance(cmd, SelectCommand)
        assert cmd.index == 15

    def test_parse_number_with_whitespace(self, parser):
        """Parsing number with leading/trailing whitespace works."""
        cmd = parser.parse("  7  ")
        assert isinstance(cmd, SelectCommand)
        assert cmd.index == 7

    def test_parse_zero_is_invalid(self, parser):
        """Zero is not a valid selection."""
        cmd = parser.parse("0")
        assert isinstance(cmd, InvalidCommand)

    def test_parse_negative_is_invalid(self, parser):
        """Negative numbers are invalid."""
        cmd = parser.parse("-5")
        assert isinstance(cmd, InvalidCommand)

    def test_parse_back_lowercase(self, parser):
        """'b' returns BackCommand."""
        cmd = parser.parse("b")
        assert isinstance(cmd, BackCommand)

    def test_parse_back_uppercase(self, parser):
        """'B' returns BackCommand."""
        cmd = parser.parse("B")
        assert isinstance(cmd, BackCommand)

    def test_parse_back_word(self, parser):
        """'back' returns BackCommand."""
        cmd = parser.parse("back")
        assert isinstance(cmd, BackCommand)

    def test_parse_next_lowercase(self, parser):
        """'n' returns NextCommand."""
        cmd = parser.parse("n")
        assert isinstance(cmd, NextCommand)

    def test_parse_next_uppercase(self, parser):
        """'N' returns NextCommand."""
        cmd = parser.parse("N")
        assert isinstance(cmd, NextCommand)

    def test_parse_next_word(self, parser):
        """'next' returns NextCommand."""
        cmd = parser.parse("next")
        assert isinstance(cmd, NextCommand)

    def test_parse_all_lowercase(self, parser):
        """'a' returns AllCommand."""
        cmd = parser.parse("a")
        assert isinstance(cmd, AllCommand)

    def test_parse_all_uppercase(self, parser):
        """'A' returns AllCommand."""
        cmd = parser.parse("A")
        assert isinstance(cmd, AllCommand)

    def test_parse_all_word(self, parser):
        """'all' returns AllCommand."""
        cmd = parser.parse("all")
        assert isinstance(cmd, AllCommand)

    def test_parse_home_lowercase(self, parser):
        """'h' returns HomeCommand."""
        cmd = parser.parse("h")
        assert isinstance(cmd, HomeCommand)

    def test_parse_home_uppercase(self, parser):
        """'H' returns HomeCommand."""
        cmd = parser.parse("H")
        assert isinstance(cmd, HomeCommand)

    def test_parse_home_word(self, parser):
        """'home' returns HomeCommand."""
        cmd = parser.parse("home")
        assert isinstance(cmd, HomeCommand)

    def test_parse_help_question_mark(self, parser):
        """'?' returns HelpCommand."""
        cmd = parser.parse("?")
        assert isinstance(cmd, HelpCommand)

    def test_parse_help_word(self, parser):
        """'help' returns HelpCommand."""
        cmd = parser.parse("help")
        assert isinstance(cmd, HelpCommand)

    def test_parse_empty_string(self, parser):
        """Empty string returns InvalidCommand."""
        cmd = parser.parse("")
        assert isinstance(cmd, InvalidCommand)

    def test_parse_whitespace_only(self, parser):
        """Whitespace only returns InvalidCommand."""
        cmd = parser.parse("   ")
        assert isinstance(cmd, InvalidCommand)

    def test_parse_unknown_command(self, parser):
        """Unknown command returns InvalidCommand."""
        cmd = parser.parse("xyz")
        assert isinstance(cmd, InvalidCommand)
        assert "xyz" in cmd.original_input

    def test_parse_number_too_large(self, parser):
        """Numbers > 99 are invalid (menu won't have that many items)."""
        cmd = parser.parse("100")
        assert isinstance(cmd, InvalidCommand)

    def test_command_equality(self):
        """Commands with same data are equal."""
        cmd1 = SelectCommand(index=5)
        cmd2 = SelectCommand(index=5)
        assert cmd1 == cmd2

    def test_command_inequality(self):
        """Commands with different data are not equal."""
        cmd1 = SelectCommand(index=5)
        cmd2 = SelectCommand(index=6)
        assert cmd1 != cmd2

    def test_different_command_types_not_equal(self):
        """Different command types are not equal."""
        cmd1 = SelectCommand(index=1)
        cmd2 = BackCommand()
        assert cmd1 != cmd2
