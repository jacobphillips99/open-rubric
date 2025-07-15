"""
Example workflows for the MultiStep Rubric system.

This module contains complete example workflows with requirements and scenarios
for different domains, showcasing the versatility of the multistep evaluation system.
"""

# Import first responder example
from .first_responder import (
    requirements as first_responder_requirements,
    scenarios as first_responder_scenarios
)

# Import debugging example  
from .debugging import (
    requirements as debugging_requirements,
    scenarios as debugging_scenarios
)

# Legacy aliases for backward compatibility
first_responder_reqs = first_responder_requirements
scenarios = first_responder_scenarios
debugging_reqs = debugging_requirements
debugging_scenarios = debugging_scenarios

# Combined scenarios from all examples
all_scenarios = first_responder_scenarios + debugging_scenarios

# Available workflow examples
AVAILABLE_WORKFLOWS = {
    "first_responder": {
        "name": "First Responder Emergency Medical Response",
        "description": "Wide-branching workflow for emergency medical situations with parallel assessments",
        "requirements": first_responder_requirements,
        "scenarios": first_responder_scenarios,
        "characteristics": {
            "structure": "wide_branching",
            "depth": "shallow_to_medium",
            "domain": "emergency_medical",
            "complexity": "high_parallel"
        }
    },
    "debugging": {
        "name": "Software Debugging Investigation",
        "description": "Sequential workflow for systematic software problem investigation",
        "requirements": debugging_requirements,
        "scenarios": debugging_scenarios,
        "characteristics": {
            "structure": "sequential",
            "depth": "deep",
            "domain": "software_engineering", 
            "complexity": "medium_sequential"
        }
    }
}

def get_workflow(name: str) -> dict:
    """
    Get a workflow by name.
    
    Args:
        name: Name of the workflow ('first_responder' or 'debugging')
        
    Returns:
        Dictionary containing workflow information
        
    Raises:
        KeyError: If workflow name is not found
    """
    if name not in AVAILABLE_WORKFLOWS:
        available = ", ".join(AVAILABLE_WORKFLOWS.keys())
        raise KeyError(f"Workflow '{name}' not found. Available workflows: {available}")
    
    return AVAILABLE_WORKFLOWS[name]

def list_workflows() -> list[str]:
    """
    List all available workflow names.
    
    Returns:
        List of workflow names
    """
    return list(AVAILABLE_WORKFLOWS.keys())

def get_workflow_summary() -> str:
    """
    Get a summary of all available workflows.
    
    Returns:
        Formatted string describing all workflows
    """
    summary = "Available Workflow Examples:\n"
    summary += "=" * 50 + "\n"
    
    for name, info in AVAILABLE_WORKFLOWS.items():
        summary += f"\n{name.upper()}:\n"
        summary += f"  Name: {info['name']}\n"
        summary += f"  Description: {info['description']}\n"
        summary += f"  Requirements: {len(info['requirements'])}\n"
        summary += f"  Scenarios: {len(info['scenarios'])}\n"
        summary += f"  Structure: {info['characteristics']['structure']}\n"
        summary += f"  Domain: {info['characteristics']['domain']}\n"
    
    return summary

# Export everything
__all__ = [
    # Individual workflow components
    "first_responder_requirements",
    "first_responder_scenarios", 
    "debugging_requirements",
    "debugging_scenarios",
    
    # Legacy aliases
    "first_responder_reqs",
    "scenarios",
    "debugging_reqs",
    "debugging_scenarios",
    
    # Combined data
    "all_scenarios",
    
    # Workflow registry
    "AVAILABLE_WORKFLOWS",
    "get_workflow",
    "list_workflows",
    "get_workflow_summary"
] 