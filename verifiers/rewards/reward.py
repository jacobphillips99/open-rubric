from typing import Callable, Optional


class Reward:
    """
    Reward class. Must implement a `__call__` method that takes inputs and returns a score.

    Each reward function takes:
    - prompt: List[Dict[str, str]] | str 
    - completion: List[Dict[str, str]] | str
    - answer: Any (metadata for scoring)
    - task (optional): str (type of task)
    - **kwargs: additional kwargs

    Returns:
    - float
    """
    def __call__(self, *args, **kwargs) -> float:
        raise NotImplementedError("Reward function must implement a `__call__` method.")
    

class RewardWithFunction(Reward):
    def __init__(self, func: Callable, name: Optional[str] = None):
        self.func = func
        self.name = name if name is not None else func.__name__
    
    def __call__(self, *args, **kwargs) -> float:
        return self.func(*args, **kwargs)
    