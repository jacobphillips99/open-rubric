"""
Demo and tutorial utilities for the MultiStep Rubric system.

This module provides interactive demos and tutorials to help users
understand and work with multistep workflows.
"""

from .demo_builder import (demo_branching_template, demo_fluent_builder,
                           demo_linear_template, demo_quick_helpers,
                           demo_scenario_builder)
from .demo_builder import run_full_demo as run_builder_demo
from .demo_visualizer import (demo_all_possible_paths,
                              demo_debugging_visualization,
                              demo_first_responder_visualization,
                              demo_workflow_comparison)
from .demo_visualizer import run_full_demo as run_visualizer_demo
from .demo_workflow_registry import (demo_error_handling, demo_workflow_access,
                                     demo_workflow_registry)
from .demo_workflow_registry import run_full_demo as run_registry_demo
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
    "demo_first_responder_visualization",
    "demo_debugging_visualization",
    "demo_workflow_comparison",
    "demo_all_possible_paths",
    "run_visualizer_demo",
    # Registry demos
    "demo_workflow_registry",
    "demo_workflow_access",
    "demo_error_handling",
    "run_registry_demo",
    # Tutorial
    "MultiStepTutorial",
]
