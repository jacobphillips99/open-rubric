"""
Requirement class for multistep rubrics.

Requirements are a core building block of a multistep rubrics -- they define the questions that are asked of a scenario, and the dependencies between them.
They host the question and the judge response format in order to select the next dependent requirement(s).
"""

from typing import Optional

from verifiers.rewards.judge_reward import (JudgeResponseFormat,
                                            binary_judge_response_format)


class Requirement:
    """
    Requirements are instantiated acording to a name, question, judge response format, and dependencies.
    The judge's response format is used to determine the next dependent requirement(s).
    """

    # TODO -- check depenedencies float???
    def __init__(
        self,
        name: str,
        question: str,
        judge_response_format: JudgeResponseFormat,
        dependencies: Optional[dict[float, list[str]]] = None,
    ):
        """Simple init for a requirement."""
        self.name = name
        self.question = question
        self.dependencies = dependencies
        self.judge_response_format = judge_response_format

        if dependencies is not None:
            assert all(d in judge_response_format.options for d in dependencies.keys())

    def terminal(self) -> bool:
        """A terminal requirement is one that has no dependencies."""
        return not bool(self.dependencies)


class BinaryRequirement(Requirement):
    """
    Helper class for binary requirements; they are the most common type of requirement.
    They have a binary response format (0.0 or 1.0) and use the binary judge response format.
    """

    def __init__(
        self,
        name: str,
        question: str,
        dependencies: Optional[dict[float, list[str]]] = None,
    ) -> None:
        super().__init__(name, question, binary_judge_response_format, dependencies)
