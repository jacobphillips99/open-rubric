"""
Demo script for the WorkflowBuilder and related builder utilities.

This demonstrates how to create workflows using the fluent builder interface.
"""

from .builder import (
    WorkflowBuilder, 
    ScenarioBuilder,
    LinearWorkflowTemplate,
    BranchingWorkflowTemplate,
    quick_workflow,
    quick_scenario
)
from .visualization import WorkflowVisualizer


def demo_fluent_builder():
    """Demonstrate the fluent builder interface."""
    print("🔧 FLUENT WORKFLOW BUILDER DEMO")
    print("=" * 50)
    
    # Create a customer service workflow using fluent interface
    builder = WorkflowBuilder()
    
    # Build the workflow step by step
    builder.node("greet_customer", "Does the response include a proper greeting?") \
           .if_yes("identify_issue") \
           .if_no("request_clarification")
           
    builder.node("identify_issue", "Does the response identify the customer's main issue?") \
           .if_yes("check_account_status", "gather_details") \
           .if_no("ask_clarifying_questions")
           
    builder.node("check_account_status", "Does the response check the customer's account?") \
           .if_yes("provide_solution") \
           .if_no("escalate_to_specialist")
           
    builder.node("gather_details", "Does the response gather relevant details?") \
           .if_yes("provide_solution") \
           .if_no("ask_clarifying_questions")
    
    # Terminal nodes
    builder.node("provide_solution", "Does the response provide a clear solution?").terminal()
    builder.node("escalate_to_specialist", "Does the response escalate appropriately?").terminal()
    builder.node("ask_clarifying_questions", "Does the response ask for clarification?").terminal()
    builder.node("request_clarification", "Does the response request clarification?").terminal()
    
    # Build and validate
    workflow = builder.build()
    
    print("Built customer service workflow with fluent interface:")
    print(f"✓ Created {len(workflow)} requirements")
    
    # Validate the workflow
    errors = builder.validate()
    if errors:
        print("❌ Validation errors found:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ Workflow validation passed!")
    
    # Visualize the created workflow
    print("\nWorkflow Structure:")
    visualizer = WorkflowVisualizer(workflow)
    visualizer.print_workflow_structure()
    visualizer.print_workflow_metrics()


def demo_linear_template():
    """Demonstrate the linear workflow template."""
    print("\n📏 LINEAR WORKFLOW TEMPLATE DEMO")
    print("=" * 50)
    
    # Create a simple linear troubleshooting workflow
    steps = [
        ("identify_problem", "Does the response identify the specific problem?"),
        ("check_basics", "Does the response check basic troubleshooting steps?"),
        ("test_solution", "Does the response test the proposed solution?"),
        ("verify_fix", "Does the response verify that the issue is resolved?"),
        ("document_solution", "Does the response document the solution for future reference?")
    ]
    
    workflow = LinearWorkflowTemplate.build_from_steps(steps)
    
    print("Built linear troubleshooting workflow:")
    print(f"✓ Created {len(workflow)} requirements in sequence")
    
    # Show the structure
    visualizer = WorkflowVisualizer(workflow)
    visualizer.print_workflow_structure()


