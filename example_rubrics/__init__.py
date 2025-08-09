"""
Example workflows for the MultiStep Rubric system.

This module contains complete example workflows with requirements and scenarios
for different domains, showcasing the versatility of the multistep evaluation system.
"""

import typing as t

from verifiers.rubrics.multistep.requirement import Requirement
from verifiers.rubrics.multistep.scenario import Scenario

# Import debugging example
from .debugging import requirements as debugging_requirements
from .debugging import scenarios as debugging_scenarios
# Import first responder example
from .first_responder import \
    advanced_scenarios as first_responder_advanced_scenarios
from .first_responder import requirements as first_responder_requirements
from .first_responder import scenarios as first_responder_scenarios

# Legacy aliases for backward compatibility
first_responder_reqs = first_responder_requirements
scenarios = first_responder_scenarios
debugging_reqs = debugging_requirements
debugging_scenarios = debugging_scenarios

# Combined scenarios from all examples
all_scenarios = first_responder_scenarios + debugging_scenarios

# Available workflow examples
AVAILABLE_WORKFLOWS: dict[str, dict[str, t.Any]] = {
    "first_responder": {
        "name": "First Responder Emergency Medical Response",
        "description": "Wide-branching workflow for emergency medical situations with parallel assessments",
        "requirements": first_responder_requirements,
        "scenarios": first_responder_scenarios,
        "advanced_scenarios": first_responder_advanced_scenarios,
    },
    "debugging": {
        "name": "Software Debugging Investigation",
        "description": "Sequential workflow for systematic software problem investigation",
        "requirements": debugging_requirements,
        "scenarios": debugging_scenarios,
        "advanced_scenarios": [],
    },
}


def get_workflow(
    name: str, advanced: bool = False
) -> tuple[list[Requirement], list[Scenario]]:
    """
    Get a workflow by name.

    Args:
        name: Name of the workflow ('first_responder' or 'debugging')
        advanced: Whether to return advanced scenarios (default: False)
    Returns:
        Dictionary containing workflow information

    Raises:
        KeyError: If workflow name is not found
    """
    if name not in AVAILABLE_WORKFLOWS:
        available = ", ".join(AVAILABLE_WORKFLOWS.keys())
        raise KeyError(f"Workflow '{name}' not found. Available workflows: {available}")

    reqs = AVAILABLE_WORKFLOWS[name]["requirements"]
    if advanced:
        scenarios = AVAILABLE_WORKFLOWS[name]["advanced_scenarios"]
    else:
        scenarios = AVAILABLE_WORKFLOWS[name]["scenarios"]
    return reqs, scenarios


def list_workflows() -> list[str]:
    """
    List all available workflow names.

    Returns:
        List of workflow names
    """
    return list(AVAILABLE_WORKFLOWS.keys())


def get_workflow_summary() -> str:
    """
    Get a summary of all available workflows.

    Returns:
        Formatted string describing all workflows
    """
    summary = "Available Workflow Examples:\n"
    summary += "=" * 50 + "\n"

    for name, info in AVAILABLE_WORKFLOWS.items():
        summary += f"\n{name.upper()}:\n"
        summary += f"  Name: {info['name']}\n"
        summary += f"  Description: {info['description']}\n"
        summary += f"  Requirements: {len(info['requirements'])}\n"
        summary += f"  Scenarios: {len(info['scenarios'])}\n"
        summary += f"  Structure: {info['characteristics']['structure']}\n"
        summary += f"  Domain: {info['characteristics']['domain']}\n"

    return summary


# Export everything
__all__ = [
    # Individual workflow components
    "first_responder_requirements",
    "first_responder_scenarios",
    "debugging_requirements",
    "debugging_scenarios",
    # Legacy aliases
    "first_responder_reqs",
    "scenarios",
    "debugging_reqs",
    "debugging_scenarios",
    # Combined data
    "all_scenarios",
    # Workflow registry
    "AVAILABLE_WORKFLOWS",
    "get_workflow",
    "list_workflows",
    "get_workflow_summary",
]
