"""
Demo script for the new MultiStep Visualizers.

This demonstrates the visualization capabilities of the three specialized visualizers:
1. RequirementsVisualizer - For analyzing requirement dependencies
2. RubricVisualizer - For visualizing complete rubrics with nodes
3. CompletedRubricVisualizer - For visualizing evaluated rubrics with results
"""

from multistep_extras.example_rubrics import get_workflow
from multistep_extras.utils.print_utils import (print_debug, print_header,
                                                print_info, print_process,
                                                print_score, print_success)
from multistep_extras.visualization.visualizer import (
    CompletedRubricVisualizer, RequirementsVisualizer, RubricVisualizer,
    visualize_requirements)
from verifiers.rewards.judge_reward import JudgeRewarder
# For creating mock rubrics and evaluations
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.requirement import (BinaryRequirement,
                                                     Requirement)
from verifiers.rubrics.multistep.scenario import Scenario


class MockJudgeRewarder(JudgeRewarder):
    """Mock judge rewarder for demo purposes."""

    def __init__(self):
        """Initialize a simple mock judge for demo purposes."""
        self.model = "mock-judge-model"
        self.response_format = "binary"

    async def __call__(self, question: str, content: str, answer, **kwargs):
        """Return a mock judge response that always indicates correct for demo purposes."""
        from verifiers.rewards.judge_reward import JudgeResponse

        return JudgeResponse(answer=1.0, reasoning="Mock evaluation for demo purposes")


def create_simple_demo_requirements() -> list[Requirement]:
    """Create simple self-contained requirements for demo purposes."""
    return [
        BinaryRequirement(
            name="safety_check",
            question="Does the response consider safety first?",
            dependencies={1.0: ["initial_assessment"], 0.0: ["emergency_protocol"]},
        ),
        BinaryRequirement(
            name="initial_assessment",
            question="Does the response include initial assessment?",
            dependencies={1.0: ["terminal_action"], 0.0: ["emergency_protocol"]},
        ),
        BinaryRequirement(
            name="emergency_protocol",
            question="Does the response follow emergency protocols?",
        ),
        BinaryRequirement(
            name="terminal_action",
            question="Does the response include appropriate terminal actions?",
        ),
    ]


def demo_requirements_visualizer(
    name: str, reqs: list[Requirement], scenarios: list[Scenario]
):
    """Demonstrate the RequirementsVisualizer for pure requirement analysis."""
    print_header("📋 REQUIREMENTS VISUALIZER DEMO")
    print_info("Analyzing requirement dependencies and workflow structure.")
    print()

    # Start with simple, clear hierarchical requirements to show the concept
    print_process("🔍 Understanding Requirement Dependencies:")
    print_info(
        "Let's start with a simple example to understand how requirements connect..."
    )
    print()

    simple_reqs = create_simple_demo_requirements()
    simple_viz = RequirementsVisualizer(simple_reqs)
    simple_viz.print_workflow_structure()

    # Trace a path through the simple requirements
    print_process("📍 Evaluation Path Tracing:")
    print_info("When we provide answers, the visualizer shows which path gets taken:")
    sample_answers = {"safety_check": 1.0, "initial_assessment": 1.0}
    simple_viz.print_evaluation_path(sample_answers)
    print()

    # Now show the real workflow - use full requirements list to avoid dependency issues
    print_process(f"🚑 Real-World Example: {name.title()} Workflow:")
    print_info("Now let's see the complete real-world requirement structure...")
    print()

    # Show the full requirements list to avoid breaking dependency references
    visualize_requirements(reqs)


def demo_rubric_visualizer(name: str, reqs: list[Requirement]):
    """Demonstrate the RubricVisualizer for complete rubrics with nodes."""
    print_header("🏗️ RUBRIC VISUALIZER DEMO")
    print_info("Visualizing complete rubrics with nodes, judges, and strategies.")
    print()

    # Create a mock rubric with simple, self-contained requirements
    mock_judge = MockJudgeRewarder()
    simple_reqs = create_simple_demo_requirements()
    rubric = MultiStepRubric(simple_reqs, mock_judge)

    print_process("🔧 Simple Demo Rubric Configuration:")
    viz = RubricVisualizer(rubric)
    viz.print_complete_structure()


