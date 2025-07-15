"""
Demo script for the workflow registry functionality.

This demonstrates how to use the new workflow registry to explore and access
different example workflows.
"""

from .examples import (
    get_workflow, 
    list_workflows, 
    get_workflow_summary,
    AVAILABLE_WORKFLOWS
)
from .visualization import WorkflowVisualizer


def demo_workflow_registry():
    """Demonstrate the workflow registry functionality."""
    print("🗂️  WORKFLOW REGISTRY DEMO")
    print("=" * 50)
    
    # Show all available workflows
    print("\n1. List all available workflows:")
    workflows = list_workflows()
    print(f"Available workflows: {workflows}")
    
    # Show workflow summary
    print("\n2. Get workflow summary:")
    summary = get_workflow_summary()
    print(summary)
    
    # Get specific workflow details
    print("\n3. Get specific workflow details:")
    for workflow_name in workflows:
        workflow = get_workflow(workflow_name)
        print(f"\n--- {workflow_name.upper()} ---")
        print(f"Name: {workflow['name']}")
        print(f"Description: {workflow['description']}")
        print(f"Requirements: {len(workflow['requirements'])}")
        print(f"Scenarios: {len(workflow['scenarios'])}")
        print(f"Structure: {workflow['characteristics']['structure']}")
        print(f"Domain: {workflow['characteristics']['domain']}")
        
        # Show first scenario as example
        if workflow['scenarios']:
            first_scenario = workflow['scenarios'][0]
            print(f"Example scenario: {first_scenario.name}")
            print(f"  Description: {first_scenario.description}")
    
    # Compare workflow structures
    print("\n4. Compare workflow structures:")
    first_responder = get_workflow("first_responder")
    debugging = get_workflow("debugging")
    
    print(f"First Responder - Requirements: {len(first_responder['requirements'])}, "
          f"Structure: {first_responder['characteristics']['structure']}")
    print(f"Debugging - Requirements: {len(debugging['requirements'])}, "
          f"Structure: {debugging['characteristics']['structure']}")
    
    # Show visualizations for each workflow
    print("\n5. Workflow visualizations:")
    for workflow_name in workflows:
        workflow = get_workflow(workflow_name)
        print(f"\n--- {workflow_name.upper()} VISUALIZATION ---")
        
        visualizer = WorkflowVisualizer(workflow['requirements'])
        metrics = visualizer.analyze_workflow_metrics()
        
        print(f"Total Requirements: {metrics['total_requirements']}")
        print(f"Terminal Nodes: {metrics['terminal_nodes']}")
        print(f"Max Depth: {metrics['max_depth']} levels")
        print(f"Average Branching Factor: {metrics['avg_branching_factor']:.2f}")
        print(f"Root Nodes: {', '.join(metrics['root_nodes'])}")
        print(f"Total Possible Paths: {len(visualizer.find_possible_paths())}")


def demo_workflow_access():
    """Demonstrate accessing workflows programmatically."""
    print("\n🔧 PROGRAMMATIC WORKFLOW ACCESS")
    print("=" * 50)
    
    # Access via registry
    print("\n1. Access via registry:")
    first_responder = get_workflow("first_responder")
    print(f"Loaded: {first_responder['name']}")
    print(f"Requirements: {len(first_responder['requirements'])}")
    
    # Access via direct import (legacy)
    print("\n2. Access via direct import (legacy):")
    from .examples import first_responder_reqs, scenarios
    print(f"Direct import - Requirements: {len(first_responder_reqs)}")
    print(f"Direct import - Scenarios: {len(scenarios)}")
    
    # Access via AVAILABLE_WORKFLOWS dict
    print("\n3. Access via AVAILABLE_WORKFLOWS dict:")
    for name, info in AVAILABLE_WORKFLOWS.items():
        print(f"{name}: {info['name']} ({len(info['requirements'])} requirements)")


def demo_error_handling():
    """Demonstrate error handling for invalid workflows."""
    print("\n⚠️  ERROR HANDLING DEMO")
    print("=" * 50)
    
    try:
        invalid_workflow = get_workflow("nonexistent")
    except KeyError as e:
        print(f"✅ Caught expected error: {e}")
    
    print("✅ Error handling works correctly!")


def run_full_demo():
    """Run the complete workflow registry demo."""
    print("🗃️  WORKFLOW REGISTRY SYSTEM DEMO")
    print("=" * 60)
    print("This demo showcases the new workflow registry system.\n")
    
    demo_workflow_registry()
    demo_workflow_access()
    demo_error_handling()
    
    print("\n🎯 WORKFLOW REGISTRY DEMO COMPLETE!")
    print("You've seen:")
    print("✓ Workflow discovery and listing")
    print("✓ Detailed workflow information")
    print("✓ Workflow comparison and analysis")
    print("✓ Multiple access methods")
    print("✓ Error handling for invalid workflows")
    print("✓ Integration with visualization tools")


if __name__ == "__main__":
    run_full_demo() 