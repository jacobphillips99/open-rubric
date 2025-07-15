from enum import Enum


class EvaluationMode(Enum):
    """Different modes for evaluating multi-step rubrics."""
    MODEL_GUIDED = "model_guided"        
    REFERENCE_GUIDED = "reference_guided"  
    EXHAUSTIVE = "exhaustive"            
    ADAPTIVE = "adaptive"                


class TerminalCondition(Enum):
    """Reasons why evaluation might terminate."""
    COMPLETED = "completed"              
    NO_VALID_PATH = "no_valid_path"      
    ERROR = "error"                      
    MAX_DEPTH_REACHED = "max_depth_reached"  