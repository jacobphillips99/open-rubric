"""
Represents a scenario for evaluating multi-step rubrics.

Contains a prompt (situation description), completion (response),
and ground truth answer path for evaluation.
"""

from typing import Optional


class Scenario:
    """Holds the information for a single scenario, to be evaluated by a rubric."""

    def __init__(
        self,
        prompt: str,
        answers: Optional[dict[str, dict[str, float | str]]] = None,
        completion: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        revealed_info: Optional[dict[str, dict[str, str]]] = None,
    ):
        """
        Initialize a scenario with the given information.

        Args:
            prompt: The situation or question being presented
            completion: The response or actions taken
            answers: Ground truth path mapping requirement names to expected scores
            name: Optional name for the scenario
            description: Optional description of what this scenario tests
            revealed_info: Optional mapping of requirement names to revealed information
                          Format: {"requirement_name": {"1.0": "info when satisfied", "0.0": "info when not satisfied"}}
        """
        self.prompt = prompt
        self.answers = answers
        self.completion = completion  # May be None if needs to be generated
        self.name = name
        self.description = description
        self.revealed_info = revealed_info or {}

    def to_content(self) -> str:
        """Return a string of the content of the scenario."""
        return f"""
        prompt: {self.prompt}
        completion: {self.completion}
        """.strip()
