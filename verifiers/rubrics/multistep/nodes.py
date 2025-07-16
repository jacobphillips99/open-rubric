"""Node implementations for multistep rubric evaluation."""

import asyncio
from typing import Any

from verifiers.rewards.judge_reward import BinaryJudgeRewarder, JudgeRewarder
from verifiers.rewards.reward import Reward
from verifiers.rubrics.multistep.requirement import Requirement
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

    async def __call__(self, scenario: Scenario, **kwargs):
        """Evaluate the requirement using judge reward against a scenario."""
        question = self.requirement.question

        # Handle missing answers gracefully in reference-guided evaluation
        if scenario.answers is None or self.requirement.name not in scenario.answers:
            print(
                f"Warning: No answer provided for requirement '{self.requirement.name}', skipping evaluation"
            )
            return 0.0  # Return neutral score when answer is missing

        # Extract answer value from the new format
        answer_data = scenario.answers[self.requirement.name]
        if isinstance(answer_data, dict) and "answer" in answer_data:
            answer: float | str = answer_data["answer"]
        else:
            # Fallback for old format - answer_data is the direct value
            answer = answer_data  # type: ignore[assignment]

        content = scenario.to_content()
        judge_result = await self.judge_rewarder(question, content, answer, **kwargs)

        # Extract numeric answer from JudgeResponse
        return judge_result.answer

    def get_dependencies(self):
        """Get the dependencies for this requirement."""
        return self.requirement.dependencies


class BinaryRequirementRewardNode(RequirementJudgeRewardNode):
    """
    Special subclass of the RequirementJudgeRewardNode for binary requirements.
    This is the main node used in workflows with binary branching.
    """

    def __init__(self, requirement: Any, judge_rewarder: BinaryJudgeRewarder):
        """Initialize a binary requirement judge reward node."""
        super().__init__(requirement, judge_rewarder)


# TODO: more node types
