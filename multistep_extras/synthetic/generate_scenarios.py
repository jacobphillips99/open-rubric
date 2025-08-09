"""
Generate scenarios from hidden descriptions using a rubric.

This script takes hidden descriptions and a rubric to generate complete scenarios
with prompts, answers, and revealed information.
"""

import argparse
import asyncio
import json
import traceback
from pathlib import Path
from typing import Optional

from openai import OpenAI

from multistep_extras.builders.scenario_generator import \
    generate_scenario_from_hidden_description
from example_rubrics import get_workflow, list_workflows
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.scenario import Scenario


async def generate_scenario_async(
    hidden_description: str,
    requirements: list,
    scenario_id: int,
    title: str = "",
    model: str = "gpt-4.1-nano",
    client: Optional[OpenAI] = None,
    model_kwargs: Optional[dict] = None,
) -> tuple[int, Scenario]:
    """
    Generate a scenario asynchronously.

    Args:
        hidden_description: The hidden description to generate scenario from
        requirements: List of requirements from the rubric
        scenario_id: ID for tracking this scenario
        title: Title of the scenario
        model: Model to use for generation
        client: OpenAI client to use
        model_kwargs: Additional model parameters

    Returns:
        Tuple of (scenario_id, generated_scenario)
    """
    try:
        scenario = generate_scenario_from_hidden_description(
            hidden_description=hidden_description,
            requirements=requirements,
            name=f"synthetic_scenario_{scenario_id}",
            description=title or f"Generated scenario {scenario_id}",
            model=model,
            client=client,
            model_kwargs=model_kwargs,
        )
        return scenario_id, scenario
    except Exception as e:
        print(f"Error generating scenario {scenario_id}: {e}")
        raise


async def generate_scenarios_parallel(
    hidden_descriptions: list[dict],
    requirements: list,
    model: str = "gpt-4.1-nano",
    client: Optional[OpenAI] = None,
    model_kwargs: Optional[dict] = None,
    max_concurrent: int = 5,
) -> list[Scenario]:
    """
    Generate scenarios in parallel from hidden descriptions.

    Args:
        hidden_descriptions: List of hidden description dicts with 'hidden_description' field
        requirements: List of requirements from the rubric
        model: Model to use for generation
        client: OpenAI client to use
        model_kwargs: Additional model parameters
        max_concurrent: Maximum concurrent generations

    Returns:
        List of generated scenarios
    """
    if client is None:
        client = OpenAI()

    if model_kwargs is None:
        model_kwargs = {}

    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_concurrent)

    async def generate_with_semaphore(hidden_desc_dict: dict, idx: int):
        async with semaphore:
            return await generate_scenario_async(
                hidden_description=hidden_desc_dict["hidden_description"],
                requirements=requirements,
                scenario_id=idx,
                title=hidden_desc_dict.get("title", ""),
                model=model,
                client=client,
                model_kwargs=model_kwargs,
            )

    # Create tasks for all scenarios
    tasks = [
        generate_with_semaphore(desc, idx)
        for idx, desc in enumerate(hidden_descriptions)
    ]

    print(
        f"Generating {len(tasks)} scenarios with max {max_concurrent} concurrent requests..."
    )

    # Run all tasks and gather results
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and handle exceptions
    scenarios = []
    for result in results:
        if isinstance(result, Exception):
            print(f"Failed to generate scenario: {result}")
            continue

        if isinstance(result, tuple) and len(result) == 2:
            scenario_id, scenario = result
        else:
            # This shouldn't happen if result isn't an exception, but being safe
            continue
        scenarios.append(scenario)
        print(f"✓ Generated scenario {scenario_id}: {scenario.description}")

    return scenarios


def load_hidden_descriptions(file_path: str) -> list[dict]:
    """Load hidden descriptions from a JSON file."""
    with open(file_path, "r") as f:
        data = json.load(f)

    # Handle both formats: direct list or nested under 'descriptions' key
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "descriptions" in data:
        return data["descriptions"]
    else:
        raise ValueError(
            f"Invalid format in {file_path}. Expected list or dict with 'descriptions' key."
        )


def load_rubric_from_path(rubric_path: str) -> MultiStepRubric:
    """Load a rubric from a directory path or built-in workflow name."""
    # Support built-in example workflows by short name
    try:
        available = set(list_workflows())
    except Exception:
        available = set()

    if rubric_path in available:
        requirements, _scenarios = get_workflow(rubric_path)

        class _SimpleRubric:
            def __init__(self, reqs):
                self.requirements = reqs

        return _SimpleRubric(requirements)  # type: ignore[return-value]

    rubric_path_obj = Path(rubric_path)

    if rubric_path_obj.is_dir():
        return MultiStepRubric.load(rubric_path_obj, "rubric")
    if rubric_path_obj.name.endswith("_requirements.yaml"):
        directory = rubric_path_obj.parent
        base_name = rubric_path_obj.name[: -len("_requirements.yaml")]
        return MultiStepRubric.load(directory, base_name)

    raise ValueError(
        f"Invalid rubric input: {rubric_path}. Expected a directory, a file ending with '_requirements.yaml', or one of {sorted(available) if available else '[no built-ins found]'}"
    )


def save_scenarios(scenarios: list[Scenario], output_file: str) -> None:
    """Save scenarios to a YAML file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save scenarios using the built-in save method
    Scenario.save_multiple(scenarios, output_path)


async def main() -> int:
    """Main entry point for generating scenarios from hidden descriptions."""
    parser = argparse.ArgumentParser(
        description="Generate scenarios from hidden descriptions using a rubric"
    )
    parser.add_argument(
        "rubric_path",
        help="Path to rubric directory or requirements file",
    )
    parser.add_argument(
        "hidden_descriptions_file",
        help="JSON file containing list of hidden descriptions",
    )
    parser.add_argument(
        "output_file",
        help="Output YAML file to save generated scenarios",
    )
    parser.add_argument(
        "--model",
        default="gpt-4.1-nano",
        help="Model to use for generation (default: gpt-4.1-nano)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="Temperature for generation (default: 0.1)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=5,
        help="Maximum concurrent requests (default: 5)",
    )

    args = parser.parse_args()

    try:
        # Load rubric
        print(f"Loading rubric from {args.rubric_path}...")
        rubric = load_rubric_from_path(args.rubric_path)
        print(f"Loaded rubric with {len(rubric.requirements)} requirements")

        # Load hidden descriptions
        print(f"Loading hidden descriptions from {args.hidden_descriptions_file}...")
        hidden_descriptions = load_hidden_descriptions(args.hidden_descriptions_file)
        print(f"Loaded {len(hidden_descriptions)} hidden descriptions")

        # Generate scenarios in parallel
        client = OpenAI()
        model_kwargs = {"temperature": args.temperature}

        scenarios = await generate_scenarios_parallel(
            hidden_descriptions=hidden_descriptions,
            requirements=list(rubric.requirements),
            model=args.model,
            client=client,
            model_kwargs=model_kwargs,
            max_concurrent=args.max_concurrent,
        )

        # Save scenarios
        save_scenarios(scenarios, args.output_file)
        print(f"Saved {len(scenarios)} scenarios to {args.output_file}")

        # Print summary
        for scenario in scenarios:
            print(f"  - {scenario.name}: {scenario.description}")

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
