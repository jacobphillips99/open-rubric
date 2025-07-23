"""
Demo and tutorial utilities for the MultiStep Rubric system.

This module provides interactive demos and tutorials to help users
understand and work with multistep workflows.
"""

from .demo_inspector import run_full_demo as run_inspector_demo
from .tutorial import MultiStepTutorial

# Legacy alias for backward compatibility
run_visualizer_demo = run_inspector_demo

__all__ = [
    # Builder demos
    "demo_fluent_builder",
    "demo_linear_template",
    "demo_branching_template",
    "demo_quick_helpers",
    "demo_scenario_builder",
    "run_builder_demo",
    # Inspector demos (new naming)
    "run_inspector_demo", 
    # Legacy alias for backward compatibility
    "run_visualizer_demo",
    # Tutorial
    "MultiStepTutorial",
]
