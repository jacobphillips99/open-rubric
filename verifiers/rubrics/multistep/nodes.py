"""Node implementations for multistep rubric evaluation."""

import asyncio
from typing import Any

from verifiers.rewards.judge_reward import (BinaryJudgeRewarder,
                                            ContinuousJudgeRewarder,
                                            DiscreteJudgeRewarder,
                                            JudgeResponse, JudgeRewarder,
                                            UnitVectorJudgeRewarder)
from verifiers.rewards.reward import Reward
from verifiers.rubrics.multistep.requirement import (BinaryRequirement,
                                                     ContinuousRequirement,
                                                     DiscreteRequirement,
                                                     Requirement,
                                                     UnitVectorRequirement)
from verifiers.rubrics.multistep.scenario import Scenario


class RequirementRewardNode:
    """
    Basic node in a workflow for evaluating requirements.
    Nodes combine Requirements and Rewards, and are used to evaluate a scenario.
    """

    def __init__(self, requirement: Requirement, reward: Reward):
        """Initialize a requirement reward node."""
        self.requirement = requirement
        self.reward = reward
        self.name = requirement.name

    async def __call__(self, scenario: Scenario, **kwargs):
        """Evaluate the requirement against a scenario."""
        result = self.reward(scenario, **kwargs)
        # Check if the result is awaitable (async) and await if necessary
        if asyncio.iscoroutine(result):
            return await result
        return result

    def terminal(self) -> bool:
        """Check if the requirement is terminal."""
        return self.requirement.terminal()

    @property
    def dependencies(self) -> dict[str, list[str]] | None:
        """Get the dependencies for this requirement."""
        return self.requirement.dependencies


class RequirementJudgeRewardNode(RequirementRewardNode):
    """
    Special class where the Reward function is a JudgeRewarder.
    This is used to evaluate the correctness of the response.
    """

    def __init__(self, requirement: Requirement, judge_rewarder: JudgeRewarder):
        """Initialize a requirement judge reward node."""
        self.requirement = requirement
        self.judge_rewarder = judge_rewarder
        self.name = requirement.name

    async def __call__(self, scenario: Scenario, **kwargs) -> JudgeResponse:
        """Evaluate the requirement using judge reward against a scenario."""
        question = self.requirement.question

        # Handle missing answers gracefully in reference-guided evaluation
        if scenario.answers is None or self.requirement.name not in scenario.answers:
            raise ValueError(
                f"No answer provided for requirement '{self.requirement.name}' in scenario {scenario.name}; only have answers for {scenario.answers.keys()}"
            )

        # Extract answer value from the new format
        answer_data = scenario.answers[self.requirement.name]
        if isinstance(answer_data, dict) and "answer" in answer_data:
            answer: float | str = answer_data["answer"]
        else:
            # Fallback for old format - answer_data is the direct value
            answer = answer_data  # type: ignore[assignment]

        content = scenario.to_content()
        judge_result = await self.judge_rewarder(question, content, answer, **kwargs)

        return judge_result

    def get_dependencies(self):
        """Get the dependencies for this requirement."""
        return self.requirement.dependencies


class DiscreteRequirementRewardNode(RequirementJudgeRewardNode):
    """Special subclass of the RequirementJudgeRewardNode for discrete requirements."""


class ContinuousRequirementRewardNode(RequirementJudgeRewardNode):
    """Special subclass of the RequirementJudgeRewardNode for continuous requirements."""


class BinaryRequirementRewardNode(DiscreteRequirementRewardNode):
    """Special subclass of the RequirementJudgeRewardNode for binary requirements."""

    def __init__(self, requirement: Any, judge_rewarder: BinaryJudgeRewarder):
        """Initialize a binary requirement judge reward node."""
        super().__init__(requirement, judge_rewarder)


class UnitVectorRequirementRewardNode(ContinuousRequirementRewardNode):
    """Special subclass of the RequirementJudgeRewardNode for unit vector requirements."""

    def __init__(self, requirement: Any, judge_rewarder: UnitVectorJudgeRewarder):
        """Initialize a unit vector requirement judge reward node."""
        super().__init__(requirement, judge_rewarder)


REQUIREMENT_TO_JUDGE_MAPPING = {
    BinaryRequirement: BinaryJudgeRewarder,
    UnitVectorRequirement: UnitVectorJudgeRewarder,
    DiscreteRequirement: DiscreteJudgeRewarder,
    ContinuousRequirement: ContinuousJudgeRewarder,
    Requirement: JudgeRewarder,
}


class NodeFactory:
    """Factory class for creating the appropriate RequirementRewardNode based on requirement and judge rewarder types."""

    @staticmethod
    def create_node(
        requirement: Requirement, judge_options: list[JudgeRewarder]
    ) -> RequirementJudgeRewardNode:
        """
        Create the appropriate RequirementRewardNode based on the types of requirement and judge rewarder.

        Args:
            requirement: The requirement to evaluate
            judge_options: List of judge rewarders available for matching

        Returns:
            The appropriate RequirementRewardNode subclass instance
        """
        selected_judge = None
        
        # First, try name-based matching if judge_name is specified
        if hasattr(requirement, 'judge_name') and requirement.judge_name is not None:
            named_judges = [
                jr for jr in judge_options 
                if hasattr(jr, 'name') and jr.name == requirement.judge_name
            ]
            if named_judges:
                selected_judge = named_judges[0]
                # Validate that the named judge's response format is compatible
                if hasattr(selected_judge, 'judge_response_format'):
                    judge_format = selected_judge.judge_response_format
                    req_format = requirement.judge_response_format
                    if judge_format.__class__ != req_format.__class__:
                        raise ValueError(
                            f"Judge '{requirement.judge_name}' has response format {judge_format.__class__.__name__} "
                            f"but requirement '{requirement.name}' expects {req_format.__class__.__name__}"
                        )
            else:
                raise ValueError(
                    f"No judge found with name '{requirement.judge_name}' for requirement '{requirement.name}'. "
                    f"Available judge names: {[getattr(jr, 'name', 'unnamed') for jr in judge_options]}"
                )
        
        # If no judge selected by name, fall back to type-based matching
        if selected_judge is None:
            # maintain order of precedence in REQUIREMENT_TO_JUDGE_MAPPING
            for requirement_type, judge_type in REQUIREMENT_TO_JUDGE_MAPPING.items():
                if isinstance(requirement, requirement_type):
                    compatible_judges = [
                        jr for jr in judge_options if isinstance(jr, judge_type)
                    ]
                    if not compatible_judges:
                        raise ValueError(
                            f"No judge rewarder found for requirement type {requirement_type} from judge options {judge_options}"
                        )
                    selected_judge = compatible_judges[0]
                    break
            
            if selected_judge is None:
                raise ValueError(
                    f"Requirement type {type(requirement)} not found in mapping {REQUIREMENT_TO_JUDGE_MAPPING}"
                )
        
        return RequirementJudgeRewardNode(requirement, selected_judge)