def demo_branching_template():
    """Demonstrate the branching workflow template."""
    print("\n🌳 BRANCHING WORKFLOW TEMPLATE DEMO")
    print("=" * 50)
    
    # Define a decision tree structure
    tree = {
        "assess_urgency": {
            "question": "Does the response assess the urgency of the situation?",
            "yes": ["handle_urgent", "handle_normal"],
            "no": ["request_more_info"]
        },
        "handle_urgent": {
            "question": "Does the response handle urgent cases appropriately?",
            "yes": ["escalate_immediately"],
            "no": ["provide_interim_solution"]
        },
        "handle_normal": {
            "question": "Does the response handle normal cases systematically?",
            "yes": ["follow_standard_process"],
            "no": ["provide_guidance"]
        },
        "request_more_info": {
            "question": "Does the response request necessary additional information?",
            "terminal": True
        },
        "escalate_immediately": {
            "question": "Does the response escalate urgent issues immediately?",
            "terminal": True
        },
        "provide_interim_solution": {
            "question": "Does the response provide an interim solution?",
            "terminal": True
        },
        "follow_standard_process": {
            "question": "Does the response follow the standard process?",
            "terminal": True
        },
        "provide_guidance": {
            "question": "Does the response provide helpful guidance?",
            "terminal": True
        }
    }
    
    workflow = BranchingWorkflowTemplate.build_from_tree(tree)
    
    print("Built branching decision tree workflow:")
    print(f"✓ Created {len(workflow)} requirements with branching logic")
    
    # Show the structure
    visualizer = WorkflowVisualizer(workflow)
    visualizer.print_workflow_structure()


def demo_quick_helpers():
    """Demonstrate the quick helper functions."""
    print("\n⚡ QUICK HELPERS DEMO")
    print("=" * 50)
    
    # Quick workflow
    workflow = quick_workflow(
        "analyze_situation",
        "plan_response", 
        "execute_plan",
        "evaluate_results"
    )
    
    print("Quick workflow created:")
    for req in workflow:
        print(f"✓ {req.name}: {req.question}")
    
    # Quick scenario
    scenario = quick_scenario(
        "How should we handle this crisis?",
        "First, I'll analyze the situation carefully, then plan a comprehensive response.",
        analyze_situation=1.0,
        plan_response=1.0,
        execute_plan=0.0,
        evaluate_results=0.0
    )
    
    print(f"\nQuick scenario created:")
    print(f"✓ Prompt: {scenario.prompt}")
    print(f"✓ Completion: {scenario.completion}")
    print(f"✓ Answers: {list(scenario.answers.keys())}")


def demo_scenario_builder():
    """Demonstrate the scenario builder."""
    print("\n📝 SCENARIO BUILDER DEMO")
    print("=" * 50)
    
    # Build a detailed scenario
    scenario = ScenarioBuilder() \
        .name("Emergency Response Test") \
        .description("Tests emergency response decision making") \
        .prompt("A fire alarm is going off in the building. People are starting to panic.") \
        .completion("I'll immediately assess if it's a real emergency, guide people to nearest exits calmly, and ensure everyone follows evacuation procedures.") \
        .answer("assess_situation", 1.0, "Clearly states need to assess the emergency") \
        .answer("guide_people", 1.0, "Mentions guiding people to exits") \
        .answer("follow_procedures", 1.0, "References evacuation procedures") \
        .answer("manage_panic", 1.0, "Addresses the need to keep people calm") \
        .build()
    
    print("Built detailed scenario:")
    print(f"✓ Name: {scenario.name}")
    print(f"✓ Description: {scenario.description}")
    print(f"✓ Prompt: {scenario.prompt[:50]}...")
    print(f"✓ Answers: {len(scenario.answers)} requirements addressed")
    
    for req_name, answer_data in scenario.answers.items():
        print(f"  - {req_name}: {answer_data['answer']} ({answer_data['reasoning']})")


def run_full_demo():
    """Run the complete builder demo."""
    print("🏗️  MULTISTEP WORKFLOW BUILDER DEMO")
    print("=" * 60)
    print("This demo showcases the builder utilities for creating workflows.\n")
    
    demo_fluent_builder()
    demo_linear_template()
    demo_branching_template()
    demo_quick_helpers()
    demo_scenario_builder()
    
    print("\n🎯 BUILDER DEMO COMPLETE!")
    print("You've seen:")
    print("✓ Fluent workflow builder with validation")
    print("✓ Linear workflow templates")
    print("✓ Branching decision tree templates")
    print("✓ Quick helper functions")
    print("✓ Detailed scenario builder")


if __name__ == "__main__":
    run_full_demo() 