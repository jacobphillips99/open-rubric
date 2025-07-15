from typing import Callable, Optional, Union, Awaitable, Any


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
    - float | dict[str, float] for sync implementations
    - Awaitable[float | dict[str, float] | Any] for async implementations (like JudgeRewarder)
    if dict, the float answer is at the key "answer"
    """
    name: str

    def __call__(self, *args, **kwargs) -> Union[float, dict[str, float], Awaitable[Any]]:
        raise NotImplementedError("Reward function must implement a `__call__` method.")


class RewardWithFunction(Reward):
    def __init__(self, func: Callable, name: Optional[str] = None):
        self.func = func
        self.name = name if name is not None else func.__name__

    def __call__(self, *args, **kwargs) -> float:
        return self.func(*args, **kwargs)
