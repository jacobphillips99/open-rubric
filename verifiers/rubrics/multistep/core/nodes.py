from typing import Any

from verifiers.rewards.judge_reward import JudgeRewarder, BinaryJudgeRewarder
from verifiers.rewards.reward import Reward
from verifiers.rubrics.multistep.core.scenario import Scenario
from verifiers.rubrics.multistep.core.requirement import Requirement


class RequirementRewardNode:
    """
    Basic node in a workflow for evaluating requirements.
    Nodes combine Requirements and Rewards, and are used to evaluate a scenario.
    """
    def __init__(self, requirement: Requirement, reward: Reward):
        self.requirement = requirement
        self.reward = reward
        self.name = requirement.name

    async def __call__(self, scenario: Scenario, **kwargs):
        return await self.reward(scenario, **kwargs)
    

class RequirementJudgeRewardNode(RequirementRewardNode):
    """
    Special class where the Reward function is a JudgeRewarder.
    This is used to evaluate the correctness of the response.
    """
    def __init__(self, requirement: Requirement, judge_rewarder: JudgeRewarder):
        self.requirement = requirement
        self.judge_rewarder = judge_rewarder
        self.name = requirement.name
    
    async def __call__(self, scenario: Scenario, **kwargs):
        question = self.requirement.question
        
        # Handle missing answers gracefully in reference-guided evaluation
        if self.requirement.name not in scenario.answers:
            print(f"Warning: No answer provided for requirement '{self.requirement.name}', skipping evaluation")
            return 0.0  # Return neutral score when answer is missing
        
        # Extract answer value from the new format
        answer_data = scenario.answers[self.requirement.name]
        if isinstance(answer_data, dict) and "answer" in answer_data:
            answer = answer_data["answer"]
        else:
            # Fallback for old format
            answer = answer_data
            
        content = scenario.to_content()
        judge_result = await self.judge_rewarder(question, content, answer, **kwargs)
        
        # Extract numeric answer from JudgeResponse
        return judge_result.answer
    
    def get_dependencies(self):
        return self.requirement.dependencies


class BinaryRequirementRewardNode(RequirementJudgeRewardNode):
    """
    Special subclass of the RequirementJudgeRewardNode for binary requirements.
    This is the main node used in workflows with binary branching.
    """
    def __init__(self, requirement: Any, judge_rewarder: BinaryJudgeRewarder):
        super().__init__(requirement, judge_rewarder) 


# TODO: more node types