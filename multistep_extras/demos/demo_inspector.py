"""
Demo script for the new MultiStep Inspectors.

This demonstrates the inspection capabilities of the three specialized inspectors:
1. RequirementsInspector - For analyzing requirement dependencies
2. RubricInspector - For inspecting complete rubrics with nodes
3. EvaluationInspector - For inspecting evaluated rubrics with results
"""

import os
import traceback

from openai import OpenAI

from example_rubrics import get_workflow
from multistep_extras.inspection.inspector import (EvaluationInspector,
                                                   RequirementsInspector,
                                                   RubricInspector,
                                                   inspect_requirements)
from multistep_extras.utils.print_utils import (print_debug, print_error,
                                                print_header, print_info,
                                                print_process, print_score,
                                                print_success)
from verifiers.rewards.judge_reward import (JUDGE_PROMPT, BinaryJudgeRewarder,
                                            JudgeRewarder,
                                            UnitVectorJudgeRewarder)
# For creating mock rubrics and evaluations
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
# Create examples of both types
from verifiers.rubrics.multistep.requirement import (BinaryRequirement,
                                                     Requirement,
                                                     UnitVectorRequirement)
from verifiers.rubrics.multistep.scenario import Scenario


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


def demo_requirements_inspector(name: str, reqs: list[Requirement]):
    """Demonstrate the RequirementsInspector for pure requirement analysis."""
    print_header("📋 REQUIREMENTS INSPECTOR DEMO")
    print_info("Analyzing requirement dependencies and workflow structure.")
    print()

    # Start with simple, clear hierarchical requirements to show the concept
    print_process("🔍 Understanding Requirement Dependencies:")
    print_info(
        "Let's start with a simple example to understand how requirements connect..."
    )
    print()

    simple_reqs = create_simple_demo_requirements()
    simple_inspector = RequirementsInspector(simple_reqs)
    simple_inspector.print_workflow_structure()

    # Trace a path through the simple requirements
    print_process("📍 Evaluation Path Tracing:")
    print_info("When we provide answers, the inspector shows which path gets taken:")
    sample_answers = {"safety_check": 1.0, "initial_assessment": 1.0}
    simple_inspector.print_evaluation_path(sample_answers)
    print()

    # Now show the real workflow - use full requirements list to avoid dependency issues
    print_process(f"🚑 Real-World Example: {name.title()} Workflow:")
    print_info("Now let's see the complete real-world requirement structure...")
    print()

    # Show the full requirements list to avoid breaking dependency references
    inspect_requirements(reqs)


def demo_rubric_inspector(judge_options: list[JudgeRewarder]):
    """Demonstrate the RubricInspector for complete rubrics with nodes."""
    print_header("🏗️ RUBRIC INSPECTOR DEMO")
    print_info("Inspecting complete rubrics with nodes, judges, and strategies.")
    print()

    simple_reqs = create_simple_demo_requirements()
    rubric = MultiStepRubric(simple_reqs, judge_options)

    print_process("🔧 Simple Demo Rubric Configuration:")
    inspector = RubricInspector(rubric)
    inspector.print_complete_structure()


def demo_evaluation_inspector(judge_options: list[JudgeRewarder]):
    """Demonstrate the EvaluationInspector for evaluated rubrics."""
    print_header("✅ EVALUATION INSPECTOR DEMO")
    print_info("Inspecting rubrics with actual evaluation results and judge feedback.")
    print()

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

    simple_reqs = create_simple_demo_requirements()
    rubric = MultiStepRubric(simple_reqs, judge_options)

    print_process("🔍 Evaluated Scenario Results:")
    print_info("This shows how the inspector displays actual evaluation outcomes...")
    print()
    inspector = EvaluationInspector(rubric)
    inspector.print_complete_evaluation(demo_scenario, mock_results)


