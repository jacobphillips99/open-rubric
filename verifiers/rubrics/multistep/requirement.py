"""
Requirement class for multistep rubrics.

Requirements are a core building block of a multistep rubrics -- they define the questions that are asked of a scenario, and the dependencies between them.
They host the question and the judge response format in order to select the next dependent requirement(s).
"""

from typing import Any, Optional

from verifiers.rewards.judge_utils import (JudgeResponseFormat,
                                           binary_judge_response_format,
                                           unit_vector_judge_response_format)


class Requirement:
    """
    Instantiate requirements according to a name, question, judge response format, and dependencies.
    The judge's response format is used to determine the next dependent requirement(s).
    """

    def __init__(
        self,
        name: str,
        question: str,
        judge_response_format: JudgeResponseFormat,
        dependencies: Optional[dict[float, list[str]]] = None,
    ):
        """
        Initialize a requirement with name, question, judge format, and dependencies.

        Args:
            name: Unique identifier for this requirement
            question: The question to be evaluated
            judge_response_format: Format for judge responses
            dependencies: Optional dict mapping answers to dependent requirements
        """
        self.name = name
        self.question = question
        self.dependencies = dependencies
        self.judge_response_format = judge_response_format

    def validate_dependencies(self) -> None:
        """Validate the dependencies for this requirement."""
        raise NotImplementedError(
            "validate_dependencies not implemented for base class"
        )

    def terminal(self) -> bool:
        """Check if requirement is terminal, meaning it has no dependencies."""
        return not bool(self.dependencies)

    def get_dependencies_from_answer(self, answer: Any) -> list[str]:
        """Get the dependencies for this requirement based on the answer."""
        raise NotImplementedError(
            "get_dependencies_from_answer not implemented for base class"
        )


class DiscreteRequirement(Requirement):
    """
    Create discrete requirements with discrete choices for dependency options.
    They are the most common type of requirement and use the discrete judge response formats, like binary.
    """

    def validate_dependencies(self) -> None:
        """Validate the dependencies for this requirement."""
        if self.dependencies is not None:
            assert all(
                d in self.judge_response_format.options
                for d in self.dependencies.keys()
            )

    def get_dependencies_from_answer(self, answer: Any) -> list[str]:
        """Get the dependencies for this requirement based on the answer."""
        if self.dependencies is None:
            return []
        elif answer not in self.dependencies:
            raise ValueError(
                f"Answer {answer} not in dependencies for requirement {self.name}. Found dependencies: {self.dependencies.keys()}"
            )
        return self.dependencies[answer]


class ContinuousRequirement(Requirement):
    """
    Create continuous requirements with continuous choices for dependency options.
    Dependency options are selected by the closest answer to the judge's response.
    """

    def validate_dependencies(self) -> None:
        """Validate the dependencies for this requirement."""
        if self.dependencies is not None:
            assert all(
                self.judge_response_format.options[0]
                <= d
                <= self.judge_response_format.options[1]
                for d in self.dependencies.keys()
            )

    def get_dependencies_from_answer(self, answer: Any) -> list[str]:
        """Get the dependencies for this requirement based on the answer."""
        if self.dependencies is None:
            return []
        elif answer not in self.dependencies:
            raise ValueError(
                f"Answer {answer} not in dependencies for requirement {self.name}. Found dependencies: {self.dependencies.keys()}"
            )
        # determine which dependency key is closest to the answer
        closest_key = min(self.dependencies.keys(), key=lambda x: abs(x - answer))
        return self.dependencies[closest_key]


class BinaryRequirement(DiscreteRequirement):
    """
    Create binary requirements with binary response format (0.0 or 1.0).
    They are the most common type of requirement and use the binary judge response format.
    """

    def __init__(
        self,
        name: str,
        question: str,
        dependencies: Optional[dict[float, list[str]]] = None,
    ) -> None:
        """
        Initialize a binary requirement.

        Args:
            name: Unique identifier for this requirement
            question: The question to be evaluated
            dependencies: Optional dict mapping binary answers to dependent requirements
        """
        super().__init__(name, question, binary_judge_response_format, dependencies)


class UnitVectorRequirement(ContinuousRequirement):
    """
    Create unit vector requirements with unit vector response format (0.0 or 1.0).
    They are the most common type of requirement and use the unit vector judge response format.
    """

    def __init__(
        self,
        name: str,
        question: str,
        dependencies: Optional[dict[float, list[str]]] = None,
        **kwargs,
    ):
        """
        Initialize a unit vector requirement.

        Args:
            name: Unique identifier for this requirement
            question: The question to be evaluated
            dependencies: Optional dict mapping unit vector answers to dependent requirements
        """
        super().__init__(
            name, question, unit_vector_judge_response_format, dependencies, **kwargs
        )
