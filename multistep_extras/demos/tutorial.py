"""Comprehensive tutorial for the MultiStep Rubric System."""

import asyncio
from collections.abc import Sequence

from multistep_extras.example_rubrics import (debugging_reqs,
                                              debugging_scenarios,
                                              first_responder_reqs, scenarios)
from verifiers.rewards.judge_reward import (JUDGE_PROMPT, BinaryJudgeRewarder,
                                            UnitVectorJudgeRewarder)
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.requirement import (BinaryRequirement,
                                                     Requirement)
from verifiers.rubrics.multistep.reward_strategies import (
    CompletionRatioRewardStrategy, LevelWeightedRewardStrategy,
    ProgressiveRewardStrategy, RewardStrategy, SumRewardStrategy)
from verifiers.rubrics.multistep.scenario import Scenario


class MultiStepTutorial:
    """Interactive tutorial for learning the MultiStep Rubric System."""

    def __init__(self) -> None:
        """Initialize the tutorial with default judge configuration."""
        self.judge_options = [
            BinaryJudgeRewarder(judge_prompt=JUDGE_PROMPT),
            UnitVectorJudgeRewarder(judge_prompt=JUDGE_PROMPT),
        ]

    def create_simple_workflow(
        self,
    ) -> tuple[Sequence[Requirement], Sequence[Scenario]]:
        """
        Create a simple 3-step workflow for demonstration.

        Returns:
            tuple: (requirements, scenarios)
        """
        # Simple decision tree: Check prerequisites -> Make decision -> Take action
        check_prerequisites = BinaryRequirement(
            name="check_prerequisites",
            question="Does the response check if all prerequisites are met?",
            dependencies={
                1.0: ["make_decision"],  # If prerequisites checked, make decision
                0.0: [],  # If not checked, workflow stops
            },
        )

        make_decision = BinaryRequirement(
            name="make_decision",
            question="Does the response make a clear decision?",
            dependencies={
                1.0: ["take_action"],  # If decision made, take action
                0.0: [],  # If no decision, workflow stops
            },
        )

        take_action = BinaryRequirement(
            name="take_action",
            question="Does the response specify what action to take?",
        )

        requirements = [check_prerequisites, make_decision, take_action]

        # Create a scenario that follows the complete workflow
        scenario = Scenario(
            prompt="Should we deploy the new feature to production?",
            completion="First, let me check if we've completed all testing and QA. Yes, all tests are passing and security review is complete. Based on this, I recommend we proceed with deployment. We should deploy during the maintenance window tonight.",
            answers={
                "check_prerequisites": {
                    "answer": 1.0,
                    "reasoning": "Response explicitly checks prerequisites",
                },
                "make_decision": {
                    "answer": 1.0,
                    "reasoning": "Response makes clear recommendation to deploy",
                },
                "take_action": {
                    "answer": 1.0,
                    "reasoning": "Response specifies deployment timing",
                },
            },
        )

        return requirements, [scenario]

    async def demonstrate_evaluation_modes(self) -> None:
        """Demonstrate different evaluation modes."""
        print("=== EVALUATION MODES ===\n")

        requirements, demo_scenarios = self.create_simple_workflow()
        scenario = demo_scenarios[0]  # Use successful scenario

        print("Scenario: Should we deploy the new feature to production?")
        print("Response: Checks prerequisites -> Makes decision -> Takes action\n")

        # 1. MODEL_GUIDED - Follow the model's actual answers
        print("1. MODEL_GUIDED Mode:")
        print("   Follows the model's actual answers through the dependency graph")
        model_guided_rubric = MultiStepRubric(
            requirements,
            self.judge_options,
            reward_strategy=SumRewardStrategy(),
        )
        result = await model_guided_rubric.evaluate(scenario)
        print(f"   Result: {result}")
        print("   Path taken: Level 0 -> Level 1 -> Level 2\n")

        # 2. REFERENCE_GUIDED - Follow ground truth answers
        print("2. REFERENCE_GUIDED Mode:")
        print("   Follows the ground truth answers through the dependency graph")
        reference_guided_rubric = MultiStepRubric(
            requirements,
            self.judge_options,
            reward_strategy=SumRewardStrategy(),
        )
        ground_truth: dict[str, float] = {
            "check_prerequisites": 1.0,
            "make_decision": 1.0,
            "take_action": 1.0,
        }
        result = await reference_guided_rubric.evaluate(
            scenario,
            ground_truth_answers=ground_truth,
        )
        print(f"   Result: {result}")
        print("   Only evaluates requirements in the 'correct' path\n")

        # 3. EXHAUSTIVE - Evaluate everything
        print("3. EXHAUSTIVE Mode:")
        print("   Evaluates all requirements regardless of dependencies")
        exhaustive_rubric = MultiStepRubric(
            requirements,
            self.judge_options,
            reward_strategy=SumRewardStrategy(),
        )
        result = await exhaustive_rubric.evaluate(scenario)
        print(f"   Result: {result}")
        print(f"   Evaluates all {len(requirements)} requirements\n")

        # 4. ADAPTIVE - Stop when can't proceed
        print("4. ADAPTIVE Mode:")
        print("   Stops gracefully when no valid path forward exists")
        adaptive_rubric = MultiStepRubric(
            requirements,
            self.judge_options,
            reward_strategy=SumRewardStrategy(),
        )
        result = await adaptive_rubric.evaluate(scenario)
        print(f"   Result: {result}")
        print("   Evaluates requirements based on dependency satisfaction\n")

    async def demonstrate_reward_strategies(self) -> None:
        """Demonstrate different reward calculation strategies."""
        print("=== REWARD STRATEGIES ===\n")

        # Use the debugging workflow for variety
        scenario = debugging_scenarios[0]

        strategies: list[tuple[str, RewardStrategy]] = [
            ("Sum", SumRewardStrategy()),
            ("Level Weighted", LevelWeightedRewardStrategy()),
            (
                "Progressive",
                ProgressiveRewardStrategy(),
            ),
            (
                "Completion Ratio",
                CompletionRatioRewardStrategy(),
            ),
        ]

        print("Testing different reward strategies on debugging workflow:")
        print("Scenario: E-commerce checkout failing for orders over $100\n")

        for name, strategy in strategies:
            rubric = MultiStepRubric(
                debugging_reqs, self.judge_options, reward_strategy=strategy
            )

            # Convert scenario.answers to ground_truth_answers format
            ground_truth_answers: dict[str, float] = {}
            if scenario.answers:
                for name, data in scenario.answers.items():
                    if isinstance(data, dict) and "answer" in data:
                        answer_value = data["answer"]
                        if isinstance(answer_value, (int, float)):
                            ground_truth_answers[name] = float(answer_value)

            result = await rubric.score_rollout(
                prompt=scenario.prompt,
                completion=scenario.completion or "",
                answer=scenario.answers,
                state={},
                ground_truth_answers=ground_truth_answers,
            )

            print(f"{name} Strategy:")
            print(f"  Reward: {result['reward']:.3f}")
            print(f"  Logic: {self._explain_strategy(strategy)}")
            print()

    def _explain_strategy(self, strategy: RewardStrategy) -> str:
        """Provide human-readable explanation of reward strategy."""
        if isinstance(strategy, SumRewardStrategy):
            return "Simple sum of all requirement scores"
        elif isinstance(strategy, LevelWeightedRewardStrategy):
            return "Weighted sum where deeper levels get higher weights"
        elif isinstance(strategy, ProgressiveRewardStrategy):
            return "Exponentially increasing rewards for deeper levels"
        elif isinstance(strategy, CompletionRatioRewardStrategy):
            return "Combines completion ratio with average score quality"
        else:
            return "Custom reward calculation"

    async def demonstrate_workflow_comparison(self) -> None:
        """Compare different workflow structures."""
        print("=== WORKFLOW STRUCTURE COMPARISON ===\n")

        # Compare first responder (wide branching) vs debugging (narrow sequential)
        workflows: list[tuple[str, Sequence[Requirement], Scenario]] = [
            ("First Responder", first_responder_reqs, scenarios[0]),
            ("Software Debugging", debugging_reqs, debugging_scenarios[0]),
        ]

        print("Comparing workflow structures:\n")

        for name, requirements, scenario in workflows:
            rubric = MultiStepRubric(
                requirements,
                self.judge_options,
                reward_strategy=CompletionRatioRewardStrategy(),
            )

            result = await rubric.evaluate(scenario)

            # TODO: fixme and add evaluation output type
            print(f"{name} Workflow:")
            print(f"  Requirements: {len(requirements)}")
            print(f"  Levels: {len(rubric.levels)}")
            print(f"  Completion ratio: {result.completion_ratio:.2%}")
            print(f"  Total reward: {result.total_reward:.3f}")
            print()

    async def demonstrate_custom_workflow(self) -> None:
        """Show how to create custom workflows from scratch."""
        print("=== CUSTOM WORKFLOW CREATION ===\n")

        # Create a customer service workflow
        acknowledge_issue = BinaryRequirement(
            name="acknowledge_issue",
            question="Does the response acknowledge the customer's specific problem?",
            dependencies={1.0: ["check_account"], 0.0: []},
        )

        check_account = BinaryRequirement(
            name="check_account",
            question="Does the response check the customer's account status?",
            dependencies={1.0: ["provide_solution"], 0.0: []},
        )

        provide_solution = BinaryRequirement(
            name="provide_solution",
            question="Does the response provide a specific solution to the problem?",
        )

        requirements = [acknowledge_issue, check_account, provide_solution]

        scenario = Scenario(
            prompt="Customer: I can't access my account and my payment was declined. What's going on?",
            completion="I understand you're having trouble accessing your account and your payment was declined. Let me check your account status right now... I see there's a security hold on your account due to unusual activity. I'm removing that hold now, and your account should be accessible within 5 minutes.",
            answers={
                "acknowledge_issue": {
                    "answer": 1.0,
                    "reasoning": "Response acknowledges the customer's issue with their locked account and inability to access funds",
                },
                "check_account": {
                    "answer": 1.0,
                    "reasoning": "Response explicitly checks account status and identifies the security hold issue",
                },
                "provide_solution": {
                    "answer": 1.0,
                    "reasoning": "Response provides a clear solution by removing the hold and gives specific timeline (5 minutes)",
                },
            },
        )

        rubric = MultiStepRubric(
            requirements,
            self.judge_options,
            reward_strategy=LevelWeightedRewardStrategy(),
        )

        result = await rubric.score_rollout(
            prompt=scenario.prompt,
            completion=scenario.completion or "",
            answer=scenario.answers,
            state={},
        )

        print("Custom Customer Service Workflow Results:")
        print(f"  Reward: {result['reward']:.3f}")
        print(f"  Mode: {result['mode']}")
        print(f"  State: {result['state']}")
        print()

    async def run_full_tutorial(self) -> None:
        """Run the complete tutorial."""
        print("🎓 MULTISTEP RUBRIC SYSTEM TUTORIAL 🎓\n")
        print("This tutorial will walk you through all features of the system.\n")

        await self.demonstrate_evaluation_modes()
        await self.demonstrate_reward_strategies()
        await self.demonstrate_workflow_comparison()
        await self.demonstrate_custom_workflow()

        print("=== TUTORIAL COMPLETE ===")
        print("You now know how to:")
        print("✓ Create workflows with dependencies")
        print("✓ Use different evaluation modes")
        print("✓ Configure reward strategies")
        print("✓ Handle different workflow structures")
        print("✓ Create custom workflows from scratch")


async def main():
    """Run the tutorial."""
    tutorial = MultiStepTutorial()
    await tutorial.run_full_tutorial()


if __name__ == "__main__":
    asyncio.run(main())
