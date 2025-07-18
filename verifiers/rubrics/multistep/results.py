"""Evaluation result classes for multistep rubric evaluation."""

from typing import Any, Dict, Optional, Set

from verifiers.rubrics.multistep.enums import TerminalCondition


class EvaluationResult:
    """Result of evaluating requirements with terminal condition handling."""

    def __init__(
        self,
        state: Dict[str, Any],
        terminal_condition: TerminalCondition,
        completed_requirements: Optional[Set[str]] = None,
        total_requirements: Optional[int] = None,
    ):
        """
        Initialize an evaluation result.

        Args:
            state: The current evaluation state
            terminal_condition: The terminal condition that was reached
            completed_requirements: Set of completed requirement names
            total_requirements: Total number of requirements being evaluated
        """
        self.state = state
        self.terminal_condition = terminal_condition
        self.completed_requirements = completed_requirements or set()
        self.total_requirements = total_requirements or len(self.completed_requirements)

    @property
    def completion_ratio(self) -> float:
        """Calculate the ratio of completed requirements to total requirements."""
        if self.total_requirements == 0:
            return 1.0
        return len(self.completed_requirements) / self.total_requirements

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the evaluation result to a dictionary representation.

        Returns:
            Dict containing the state, terminal condition, completed requirements, and completion ratio
        """
        return {
            "state": self.state,
            "terminal_condition": self.terminal_condition.value,
            "completed_requirements": list(self.completed_requirements),
            "completion_ratio": self.completion_ratio,
        }
