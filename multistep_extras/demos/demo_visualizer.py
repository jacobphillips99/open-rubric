"""
Demo script for the new MultiStep Visualizers.

This demonstrates the visualization capabilities of the three specialized visualizers:
1. RequirementsVisualizer - For analyzing requirement dependencies
2. RubricVisualizer - For visualizing complete rubrics with nodes
3. CompletedRubricVisualizer - For visualizing evaluated rubrics with results
"""

from multistep_extras.example_rubrics import get_workflow
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
        """ Simple init for demo purposes."""
        self.model = "mock-judge-model"
        self.response_format = "binary"

    async def __call__(self, question: str, content: str, answer, **kwargs):
        """Mock judge that returns correct for demo purposes."""
        from verifiers.rewards.judge_reward import JudgeResponse

        return JudgeResponse(answer=1.0, reasoning="Mock evaluation for demo purposes")


def create_simple_demo_requirements():
    """Create a simple, self-contained set of requirements for demo purposes."""
    # Create terminal requirements first
    terminal_req1 = BinaryRequirement(
        name="terminal_action",
        question="Does the response include appropriate terminal actions?",
    )

    terminal_req2 = BinaryRequirement(
        name="emergency_protocol",
        question="Does the response follow emergency protocols?",
    )

    # Create branching requirements that depend only on terminal ones
    assessment_req = BinaryRequirement(
        name="initial_assessment",
        question="Does the response include initial assessment?",
        dependencies={1.0: ["terminal_action"], 0.0: ["emergency_protocol"]},
    )

    # Create root requirement
    safety_req = BinaryRequirement(
        name="safety_check",
        question="Does the response consider safety first?",
        dependencies={1.0: ["initial_assessment"], 0.0: ["emergency_protocol"]},
    )

    return [safety_req, assessment_req, terminal_req1, terminal_req2]


def demo_requirements_visualizer(
    name, reqs: list[Requirement], scenarios: list[Scenario]
):
    """Demonstrate the RequirementsVisualizer for pure requirement analysis."""
    print("📋 REQUIREMENTS VISUALIZER DEMO")
    print("=" * 70)
    print("Analyzing requirement dependencies and workflow structure only.\n")

    # Use a smaller, self-contained subset for demo
    print(f"🚑 {name} Requirements (sample):")
    print("-" * 40)
    # Just use the first few terminal requirements to avoid dependency issues
    sample_requirements = [req for req in reqs if req.terminal()][:3]
    visualize_requirements(sample_requirements)

    # Show evaluation path tracing with simple requirements
    print("\n🔍 Demo with Simple Self-Contained Requirements:")
    print("-" * 50)
    simple_reqs = create_simple_demo_requirements()
    simple_viz = RequirementsVisualizer(simple_reqs)
    simple_viz.print_workflow_structure()

    # Trace a path through the simple requirements
    sample_answers = {"safety_check": 1.0, "initial_assessment": 1.0}
    simple_viz.print_evaluation_path(sample_answers)


def demo_rubric_visualizer():
    """Demonstrate the RubricVisualizer for complete rubrics with nodes."""
    print("\n🏗️ RUBRIC VISUALIZER DEMO")
    print("=" * 70)
    print("Visualizing complete rubrics with nodes, judges, and strategies.\n")

    # Create a mock rubric with simple, self-contained requirements
    mock_judge = MockJudgeRewarder()
    simple_requirements = create_simple_demo_requirements()
    rubric = MultiStepRubric(simple_requirements, mock_judge)

    print("🔧 Simple Demo Rubric Configuration:")
    print("-" * 50)

    viz = RubricVisualizer(rubric)
    viz.print_complete_structure()


