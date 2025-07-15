"""
Comprehensive tutorial for the MultiStep Rubric System.

This tutorial demonstrates how to create, configure, and use multi-step rubrics
for complex dependency-based evaluations.
"""

import asyncio
from typing import Dict, Any

from verifiers.rubrics.multistep.core.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.core.scenario import Scenario
from verifiers.rubrics.multistep.core.enums import EvaluationMode, TerminalCondition
from verifiers.rubrics.multistep.core.reward_strategies import (
    LevelWeightedRewardStrategy,
    SumRewardStrategy,
    ProgressiveRewardStrategy,
    CompletionRatioRewardStrategy
)
from verifiers.rubrics.multistep.core.nodes import BinaryRequirementRewardNode
from verifiers.rubrics.multistep.examples import first_responder_reqs, debugging_reqs, scenarios, debugging_scenarios
from verifiers.rewards.judge_reward import BinaryJudgeRewarder


class MultiStepTutorial:
    """
    Interactive tutorial for learning the MultiStep Rubric System.
    """
    
    def __init__(self):
        self.judge_prompt = """
        Given a question and the ground truth answer, determine if the response is correct.
        Respond according to the judge response format.

        question={question}
        response={response}
        ground truth answer={answer}
        judge response format={judge_response_format}
        """
        self.judge_rewarder = BinaryJudgeRewarder(judge_prompt=self.judge_prompt)
    
    def create_simple_workflow(self) -> tuple[list[BinaryRequirement], list[Scenario]]:
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
                0.0: []  # If not checked, workflow stops
            }
        )
        
        make_decision = BinaryRequirement(
            name="make_decision", 
            question="Does the response make a clear decision based on the analysis?",
            dependencies={
                1.0: ["take_action"],  # If decision made, take action
                0.0: ["gather_more_info"]  # If no decision, gather more info
            }
        )
        
        # Terminal nodes
        take_action = BinaryRequirement(
            name="take_action",
            question="Does the response describe taking appropriate action?"
        )
        
        gather_more_info = BinaryRequirement(
            name="gather_more_info",
            question="Does the response describe gathering additional information?"
        )
        
        requirements = [check_prerequisites, make_decision, take_action, gather_more_info]
        
        # Sample scenarios
        scenarios = [
            Scenario(
                prompt="Should we deploy the new feature to production?",
                completion="I'll first check if all tests are passing, security review is complete, and stakeholders have approved. Since all prerequisites are met, I recommend we proceed with the deployment using our standard rollout process.",
                answers={
                    "check_prerequisites": {"answer": 1.0, "reasoning": "Explicitly checks tests, security, and approvals"},
                    "make_decision": {"answer": 1.0, "reasoning": "Makes clear recommendation to proceed"},
                    "take_action": {"answer": 1.0, "reasoning": "Describes using standard rollout process"}
                }
            ),
            Scenario(
                prompt="Should we deploy the new feature to production?", 
                completion="I need to check if the tests are complete first. Let me gather more information about the current test coverage and security review status before making a recommendation.",
                answers={
                    "check_prerequisites": {"answer": 0.0, "reasoning": "Realizes prerequisites aren't checked yet"},
                    "gather_more_info": {"answer": 1.0, "reasoning": "Describes gathering test and security info"}
                }
            )
        ]
        
        return requirements, scenarios
    
    async def demonstrate_evaluation_modes(self):
        """Demonstrate different evaluation modes with explanations."""
        print("=== EVALUATION MODES DEMONSTRATION ===\n")
        
        # Use simple workflow for clear demonstration
        requirements, demo_scenarios = self.create_simple_workflow()
        scenario = demo_scenarios[0]  # Use successful scenario
        
        rubric = MultiStepRubric(
            requirements,
            self.judge_rewarder,
            node_factory=BinaryRequirementRewardNode,
            reward_strategy=SumRewardStrategy()
        )
        
        print("Scenario: Should we deploy the new feature to production?")
        print("Response: Checks prerequisites -> Makes decision -> Takes action\n")
        
        # 1. MODEL_GUIDED - Follow the model's actual answers
        print("1. MODEL_GUIDED Mode:")
        print("   Follows the model's actual answers through the dependency graph")
        result = await rubric.evaluate(scenario, mode=EvaluationMode.MODEL_GUIDED)
        print(f"   Result: {result}")
        print(f"   Path taken: Level 0 -> Level 1 -> Level 2\n")
        
        # 2. REFERENCE_GUIDED - Follow ground truth answers  
        print("2. REFERENCE_GUIDED Mode:")
        print("   Follows the ground truth answers through the dependency graph")
        ground_truth = {
            "check_prerequisites": 1.0,
            "make_decision": 1.0, 
            "take_action": 1.0
        }
        result = await rubric.evaluate(scenario, mode=EvaluationMode.REFERENCE_GUIDED, 
                                     ground_truth_answers=ground_truth)
        print(f"   Result: {result}")
        print(f"   Only evaluates requirements in the 'correct' path\n")
        
        # 3. EXHAUSTIVE - Evaluate everything
        print("3. EXHAUSTIVE Mode:")
        print("   Evaluates all requirements regardless of dependencies")
        result = await rubric.evaluate(scenario, mode=EvaluationMode.EXHAUSTIVE)
        print(f"   Result: {result}")
        print(f"   Evaluates all {len(requirements)} requirements\n")
        
        # 4. ADAPTIVE - Stop when can't proceed
        print("4. ADAPTIVE Mode:")
        print("   Stops gracefully when no valid path forward exists")
        result = await rubric.evaluate(scenario, mode=EvaluationMode.ADAPTIVE)
        print(f"   Result: {result.to_dict()}")
        print(f"   Terminal condition: {result.terminal_condition.value}\n")
    
    async def demonstrate_reward_strategies(self):
        """Demonstrate different reward calculation strategies."""
        print("=== REWARD STRATEGIES DEMONSTRATION ===\n")
        
        # Use debugging workflow for variety
        scenario = debugging_scenarios[0]
        strategies = [
            ("Sum", SumRewardStrategy()),
            ("Level Weighted", LevelWeightedRewardStrategy(base_weight=1.0, level_multiplier=0.5)),
            ("Progressive", ProgressiveRewardStrategy(base_reward=1.0, growth_factor=1.2)),
            ("Completion Ratio", CompletionRatioRewardStrategy(ratio_weight=2.0, quality_weight=1.0))
        ]
        
        print("Testing different reward strategies on debugging workflow:")
        print("Scenario: E-commerce checkout failing for orders over $100\n")
        
        for name, strategy in strategies:
            rubric = MultiStepRubric(
                debugging_reqs,
                self.judge_rewarder, 
                reward_strategy=strategy
            )
            
            # Convert scenario.answers to ground_truth_answers format
            ground_truth_answers = {
                name: data["answer"] if isinstance(data, dict) else data
                for name, data in scenario.answers.items()
            }
            
            result = await rubric.score_rollout(
                prompt=scenario.prompt,
                completion=scenario.completion,
                answer=scenario.answers,
                state={},
                mode=EvaluationMode.REFERENCE_GUIDED,
                ground_truth_answers=ground_truth_answers
            )
            
            print(f"{name} Strategy:")
            print(f"  Reward: {result['reward']:.3f}")
            print(f"  Logic: {self._explain_strategy(strategy)}")
            print()
    
    def _explain_strategy(self, strategy) -> str:
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
    
    async def demonstrate_workflow_comparison(self):
        """Compare different workflow structures."""
        print("=== WORKFLOW STRUCTURE COMPARISON ===\n")
        
        # Compare first responder (wide branching) vs debugging (narrow sequential)
        workflows = [
            ("First Responder", first_responder_reqs, scenarios[0]),
            ("Software Debugging", debugging_reqs, debugging_scenarios[0])
        ]
        
        print("Comparing workflow structures:\n")
        
        for name, requirements, scenario in workflows:
            rubric = MultiStepRubric(
                requirements,
                self.judge_rewarder,
                reward_strategy=CompletionRatioRewardStrategy()
            )
            
            result = await rubric.evaluate(scenario, mode=EvaluationMode.ADAPTIVE)
            
            print(f"{name} Workflow:")
            print(f"  Total requirements: {len(requirements)}")
            print(f"  Completed: {len(result.completed_requirements)}")
            print(f"  Completion ratio: {result.completion_ratio:.3f}")
            print(f"  Terminal condition: {result.terminal_condition.value}")
            print(f"  Levels evaluated: {len(result.state)}")
            print()
    
    async def demonstrate_custom_workflow(self):
        """Show how to create a custom workflow from scratch."""
        print("=== CUSTOM WORKFLOW CREATION ===\n")
        
        print("Creating a simple customer service workflow...\n")
        
        # Customer service workflow
        identify_issue = BinaryRequirement(
            name="identify_issue",
            question="Does the response identify the customer's main issue?",
            dependencies={
                1.0: ["check_account", "gather_details"],
                0.0: ["ask_clarification"]
            }
        )
        
        check_account = BinaryRequirement(
            name="check_account", 
            question="Does the response check the customer's account status?",
            dependencies={
                1.0: ["provide_solution"],
                0.0: ["escalate_issue"]
            }
        )
        
        gather_details = BinaryRequirement(
            name="gather_details",
            question="Does the response gather additional details about the issue?", 
            dependencies={
                1.0: ["provide_solution"],
                0.0: ["ask_clarification"]
            }
        )
        
        # Terminal nodes
        provide_solution = BinaryRequirement(
            name="provide_solution",
            question="Does the response provide a clear solution to the customer?"
        )
        
        ask_clarification = BinaryRequirement(
            name="ask_clarification", 
            question="Does the response ask for clarification from the customer?"
        )
        
        escalate_issue = BinaryRequirement(
            name="escalate_issue",
            question="Does the response escalate the issue to appropriate personnel?"
        )
        
        requirements = [identify_issue, check_account, gather_details, 
                       provide_solution, ask_clarification, escalate_issue]
        
        scenario = Scenario(
            prompt="Customer calls saying their account is locked and they can't access their funds.",
            completion="I can see you're having trouble accessing your account. Let me check your account status - I see there's a security hold due to unusual activity. I'll remove this hold and send you a confirmation email. Your account should be accessible within 5 minutes.",
            answers={
                "identify_issue": {"answer": 1.0, "reasoning": "Identifies account access problem"},
                "check_account": {"answer": 1.0, "reasoning": "Checks account and finds security hold"},
                "provide_solution": {"answer": 1.0, "reasoning": "Provides clear solution and timeline"}
            }
        )
        
        rubric = MultiStepRubric(
            requirements,
            self.judge_rewarder,
            reward_strategy=LevelWeightedRewardStrategy()
        )
        
        result = await rubric.score_rollout(
            prompt=scenario.prompt,
            completion=scenario.completion, 
            answer=scenario.answers,
            state={},
            mode=EvaluationMode.REFERENCE_GUIDED
        )
        
        print("Custom Customer Service Workflow Results:")
        print(f"  Reward: {result['reward']:.3f}")
        print(f"  Mode: {result['mode']}")
        print(f"  State: {result['state']}")
        print()
    
    async def run_full_tutorial(self):
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