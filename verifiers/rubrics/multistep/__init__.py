# Multistep rubric module for complex dependency-based evaluations
# TODO FIX MEEEEEEEEE. 

# Core classes that users will typically import
from .rubric import MultiStepRubric
from .enums import EvaluationMode, TerminalCondition
from .results import EvaluationResult

# Example rubrics and supporting classes
from .requirements import Requirement, BinaryRequirement, Scenario
from .examples import (
    first_responder_reqs, scenarios, debugging_reqs, debugging_scenarios, all_scenarios,
    AVAILABLE_WORKFLOWS, get_workflow, list_workflows, get_workflow_summary
)

# Reward strategies for advanced users
from .core.reward_strategies import (
    RewardStrategy,
    LevelWeightedRewardStrategy,
    SumRewardStrategy, 
    MeanRewardStrategy,
    LevelBasedRewardStrategy,
    CompletionRatioRewardStrategy,
    ProgressiveRewardStrategy
)

# Node classes for advanced customization
from .nodes import (
    RequirementRewardNode,
    RequirementJudgeRewardNode, 
    BinaryRequirementRewardNode
)

# Utilities
from .utils import topological_levels
from .visualization import WorkflowVisualizer, visualize_workflow, compare_workflows
from .builder import (
    WorkflowBuilder, 
    WorkflowNode,
    ScenarioBuilder,
    LinearWorkflowTemplate,
    BranchingWorkflowTemplate,
    quick_workflow,
    quick_scenario
)

__all__ = [
    # Core API
    "MultiStepRubric",
    "EvaluationMode", 
    "TerminalCondition",
    "EvaluationResult",
    
    # Example rubrics and supporting classes
    "Requirement",
    "BinaryRequirement", 
    "Scenario",
    "first_responder_reqs",
    "scenarios",
    "debugging_reqs",
    "debugging_scenarios", 
    "all_scenarios",
    "AVAILABLE_WORKFLOWS",
    "get_workflow",
    "list_workflows",
    "get_workflow_summary",
    
    # Reward strategies
    "RewardStrategy",
    "LevelWeightedRewardStrategy",
    "SumRewardStrategy",
    "MeanRewardStrategy", 
    "LevelBasedRewardStrategy",
    "CompletionRatioRewardStrategy",
    "ProgressiveRewardStrategy",
    
    # Node classes
    "RequirementRewardNode",
    "RequirementJudgeRewardNode",
    "BinaryRequirementRewardNode",
    
    # Utilities
    "topological_levels",
    "WorkflowVisualizer",
    "visualize_workflow", 
    "compare_workflows",
    
    # Builder utilities
    "WorkflowBuilder",
    "WorkflowNode", 
    "ScenarioBuilder",
    "LinearWorkflowTemplate",
    "BranchingWorkflowTemplate",
    "quick_workflow",
    "quick_scenario"
] 