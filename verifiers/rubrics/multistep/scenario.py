"""
Represents a scenario for evaluating multi-step rubrics.

Contains a prompt (initial situation description), completion (response),
and ground truth answer path for evaluation.
"""

from pathlib import Path
from typing import List, Optional, Union

import yaml

# TODO: Scenario Generation from Full Description
# ================================================
#
# Vision: Instead of manually crafting prompt, answers, and revealed_info separately,
# scenarios should be generated from a single "full_description" field that contains
# the complete ground truth of what actually happened in the scenario.
#
# Proposed workflow:
# 1. Author writes a comprehensive full_description containing all scenario details:
#    - Environmental conditions and hazards
#    - Patient/subject status and history
#    - All relevant facts that would inform correct requirement answers
#    - Complete timeline of events
#
# 2. A model with full access to the rubric requirements would "devise" the scenario by:
#    - Extracting an appropriate initial prompt (limited information to start)
#    - Determining correct answers for each requirement based on the full description
#    - Generating revealed_info snippets that progressively unveil details from the
#      full description as requirements are satisfied
#
# Benefits:
# - Single source of truth eliminates manual alignment issues
# - Consistent ground truth across prompt, answers, and revealed info
# - Scalable for complex multi-branch workflows
# - Reduces human error in cross-referencing requirements
#
# Example:
# full_description = """
# A 34-year-old electrician was working on power lines when electrocuted and fell
# 12 feet onto concrete. Multiple active hazards present: live electrical wires
# down and sparking in 15-foot radius. Worker unconscious with visible burns on
# hands/arms, shallow irregular breathing, no pulse detected at wrist...
# """
#
# Model would derive:
# - prompt: "You arrive at a scene. A person is on the ground. Your view is limited."
# - answers: {"scene_safety": {"answer": 0.0, "reasoning": "Live electrical hazards"}}
# - revealed_info: {"scene_safety": "Live electrical wires sparking. Do not approach."}


class Scenario:
    """Holds the information for a single scenario, to be evaluated by a rubric."""

    def __init__(
        self,
        prompt: str,
        answers: Optional[dict[str, dict[str, float | str]]] = None,
        completion: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        revealed_info: Optional[dict[str, str]] = None,
        _hidden_description: Optional[str] = None,
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
                          Format: {"requirement_name": "information to reveal when correct"}
            _hidden_description: Optional full-information view of the entire scene and setup,
                               containing all ground truth details that could inform the correct
                               answers. This serves as the source of truth for generating
           
                               prompts, answers, and revealed_info.
        """
        self.prompt = prompt
        self.answers = answers
        self.completion = completion  # May be None if needs to be generated
        self.name = name
        self.description = description
        self.revealed_info = revealed_info or {}
        self._hidden_description = _hidden_description

        if self.revealed_info and self.answers:
            assert all(
                k in self.answers for k in self.revealed_info
            ), f"All revealed_info keys must be in answers; got revealed_info keys {list(self.revealed_info.keys())} but answers keys {list(self.answers.keys())}"

    def to_content(self) -> str:
        """Return a string of the content of the scenario."""
        content = f"""
        prompt: {self.prompt}
        completion: {self.completion}
        """.strip()

        if self._hidden_description:
            content += f"\n_hidden_description: {self._hidden_description}"

        return content

    def to_dict(self) -> dict:
        """Convert scenario to dictionary for serialization."""
        scenario_data = {
            "name": self.name,
            "description": self.description,
            "prompt": self.prompt,
            "completion": self.completion,
            "answers": self.answers,
            "revealed_info": self.revealed_info,
            "_hidden_description": self._hidden_description,
        }
        return scenario_data

    def save(self, file_path: Union[str, Path]) -> None:
        """
        Save this scenario to a YAML file.

        Args:
            file_path: Path to save the YAML file
        """
        scenario_data = self.to_dict()
        with open(file_path, "w") as f:
            yaml.dump(
                {"scenario": scenario_data}, f, default_flow_style=False, indent=2
            )

    @classmethod
    def load(cls, file_path: Union[str, Path]) -> "Scenario":
        """
        Load a scenario from a YAML file.

        Args:
            file_path: Path to the YAML file

        Returns:
            Scenario object
        """
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)

        scenario_data = data["scenario"]
        return cls(**scenario_data)

    @classmethod
    def save_multiple(
        cls, scenarios: List["Scenario"], file_path: Union[str, Path]
    ) -> None:
        """
        Save multiple scenarios to a YAML file.

        Args:
            scenarios: List of Scenario objects
            file_path: Path to save the YAML file
        """
        scenarios_data = [scenario.to_dict() for scenario in scenarios]
        with open(file_path, "w") as f:
            yaml.dump(
                {"scenarios": scenarios_data}, f, default_flow_style=False, indent=2
            )

    @classmethod
    def load_multiple(cls, file_path: Union[str, Path]) -> List["Scenario"]:
        """
        Load multiple scenarios from a YAML file.

        Args:
            file_path: Path to the YAML file

        Returns:
            List of Scenario objects
        """
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)

        scenarios_data = data["scenarios"]
        return [cls(**scenario_data) for scenario_data in scenarios_data]