def demo_completed_rubric_visualizer():
    """Demonstrate the CompletedRubricVisualizer for evaluated rubrics."""
    print("\n✅ COMPLETED RUBRIC VISUALIZER DEMO")
    print("=" * 70)
    print("Visualizing rubrics that have been evaluated with actual results.\n")

    # Create mock evaluation results for simple requirements
    mock_results = {
        "0": {
            "safety_check": {
                "answer": 1.0,
                "reasoning": "Response appropriately considers safety as the first priority",
            }
        },
        "1": {
            "initial_assessment": {
                "answer": 1.0,
                "reasoning": "Response includes appropriate initial assessment steps",
            }
        },
        "2": {
            "terminal_action": {
                "answer": 1.0,
                "reasoning": "Response concludes with appropriate terminal actions",
            }
        },
    }

    # Create scenario for the simple requirements
    from verifiers.rubrics.multistep.scenario import Scenario

    demo_scenario = Scenario(
        name="Simple Demo Scenario",
        description="A demonstration scenario for the visualizer",
        prompt="You encounter an emergency situation. What do you do?",
        completion="First, I ensure the scene is safe before proceeding. Then I conduct an initial assessment of the situation and take appropriate action.",
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
        },
    )

    # Create a mock rubric and scenario
    mock_judge = MockJudgeRewarder()
    simple_requirements = create_simple_demo_requirements()
    rubric = MultiStepRubric(simple_requirements, mock_judge)

    print("🔍 Evaluated Demo Scenario:")
    print("-" * 50)

    viz = CompletedRubricVisualizer(rubric, demo_scenario, mock_results)
    viz.print_complete_evaluation()


def demo_advanced_features(name, reqs: list[Requirement], scenarios: list[Scenario]):
    """Demonstrate advanced features of each visualizer."""
    print("\n🔬 ADVANCED FEATURES DEMO")
    print("=" * 70)
    print("Showcasing advanced capabilities of each visualizer.\n")

    # Advanced RequirementsVisualizer features
    print("📊 Advanced Requirements Analysis:")
    print("-" * 40)
    viz = RequirementsVisualizer(reqs)
    metrics = viz.analyze_metrics()

    print("Key Workflow Characteristics:")
    print(f"  • Structure: {metrics['max_depth']} levels deep")
    print(
        f"  • Complexity: {metrics['avg_branching_factor']:.1f} average branches per node"
    )
    print(
        f"  • Terminal Ratio: {metrics['terminal_nodes']}/{metrics['total_requirements']} ({metrics['terminal_nodes'] / metrics['total_requirements'] * 100:.1f}%)"
    )
    print(f"  • Connectivity: {metrics['total_edges']} dependency edges")
    print()

    # Show dependency complexity
    print("🔗 Dependency Complexity Analysis:")
    print("-" * 40)
    complex_nodes = []
    for req in reqs:
        if req.dependencies and len(req.dependencies) > 2:
            complex_nodes.append(req.name)

    print(
        f"Multi-branch nodes ({len(complex_nodes)}): {', '.join(complex_nodes[:5])}{'...' if len(complex_nodes) > 5 else ''}"
    )
    print()


def run_full_demo():
    """Run the complete visualization demo showcasing all three visualizers."""
    print("🎭 MULTISTEP VISUALIZERS DEMO")
    print("=" * 70)
    print("Comprehensive demonstration of all three specialized visualizers.\n")
    print("This demo showcases:")
    print("✓ RequirementsVisualizer - Pure requirement dependency analysis")
    print("✓ RubricVisualizer - Complete rubric structure with nodes")
    print("✓ CompletedRubricVisualizer - Evaluated rubrics with results")
    print("✓ Workflow comparison capabilities")
    print("✓ Advanced analysis features")
    print()

    workflow_name = "first_responder"
    requirements, scenarios = get_workflow(workflow_name)

    demo_requirements_visualizer(workflow_name, requirements, scenarios)
    demo_rubric_visualizer()
    demo_completed_rubric_visualizer()
    demo_advanced_features(workflow_name, requirements, scenarios)

    print("\n🎉 DEMO COMPLETE!")
    print("=" * 70)
    print("You've explored all three specialized visualizers:")
    print()
    print("📋 RequirementsVisualizer:")
    print("   • Dependency graph analysis")
    print("   • Workflow level structure")
    print("   • Metrics and statistics")
    print("   • Evaluation path tracing")
    print()
    print("🏗️ RubricVisualizer:")
    print("   • Complete rubric configuration")
    print("   • Node types and structures")
    print("   • Judge and reward strategy details")
    print("   • Integrated requirements analysis")
    print()
    print("✅ CompletedRubricVisualizer:")
    print("   • Scenario evaluation details")
    print("   • Judge results and reasoning")
    print("   • Actual evaluation paths taken")
    print("   • Information revelation tracking")
    print()
    print("⚖️  Comparison Tools:")
    print("   • Side-by-side workflow analysis")
    print("   • Metric comparison tables")
    print("   • Structural differences highlighting")


if __name__ == "__main__":
    run_full_demo()
