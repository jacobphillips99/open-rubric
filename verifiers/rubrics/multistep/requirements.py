from typing import Any, Optional

from verifiers.rewards.judge_reward import JudgeResponseFormat, binary_judge_response_format


class Requirement:
    def __init__(self, name: str, question: str, judge_response_format: JudgeResponseFormat, dependencies: Optional[dict[float, list[str]]] = None):
        self.name = name
        self.question = question
        self.dependencies = dependencies
        self.judge_response_format = judge_response_format

        if dependencies is not None:
            assert all(d in judge_response_format.options for d in dependencies.keys())

    def terminal(self):
        return self.dependencies is None
    

class BinaryRequirement(Requirement):
    def __init__(self, name: str, question: str, dependencies: Optional[dict[float, list[str]]] = None):
        super().__init__(name, question, binary_judge_response_format, dependencies)


class Scenario:
    """
    Represents a test scenario for evaluating multi-step rubrics.
    
    Contains a prompt (situation description), completion (response), 
    and ground truth answer path for evaluation.
    """
    
    def __init__(self, prompt: str, answers: dict[str, float], completion: Optional[str] = None,
                 name: Optional[str] = None, description: Optional[str] = None):
        """
        Initialize a scenario.
        
        Args:
            prompt: The situation or question being presented
            completion: The response or actions taken
            answers: Ground truth path mapping requirement names to expected scores
            name: Optional name for the scenario
            description: Optional description of what this scenario tests
        """
        self.prompt = prompt
        self.answers = answers
        # scenarios may or may not have a completion; it might need to be generated
        self.completion = completion
        self.name = name
        self.description = description

    def to_content(self):
        return f"""
        prompt: {self.prompt}
        completion: {self.completion}
        """.strip() 