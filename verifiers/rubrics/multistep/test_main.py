import asyncio

from .examples import first_responder_reqs, scenarios
from verifiers.rewards.judge_reward import BinaryJudgeRewarder

from .rubric import MultiStepRubric
from .enums import EvaluationMode
from .nodes import BinaryRequirementRewardNode
from .reward_strategies import (
    LevelWeightedRewardStrategy,
    SumRewardStrategy,
    MeanRewardStrategy,
    LevelBasedRewardStrategy,
    CompletionRatioRewardStrategy,
    ProgressiveRewardStrategy
)


async def main():
    judge_prompt = """
    Given a question and the ground truth answer, determine if the response is correct.
    Respond according to the judge response format.

    question={question}
    response={response}
    ground truth answer={answer}
    judge response format={judge_response_format}
    """

    scenario = scenarios[0]
    judge_rewarder = BinaryJudgeRewarder(judge_prompt=judge_prompt)
    
    # Example: Different reward strategies
    strategies = [
        ("level_weighted", LevelWeightedRewardStrategy(base_weight=1.0, level_multiplier=1.0)),
        ("sum", SumRewardStrategy()),
        ("mean", MeanRewardStrategy()),
        ("level_based", LevelBasedRewardStrategy(max_level_bonus=2.0, completion_bonus=1.0)),
        ("completion_ratio", CompletionRatioRewardStrategy(ratio_weight=2.0, quality_weight=1.0)),
        ("progressive", ProgressiveRewardStrategy(base_reward=1.0, growth_factor=1.5))
    ]
    
    print(f"Testing different reward strategies with scenario: {scenario.name or 'Scenario 0'}")
    print("=" * 80)
    
    for strategy_name, strategy in strategies:
        rubric = MultiStepRubric(
            first_responder_reqs, 
            judge_rewarder, 
            node_factory=BinaryRequirementRewardNode,
            reward_strategy=strategy
        )
        
        # Convert scenario.answers to ground_truth_answers format for compatibility
        ground_truth_answers = {}
        for req_name, answer_data in scenario.answers.items():
            if isinstance(answer_data, dict) and "answer" in answer_data:
                ground_truth_answers[req_name] = answer_data["answer"]
            else:
                ground_truth_answers[req_name] = answer_data
        
        result = await rubric.score_rollout(
            prompt=scenario.prompt,
            completion=scenario.completion,
            answer=scenario.answers,
            state={},
            mode=EvaluationMode.REFERENCE_GUIDED,
            ground_truth_answers=ground_truth_answers
        )
        
        print(f"\n{strategy_name.upper()} Strategy:")
        print(f"  Reward: {result['reward']:.3f}")
        print(f"  Strategy: {result.get('reward_strategy', 'unknown')}")
        print(f"  Terminal Condition: {result.get('terminal_condition', 'completed')}")
        if 'completion_ratio' in result:
            print(f"  Completion Ratio: {result['completion_ratio']:.3f}")
    
    print("\n" + "=" * 80)
    print("Reward Strategy Comparison Complete!")


if __name__ == "__main__":
    result = asyncio.run(main()) 