def demo_completed_rubric_visualizer(name: str = ""):
    """Demonstrate the CompletedRubricVisualizer for evaluated rubrics."""
    print_header("✅ COMPLETED RUBRIC VISUALIZER DEMO")
    print_info("Visualizing rubrics with actual evaluation results and judge feedback.")
    print()

    # Create demo scenario with consistent answers
    from verifiers.rubrics.multistep.scenario import Scenario

    demo_scenario = Scenario(
        name="Emergency Response Demo",
        description="A demonstration scenario showing proper emergency response evaluation",
        prompt="You encounter an emergency situation. What do you do?",
        completion="First, I ensure the scene is safe before proceeding. Then I conduct an initial assessment of the situation and take appropriate action following emergency protocols.",
        answers={
            "safety_check": {"answer": 1.0, "reasoning": "Safety is addressed first"},
            "initial_assessment": {
                "answer": 1.0,
                "reasoning": "Assessment is mentioned",
            },
            "terminal_action": {
                "answer": 1.0,
                "reasoning": "Appropriate action is taken",
            },
            "emergency_protocol": {
                "answer": 1.0,
                "reasoning": "Emergency protocols mentioned",
            },
        },
    )

    # Create consistent mock results organized by evaluation levels
    # Level 0: Root requirements (safety_check)
    # Level 1: Next level requirements (initial_assessment)
    # Level 2: Terminal requirements (terminal_action, emergency_protocol)
    mock_results = {
        "0": {  # Level 0 - Root requirements
            "safety_check": {
                "answer": 1.0,
                "reasoning": "Response appropriately considers safety as the first priority",
            }
        },
        "1": {  # Level 1 - Next level after safety_check passes
            "initial_assessment": {
                "answer": 1.0,
                "reasoning": "Response includes appropriate initial assessment steps",
            }
        },
        "2": {  # Level 2 - Terminal requirements
            "terminal_action": {
                "answer": 1.0,
                "reasoning": "Response concludes with appropriate terminal actions",
            },
            "emergency_protocol": {
                "answer": 1.0,
                "reasoning": "Response mentions following emergency protocols",
            },
        },
    }

    mock_judge = MockJudgeRewarder()
    simple_reqs = create_simple_demo_requirements()
    rubric = MultiStepRubric(simple_reqs, mock_judge)

    print_process("🔍 Evaluated Scenario Results:")
    print_info("This shows how the visualizer displays actual evaluation outcomes...")
    print()
    viz = CompletedRubricVisualizer(rubric, demo_scenario, mock_results)
    viz.print_complete_evaluation()


def demo_advanced_features(
    name: str, reqs: list[Requirement], scenarios: list[Scenario]
):
    """Demonstrate advanced features of each visualizer."""
    print_header("🔬 ADVANCED ANALYSIS FEATURES")
    print_info("Deep-dive into workflow metrics and complexity analysis.")
    print()

    # Advanced RequirementsVisualizer features
    print_process("📊 Workflow Complexity Metrics:")
    viz = RequirementsVisualizer(reqs)
    metrics = viz.analyze_metrics()

    print_score("📈 Key Workflow Characteristics:")
    print_info(f"  • Depth: {metrics['max_depth']} levels deep")
    print_info(
        f"  • Branching: {metrics['avg_branching_factor']:.1f} average branches per node"
    )
    print_info(
        f"  • Terminal ratio: {metrics['terminal_nodes']}/{metrics['total_requirements']} nodes ({metrics['terminal_nodes'] / metrics['total_requirements'] * 100:.1f}%)"
    )
    print_info(f"  • Connectivity: {metrics['total_edges']} dependency relationships")
    print()

    # Show dependency complexity with better context
    print_process("🔗 Dependency Complexity Analysis:")
    complex_nodes = []
    simple_nodes = []

    for req in reqs:
        if req.dependencies and len(req.dependencies) > 2:
            complex_nodes.append(req.name)
        elif req.dependencies and len(req.dependencies) > 0:
            simple_nodes.append(req.name)

    if complex_nodes:
        print_info(
            f"🔀 Multi-branch nodes ({len(complex_nodes)}): {', '.join(complex_nodes[:3])}{'...' if len(complex_nodes) > 3 else ''}"
        )
    if simple_nodes:
        print_debug(
            f"🔗 Simple branch nodes ({len(simple_nodes)}): {', '.join(simple_nodes[:3])}{'...' if len(simple_nodes) > 3 else ''}"
        )

    if not complex_nodes and not simple_nodes:
        print_debug(
            "📋 This workflow uses mostly terminal requirements (simple structure)"
        )

    print()
    print_process("💡 Workflow Insights:")

    if metrics["max_depth"] > 4:
        print_info("🏗️  Deep workflow - good for complex multi-stage processes")
    elif metrics["max_depth"] > 2:
        print_info("⚖️  Moderate depth - balanced structure")
    else:
        print_info("📋 Flat structure - good for independent criteria")

    if metrics["avg_branching_factor"] > 1.5:
        print_info("🌳 High branching - lots of conditional paths")
    else:
        print_info("🔗 Linear flow - more predictable evaluation paths")


def run_full_demo():
    """Run the complete visualization demo showcasing all three visualizers."""
    workflow_name = "first_responder"
    requirements, scenarios = get_workflow(workflow_name)

    demo_requirements_visualizer(workflow_name, requirements, scenarios)
    demo_rubric_visualizer(workflow_name, requirements)
    demo_completed_rubric_visualizer()
    demo_advanced_features(workflow_name, requirements, scenarios)

    print_success("🎉 DEMO JOURNEY COMPLETE!")


if __name__ == "__main__":
    run_full_demo()
