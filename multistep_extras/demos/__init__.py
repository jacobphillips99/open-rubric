"""
Demo and tutorial utilities for the MultiStep Rubric system.

This module provides interactive demos and tutorials to help users
understand and work with multistep workflows.
"""

from .demo_builder import (demo_branching_template, demo_fluent_builder,
                           demo_linear_template, demo_quick_helpers,
                           demo_scenario_builder)
from .demo_builder import run_full_demo as run_builder_demo
from .demo_visualizer import run_full_demo as run_visualizer_demo
from .tutorial import MultiStepTutorial

__all__ = [
    # Builder demos
    "demo_fluent_builder",
    "demo_linear_template",
    "demo_branching_template",
    "demo_quick_helpers",
    "demo_scenario_builder",
    "run_builder_demo",
    # Visualizer demos
    "run_visualizer_demo",
    # Tutorial
    "MultiStepTutorial",
]
