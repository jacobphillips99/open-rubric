"""
Builder classes for creating rubrics and scenarios manually.

The builder classes are meant to simply and easily create rubrics and scenarios. They may be used by a human
or LLM in order to create rubrics and scenarios, and may power a UI to create these objects by hand.
"""

from verifiers.rewards.judge_reward import (JudgeRewarder, make_judge_rewarder)
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.requirement import (Requirement,
                                                     make_requirement,)
from verifiers.rubrics.multistep.reward_strategies import (RewardStrategy, make_reward_strategy)


class RubricBuilder:
    """Builder for creating a MultiStepRubric."""

    def __init__(self) -> None:
        """ Initialize the RubricBuilder."""
        self.requirements = []
        self.judge_options = []
        self.reward_strategy = None

    def add_requirement(self, requirement: Requirement | dict) -> None:
        """Add a requirement to the RubricBuilder."""
        if isinstance(requirement, dict):
            requirement_type = requirement.pop("type")
            requirement = make_requirement(requirement_type, **requirement)
        self.requirements.append(requirement)

    def add_requirements(self, requirements: list[Requirement | dict]) -> None:
        """Add multiple requirements to the RubricBuilder."""
        for requirement in requirements:
            self.add_requirement(requirement)

    def add_judge_option(self, judge_option: JudgeRewarder | dict) -> None:
        """Add a judge option to the RubricBuilder."""
        if isinstance(judge_option, dict):
            judge_type = judge_option.pop("type")
            judge_option = make_judge_rewarder(judge_type, **judge_option)
        self.judge_options.append(judge_option)

    def add_judge_options(self, judge_options: list[JudgeRewarder | dict]) -> None:
        """Add multiple judge options to the RubricBuilder."""
        for judge_option in judge_options:
            self.add_judge_option(judge_option)

    def set_reward_strategy(self, reward_strategy: RewardStrategy | dict) -> None:
        """Set the reward strategy for the RubricBuilder."""
        if isinstance(reward_strategy, dict):
            reward_strategy_type = reward_strategy.pop("type")
            reward_strategy = make_reward_strategy(reward_strategy_type, **reward_strategy)
        self.reward_strategy = reward_strategy

    def make_rubric(self) -> MultiStepRubric:
        """Make a MultiStepRubric from the RubricBuilder."""
        return MultiStepRubric(
            self.requirements, self.judge_options, self.reward_strategy
        )


class ScenarioBuilder:
    """Builder for creating a Scenario."""
    pass
