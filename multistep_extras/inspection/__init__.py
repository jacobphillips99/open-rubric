"""
Inspection utilities for MultiStep Rubric workflows.

This module provides tools to inspect workflow structures, dependencies,
and evaluation paths to help users understand complex rubrics.
"""

from .inspector import (EvaluationInspector, RequirementsInspector,
                        RubricInspector, inspect_requirements, compare_requirements)

# Legacy aliases for backward compatibility
from .inspector import (RequirementsVisualizer, RubricVisualizer, 
                       CompletedRubricVisualizer, visualize_requirements)

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