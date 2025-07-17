"""
Generic test utilities for multistep testing.

This module contains reusable print utilities and test scenario functions
that can be shared across multiple test files.
"""

from multistep_extras.example_rubrics import \
    first_responder_advanced_scenarios as ADVANCED_SCENARIOS
from verifiers.rubrics.multistep.scenario import Scenario


# Color codes for terminal output
class Colors:
    HEADER = "\033[95m"  # Magenta
    BLUE = "\033[94m"  # Blue
    CYAN = "\033[96m"  # Cyan
    GREEN = "\033[92m"  # Green
    YELLOW = "\033[93m"  # Yellow
    RED = "\033[91m"  # Red
    BOLD = "\033[1m"  # Bold
    UNDERLINE = "\033[4m"  # Underline
    END = "\033[0m"  # End formatting

    # Semantic colors
    SUCCESS = GREEN
    ERROR = RED
    STATE = YELLOW
    ASSISTANT = CYAN
    ENVIRONMENT = BLUE
    INFO = "\033[37m"  # White
    RUBRIC = "\033[35m"  # Purple
    SCORE = "\033[32m"  # Bright Green
    REWARD = "\033[33m"  # Orange-ish
    DEBUG = "\033[90m"  # Dark Gray


def print_header(text: str) -> None:
    """Print a colored header."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{text}{Colors.END}")


def print_section(text: str) -> None:
    """Print a section divider."""
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * len(text)}{Colors.END}")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.SUCCESS}SUCCESS: {text}{Colors.END}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.ERROR}ERROR: {text}{Colors.END}")


def print_state(text: str) -> None:
    """Print state information."""
    print(f"{Colors.STATE}STATE: {text}{Colors.END}")


def print_assistant(text: str) -> None:
    """Print assistant message."""
    print(f"{Colors.ASSISTANT}ASSISTANT: {text}{Colors.END}")


def print_environment(text: str) -> None:
    """Print environment message."""
    print(f"{Colors.ENVIRONMENT}ENVIRONMENT: {text}{Colors.END}")


def print_info(text: str) -> None:
    """Print general information."""
    print(f"{Colors.INFO}INFO: {text}{Colors.END}")


def print_process(text: str) -> None:
    """Print process/action information."""
    print(f"{Colors.BLUE}PROCESS: {text}{Colors.END}")


def print_rubric(text: str) -> None:
    """Print rubric-related information."""
    print(f"{Colors.RUBRIC}RUBRIC: {text}{Colors.END}")


def print_score(text: str) -> None:
    """Print scoring information."""
    print(f"{Colors.SCORE}SCORE: {text}{Colors.END}")


def print_reward(text: str) -> None:
    """Print reward information."""
    print(f"{Colors.REWARD}REWARD: {text}{Colors.END}")


def print_debug(text: str) -> None:
    """Print debug information."""
    print(f"{Colors.DEBUG}DEBUG: {text}{Colors.END}")
