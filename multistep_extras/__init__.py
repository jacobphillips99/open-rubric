"""TODO FIXME - holds the extras for the multistep rubric system."""

from .builders import RubricBuilder, ScenarioBuilder
from .demos import MultiStepTutorial, run_inspector_demo, run_visualizer_demo
from .example_rubrics import (AVAILABLE_WORKFLOWS, all_scenarios,
                              debugging_reqs, debugging_scenarios,
                              first_responder_reqs, get_workflow,
                              get_workflow_summary, list_workflows, scenarios)
# Legacy aliases for backward compatibility
from .inspection import (EvaluationInspector, RequirementsInspector,
                         RubricInspector, inspect_requirements)
from .visualization import (CompletedRubricVisualizer, RequirementsVisualizer,
                            RubricVisualizer, visualize_requirements)

__all__ = [
    # Builders
    "RubricBuilder",
    "ScenarioBuilder",
    # Example Rubrics
    "AVAILABLE_WORKFLOWS",
    "all_scenarios",
    "debugging_reqs",
    "debugging_scenarios",
    "first_responder_reqs",
    "get_workflow",
    "get_workflow_summary",
    "list_workflows",
    "scenarios",
    # Inspection (new naming)
    "RequirementsInspector",
    "RubricInspector",
    "EvaluationInspector",
    "inspect_requirements",
    # Legacy aliases for backward compatibility
    "RequirementsVisualizer",
    "RubricVisualizer",
    "CompletedRubricVisualizer",
    "visualize_requirements",
    # Demos
    "MultiStepTutorial",
    "run_inspector_demo",
    # Legacy demo alias
    "run_visualizer_demo",
]
