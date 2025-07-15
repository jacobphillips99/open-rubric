"""
Demo script for the WorkflowVisualizer.

This demonstrates the visualization capabilities of the multistep rubric system.
"""

from multistep_extras.example_rubrics import (debugging_reqs,
                                              debugging_scenarios,
                                              first_responder_reqs, scenarios)
from multistep_extras.visualization import (WorkflowVisualizer,
                                            compare_workflows)


def demo_first_responder_visualization():
    """Demonstrate visualization of the first responder workflow."""
    print("🚑 FIRST RESPONDER WORKFLOW VISUALIZATION")
    print("=" * 60)

    visualizer = WorkflowVisualizer(first_responder_reqs)

    # Show structure
    visualizer.print_workflow_structure()

    # Show metrics
    visualizer.print_workflow_metrics()

    # Show dependency graph
    visualizer.print_dependency_graph()

    # Trace evaluation path for the first scenario
    scenario = scenarios[0]
    answers = {name: data["answer"] for name, data in scenario.answers.items()}
    visualizer.print_evaluation_path(answers)


def demo_debugging_visualization():
    """Demonstrate visualization of the debugging workflow."""
    print("\n💻 SOFTWARE DEBUGGING WORKFLOW VISUALIZATION")
    print("=" * 60)

    visualizer = WorkflowVisualizer(debugging_reqs)

    # Show structure
    visualizer.print_workflow_structure()

    # Show metrics
    visualizer.print_workflow_metrics()

    # Trace evaluation path for debugging scenario
    scenario = debugging_scenarios[0]
    answers = {name: data["answer"] for name, data in scenario.answers.items()}
    visualizer.print_evaluation_path(answers)


def demo_workflow_comparison():
    """Demonstrate workflow comparison."""
    print("\n⚖️  WORKFLOW COMPARISON")
    print("=" * 60)

    compare_workflows(
        first_responder_reqs, debugging_reqs, ("First Responder", "Software Debugging")
    )


def demo_all_possible_paths():
    """Show all possible paths through workflows."""
    print("\n🛤️  ALL POSSIBLE PATHS")
    print("=" * 60)

    print("First Responder Workflow Paths:")
    print("-" * 40)
    visualizer1 = WorkflowVisualizer(first_responder_reqs)
    visualizer1.print_all_possible_paths(max_paths=10)

    print("Debugging Workflow Paths:")
    print("-" * 40)
    visualizer2 = WorkflowVisualizer(debugging_reqs)
    visualizer2.print_all_possible_paths(max_paths=10)


def run_full_demo():
    """Run the complete visualization demo."""
    print("🎭 MULTISTEP WORKFLOW VISUALIZER DEMO")
    print("=" * 60)
    print(
        "This demo showcases the visualization capabilities of the multistep rubric system.\n"
    )

    demo_first_responder_visualization()
    demo_debugging_visualization()
    demo_workflow_comparison()
    demo_all_possible_paths()

    print("\n✨ DEMO COMPLETE!")
    print("You've seen:")
    print("✓ Workflow structure visualization")
    print("✓ Dependency graph display")
    print("✓ Workflow metrics analysis")
    print("✓ Evaluation path tracing")
    print("✓ Side-by-side workflow comparison")
    print("✓ All possible paths enumeration")


if __name__ == "__main__":
    run_full_demo()
