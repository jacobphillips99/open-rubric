"""
Builder classes for creating rubrics and scenarios manually.

The builder classes are meant to simply and easily create rubrics and scenarios. They may be used by a human
or LLM in order to create rubrics and scenarios, and may power a UI to create these objects by hand.
"""

from verifiers.rewards.judge_reward import JudgeRewarder, make_judge_rewarder
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.requirement import Requirement, make_requirement
from verifiers.rubrics.multistep.reward_strategies import RewardStrategy


class RubricBuilder:
    """Builder for creating a MultiStepRubric."""
    def __init__(self) -> None:
        self.requirements = []
        self.judge_options = []
        self.reward_strategy = None

    def add_requirement(self, requirement: Requirement | dict):
        if isinstance(requirement, dict):
            requirement = make_requirement(requirement)
        self.requirements.append(requirement)
    
    def add_requirements(self, requirements: list[Requirement | dict]):
        for requirement in requirements:
            self.add_requirement(requirement)

    def add_judge_option(self, judge_option: JudgeRewarder | dict):
        if isinstance(judge_option, dict):
            judge_option = make_judge_rewarder(judge_option)
        self.judge_options.append(judge_option)

    def add_judge_options(self, judge_options: list[JudgeRewarder | dict]):
        for judge_option in judge_options:
            self.add_judge_option(judge_option)

    def set_reward_strategy(self, reward_strategy: RewardStrategy):
        self.reward_strategy = reward_strategy

    def make_rubric(self) -> MultiStepRubric:
        return MultiStepRubric(self.requirements, self.judge_options, self.reward_strategy)
