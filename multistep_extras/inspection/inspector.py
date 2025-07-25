"""
Inspection utilities for MultiStep Rubric workflows.

This module provides three specialized inspectors for different use cases:
1. RequirementsInspector - For analyzing requirement dependencies
2. RubricInspector - For inspecting complete rubrics with nodes
3. EvaluationInspector - For inspecting evaluated rubrics with results
"""

from typing import List, Tuple

from verifiers.rubrics.multistep.requirement import Requirement
from .base_inspector import (BaseEvaluationInspector,
                             BaseRequirementsInspector, BaseRubricInspector)


class RequirementsInspector(BaseRequirementsInspector):
    """Inspector focused on requirement dependencies and workflow structure."""

    pass


class RubricInspector(BaseRubricInspector):
    """Inspector for complete MultiStepRubric with nodes and judge rewarders."""

    pass


class EvaluationInspector(BaseEvaluationInspector):
    """Inspector for rubrics that have been evaluated with results."""

    pass


# Convenience functions for backward compatibility and easy usage
def inspect_requirements(requirements: List[Requirement]) -> None:
    """
    Inspect requirement dependencies and structure.

    Args:
        requirements: List of requirement objects
    """
    inspector = RequirementsInspector(requirements)
    inspector.print_dependency_graph()
    inspector.print_workflow_structure()
    inspector.print_metrics()


def compare_requirements(
    workflow1: List[Requirement],
    workflow2: List[Requirement],
    names: Tuple[str, str] = ("Workflow 1", "Workflow 2"),
) -> None:
    """
    Compare two requirement workflows side by side.

    Args:
        workflow1: First workflow requirements
        workflow2: Second workflow requirements
        names: Names for the workflows
    """
    print(f"COMPARING REQUIREMENTS: {names[0]} vs {names[1]}")
    print("=" * 80)

    inspector1 = RequirementsInspector(workflow1)
    inspector2 = RequirementsInspector(workflow2)

    metrics1 = inspector1.analyze_metrics()
    metrics2 = inspector2.analyze_metrics()

    print(f"{'Metric':<25} {names[0]:<20} {names[1]:<20}")
    print("-" * 65)

    comparison_metrics = [
        "total_requirements",
        "terminal_nodes",
        "branching_nodes",
        "multi_branch_nodes",
        "max_depth",
        "avg_branching_factor",
        "total_edges",
    ]

    for metric in comparison_metrics:
        val1 = metrics1[metric]
        val2 = metrics2[metric]

        if isinstance(val1, float):
            print(f"{metric:<25} {val1:<20.2f} {val2:<20.2f}")
        else:
            print(f"{metric:<25} {val1:<20} {val2:<20}")
    print()


# Legacy function aliases for backward compatibility
def visualize_requirements(requirements: List[Requirement]) -> None:
    """
    Legacy alias for inspect_requirements. Use inspect_requirements instead.

    Args:
        requirements: List of requirement objects
    """
    inspect_requirements(requirements)


# Legacy class aliases for backward compatibility
RequirementsVisualizer = RequirementsInspector
RubricVisualizer = RubricInspector
CompletedRubricVisualizer = EvaluationInspector
