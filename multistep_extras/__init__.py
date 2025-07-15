"""TODO FIXME - holds the extras for the multistep rubric system."""

from .builders import (BranchingWorkflowTemplate, LinearWorkflowTemplate,
                       ScenarioBuilder, WorkflowBuilder, WorkflowNode,
                       quick_scenario, quick_workflow)
from .demos import (MultiStepTutorial, create_progressive_scenario,
                    demo_all_possible_paths, demo_branching_template,
                    demo_debugging_visualization, demo_error_handling,
                    demo_first_responder_visualization, demo_fluent_builder,
                    demo_linear_template, demo_progressive_revelation,
                    demo_quick_helpers, demo_scenario_builder,
                    demo_workflow_access, demo_workflow_comparison,
                    demo_workflow_registry, run_builder_demo,
                    run_registry_demo, run_visualizer_demo)
from .example_rubrics import (AVAILABLE_WORKFLOWS, all_scenarios,
                              debugging_reqs, debugging_scenarios,
                              first_responder_reqs, get_workflow,
                              get_workflow_summary, list_workflows, scenarios)
from .visualization import (WorkflowVisualizer, compare_workflows,
                            visualize_workflow)

__all__ = [
    # Builders
    "BranchingWorkflowTemplate",
    "LinearWorkflowTemplate",
    "ScenarioBuilder",
    "WorkflowBuilder",
    "WorkflowNode",
    "quick_scenario",
    "quick_workflow",
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
    # Visualization
    "WorkflowVisualizer",
    "compare_workflows",
    "visualize_workflow",
    # Demos
    "MultiStepTutorial",
    "create_progressive_scenario",
    "demo_all_possible_paths",
    "demo_branching_template",
    "demo_debugging_visualization",
    "demo_error_handling",
    "demo_first_responder_visualization",
    "demo_fluent_builder",
    "demo_linear_template",
    "demo_progressive_revelation",
    "demo_quick_helpers",
    "demo_scenario_builder",
    "demo_workflow_access",
    "demo_workflow_comparison",
    "demo_workflow_registry",
    "run_builder_demo",
    "run_registry_demo",
    "run_visualizer_demo",
]
