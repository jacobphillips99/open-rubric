"""
Inspection utilities for MultiStep Rubric workflows.

This module provides tools to inspect workflow structures, dependencies,
and evaluation paths to help users understand complex rubrics.
"""

# Legacy aliases for backward compatibility
from .inspector import (CompletedRubricVisualizer, EvaluationInspector,
                        RequirementsInspector, RequirementsVisualizer,
                        RubricInspector, RubricVisualizer,
                        compare_requirements, inspect_requirements,
                        visualize_requirements)

__all__ = [
    # New naming convention
    "RequirementsInspector",
    "RubricInspector",
    "EvaluationInspector",
    "inspect_requirements",
    "compare_requirements",
    # Legacy aliases for backward compatibility
    "RequirementsVisualizer",
    "RubricVisualizer",
    "CompletedRubricVisualizer",
    "visualize_requirements",
]
