"""
Requirement class for multistep rubrics.

Requirements are a core building block of a multistep rubrics -- they define the questions that are asked of a scenario, and the dependencies between them.
They host the question and the judge response format in order to select the next dependent requirement(s).
"""

from pathlib import Path
from typing import Any, List, Optional, Union

import yaml

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

    def to_dict(self) -> dict:
        """Convert requirement to dictionary for serialization."""
        return {
            "name": self.name,
            "question": self.question,
            "type": self.__class__.__name__.replace("Requirement", "").lower(),
            "dependencies": self.dependencies,
            "judge_response_format": self.judge_response_format.to_dict(),
        }

    def save(self, file_path: Union[str, Path]) -> None:
        """
        Save this requirement to a YAML file.

        Args:
            file_path: Path to save the YAML file
        """
        req_data = self.to_dict()
        with open(file_path, "w") as f:
            yaml.dump({"requirement": req_data}, f, default_flow_style=False, indent=2)

    @classmethod
    def save_multiple(
        cls, requirements: List["Requirement"], file_path: Union[str, Path]
    ) -> None:
        """
        Save multiple requirements to a YAML file.

        Args:
            requirements: List of Requirement objects
            file_path: Path to save the YAML file
        """
        requirements_data = [req.to_dict() for req in requirements]
        with open(file_path, "w") as f:
            yaml.dump(
                {"requirements": requirements_data},
                f,
                default_flow_style=False,
                indent=2,
            )

    @classmethod
    def load_multiple(cls, file_path: Union[str, Path]) -> List["Requirement"]:
        """
        Load multiple requirements from a YAML file.

        Args:
            file_path: Path to the YAML file

        Returns:
            List of Requirement objects
        """
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)

        requirements_data = data["requirements"]
        return make_requirements(requirements_data)


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


NAME_TO_REQUIREMENT_CLASS = {
    "binary": BinaryRequirement,
    "unit_vector": UnitVectorRequirement,
    "discrete": DiscreteRequirement,
    "continuous": ContinuousRequirement,
}


def make_requirement(type: str, **kwargs) -> Requirement:
    """Make a requirement based on the type."""
    # Filter out judge_response_format for requirement types that set it automatically
    base_types = ["discrete", "continuous"]
    if type not in base_types:
        kwargs.pop("judge_response_format", None)
    return NAME_TO_REQUIREMENT_CLASS[type](**kwargs)


def make_requirements(requirements: list[dict]) -> list[Requirement]:
    """Make a list of requirements based on the requirements."""
    result = []
    for r in requirements:
        # Create a copy without the 'type' key to avoid conflicts
        kwargs = {k: v for k, v in r.items() if k != "type"}
        result.append(make_requirement(r["type"], **kwargs))
    return result
