"""
Demo script showing how to save and load MultiStepRubric workflows using the object-oriented API.

This example converts the first_responder workflow to YAML format
and demonstrates loading it back using methods on the objects themselves.
"""

from pathlib import Path

# Import the existing first responder workflow
from example_rubrics.first_responder import (requirements,
                                            scenarios)
from verifiers.rewards.judge_reward import JUDGE_PROMPT, BinaryJudgeRewarder
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.requirement import Requirement
from verifiers.rubrics.multistep.reward_strategies import \
    LevelWeightedRewardStrategy
from verifiers.rubrics.multistep.scenario import Scenario


def main():
    """Demonstrate saving and loading workflows using object methods."""
    judge_options = [
        BinaryJudgeRewarder(judge_prompt=JUDGE_PROMPT, judge_model="gpt-4o-mini")
    ]

    # Create reward strategy
    reward_strategy = LevelWeightedRewardStrategy(base_weight=1.0, level_multiplier=0.5)

    # Create the rubric
    rubric = MultiStepRubric(
        requirements=requirements,
        judge_options=judge_options,
        reward_strategy=reward_strategy,
    )

    # Create output directory
    output_dir = Path("outputs/workflows")

    # Save the rubric using object method
    print("Saving first responder rubric...")
    rubric.save(output_dir, "first_responder")

    # Save scenarios separately using class method
    print("Saving scenarios...")
    Scenario.save_multiple(scenarios, output_dir / "first_responder_scenarios.yaml")

    # Load it back using class methods
    print("\nLoading rubric back...")
    loaded_rubric = MultiStepRubric.load(output_dir, "first_responder")

    print("Loading scenarios back...")
    loaded_scenarios = Scenario.load_multiple(
        output_dir / "first_responder_scenarios.yaml"
    )

    # Verify it loaded correctly
    print("\nLoaded rubric successfully!")
    print(f"Requirements: {len(loaded_rubric.requirements)}")
    print(f"Judge options: {len(loaded_rubric.judge_options)}")
    print(f"Reward strategy: {loaded_rubric.reward_strategy.__class__.__name__}")
    print(f"Scenarios: {len(loaded_scenarios)}")

    # Show some requirements
    print("\nFirst few requirements:")
    for i, req in enumerate(loaded_rubric.requirements[:3]):
        print(f"  {i + 1}. {req.name}: {req.question}")
        if req.dependencies:
            print(f"     Dependencies: {req.dependencies}")

    # Show some scenarios
    print("\nFirst scenario:")
    scenario = loaded_scenarios[0]
    print(f"  Name: {scenario.name}")
    print(f"  Description: {scenario.description}")
    print(f"  Prompt: {scenario.prompt[:100]}...")

    # Test individual requirement serialization
    print("\nTesting individual requirement save/load...")
    first_req = requirements[0]
    req_file = output_dir / "test_requirement.yaml"
    first_req.save(req_file)
    # For single requirement, we need to save as multiple to use load_multiple
    Requirement.save_multiple([first_req], output_dir / "test_requirements_list.yaml")
    loaded_req = Requirement.load_multiple(output_dir / "test_requirements_list.yaml")[
        0
    ]
    print(f"Individual requirement loaded: {loaded_req.name} - {loaded_req.question}")

    # Test individual scenario serialization
    print("\nTesting individual scenario save/load...")
    first_scenario = scenarios[0]
    scenario_file = output_dir / "test_scenario.yaml"
    first_scenario.save(scenario_file)
    loaded_single_scenario = Scenario.load(scenario_file)
    print(f"Individual scenario loaded: {loaded_single_scenario.name}")

    print("\nDemo completed successfully!")
    print("\nFiles created:")
    for yaml_file in output_dir.glob("*.yaml"):
        print(f"  - {yaml_file.name}")


if __name__ == "__main__":
    main()
