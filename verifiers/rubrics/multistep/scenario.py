"""
Represents a scenario for evaluating multi-step rubrics.

Contains a prompt (initial situation description), completion (response),
and ground truth answer path for evaluation.
"""

from typing import Optional

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