def demo_discrete_vs_continuous(judge_options: list[JudgeRewarder]):
    """Demonstrate the difference between discrete and continuous requirements."""
    print_header("⚡ DISCRETE VS CONTINUOUS SCORING DEMO")
    print_info(
        "Comparing how discrete and continuous requirements display in the inspector."
    )
    print()

    try:
        discrete_req = BinaryRequirement(
            name="safety_check",
            question="Does the response prioritize safety?",
            dependencies={1.0: ["next_step"], 0.0: []},
        )

        # UnitVectorRequirement only supports 0.0 and 1.0 as dependency keys
        # Let's use threshold-based logic: 0.0 leads to basic_check, 1.0 leads to advanced_check
        continuous_req = UnitVectorRequirement(
            name="quality_score",
            question="How would you rate the overall quality of this response?",
            dependencies={1.0: ["advanced_check"], 0.0: ["basic_check"]},
        )

        print_process("✅ Requirements created successfully!")
        print()

        print_process("📋 Discrete Requirement Example:")
        print_info(f"  • Name: {discrete_req.name}")
        print_info(f"  • Format: {discrete_req.judge_response_format.options}")
        if discrete_req.judge_response_format.meanings:
            meanings = ", ".join(
                [
                    f"{k}={v}"
                    for k, v in discrete_req.judge_response_format.meanings.items()
                ]
            )
            print_info(f"  • Meanings: {meanings}")
        print_info("  • Dependencies: Exact match logic")
        print()

        print_process("📈 Continuous Requirement Example:")
        print_info(f"  • Name: {continuous_req.name}")
        print_info(f"  • Format: {continuous_req.judge_response_format.options}")
        if continuous_req.judge_response_format.meanings:
            meanings = ", ".join(
                [
                    f"{k}={v}"
                    for k, v in continuous_req.judge_response_format.meanings.items()
                ]
            )
            print_info(f"  • Meanings: {meanings}")
        print_info("  • Dependencies: Threshold-based logic")
        print()

        # Test validation with a mock scenario
        test_requirements = [discrete_req, continuous_req]
        test_rubric = MultiStepRubric(test_requirements, judge_options)

        print_process("🔍 Testing rubric validation:")

        # Test with valid scenario
        valid_scenario = Scenario(
            prompt="Test prompt",
            completion="Test completion",
            answers={
                "safety_check": {"answer": 1.0, "reasoning": "Safe response"},
                "quality_score": {"answer": 0.0, "reasoning": "Basic quality"},
            },
        )

        try:
            test_rubric.validate(valid_scenario)
            print_info("  ✅ Valid scenario passed validation")
        except ValueError as e:
            print_info(f"  ❌ Valid scenario failed: {e}; {traceback.format_exc()}")

        # Test with invalid scenario (invalid answer value)
        invalid_scenario = Scenario(
            prompt="Test prompt",
            completion="Test completion",
            answers={
                "safety_check": {
                    "answer": 2.0,
                    "reasoning": "Invalid value",
                },  # Invalid: not in [0.0, 1.0]
                "quality_score": {
                    "answer": 0.5,
                    "reasoning": "Mid quality",
                },  # Invalid: not in [0.0, 1.0]
            },
        )

        try:
            test_rubric.validate(invalid_scenario)
            print_info("  ❌ Invalid scenario unexpectedly passed validation")
        except ValueError as e:
            print_info(
                f"  ✅ Invalid scenario correctly rejected: {e}; {traceback.format_exc()}"
            )

        print()
        print_process("🎯 Key Insights:")
        print_info(
            "  • UnitVectorRequirement only accepts 0.0 and 1.0 as dependency keys"
        )
        print_info("  • BinaryRequirement uses exact matching for dependencies")
        print_info("  • Always validate scenarios before evaluation")
        print_info(
            "  • Rubric.validate() checks answer values against valid response format options"
        )

    except Exception as e:
        print_error(f"❌ Error creating requirements: {e}; {traceback.format_exc()}")
        print_info("This demonstrates the importance of validation!")
        print()
        print_process("🔧 Resolution:")
        print_info("  • Check that dependency keys match valid response format options")
        print_info("  • Use rubric.validate(scenario) before evaluation")
        print_info(
            "  • For custom thresholds, create custom ContinuousRequirement subclasses"
        )


def demo_advanced_features(
    name: str, reqs: list[Requirement], scenarios: list[Scenario]
):
    """Demonstrate advanced features of each inspector."""
    print_header("🔬 ADVANCED ANALYSIS FEATURES")
    print_info("Deep-dive into workflow metrics and complexity analysis.")
    print()

    # Advanced RequirementsInspector features
    print_process("📊 Workflow Complexity Metrics:")
    inspector = RequirementsInspector(reqs)
    metrics = inspector.analyze_metrics()

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
    """Run the complete inspection demo showcasing all three inspectors."""
    workflow_name = "first_responder"
    requirements, scenarios = get_workflow(workflow_name)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    judge_model = "gpt-4o-nano"
    judge_options = [
        BinaryJudgeRewarder(
            judge_prompt=JUDGE_PROMPT, judge_client=client, judge_model=judge_model
        ),
        UnitVectorJudgeRewarder(
            judge_prompt=JUDGE_PROMPT, judge_client=client, judge_model=judge_model
        ),
    ]

    demo_requirements_inspector(workflow_name, requirements)
    demo_rubric_inspector(judge_options)
    demo_evaluation_inspector(judge_options)
    demo_discrete_vs_continuous(judge_options)
    demo_advanced_features(workflow_name, requirements, scenarios)

    print_success("🎉 DEMO JOURNEY COMPLETE!")


if __name__ == "__main__":
    run_full_demo()
