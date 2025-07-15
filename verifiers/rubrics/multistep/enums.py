from enum import Enum


class EvaluationMode(Enum):
    """Different modes for evaluating multi-step rubrics."""
    MODEL_GUIDED = "model_guided"        # Follow model's answers through graph
    REFERENCE_GUIDED = "reference_guided"  # Follow ground truth answers through graph  
    EXHAUSTIVE = "exhaustive"            # Evaluate all nodes regardless of dependencies
    ADAPTIVE = "adaptive"                # Stop gracefully when can't proceed further


class TerminalCondition(Enum):
    """Reasons why evaluation might terminate."""
    COMPLETED = "completed"              # Successfully evaluated all reachable nodes
    NO_VALID_PATH = "no_valid_path"      # No valid path forward from current state
    ERROR = "error"                      # Error occurred during evaluation
    MAX_DEPTH_REACHED = "max_depth_reached"  # Hit maximum evaluation depth 