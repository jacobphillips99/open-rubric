"""
Main entrypoint for synthetic scenario generation.

This script orchestrates the full pipeline:
1. Generate hidden descriptions from a rubric
2. Generate scenarios from those descriptions
3. Optionally combine and save results
"""

import argparse
import asyncio
import json
import os
import traceback
from pathlib import Path
from typing import Optional

from datasets import Dataset
from openai import OpenAI

from verifiers.rubrics.multistep.scenario import Scenario

from .generate_hidden_descriptions import (generate_hidden_descriptions_async,
                                           load_rubric_from_path)
from .generate_scenarios import generate_scenarios_parallel, save_scenarios


def load_existing_data(output_dir: str) -> tuple[list[dict], list[Scenario]]:
    """
    Load existing hidden descriptions and scenarios from output directory.

    Args:
        output_dir: Directory containing the generated files

    Returns:
        Tuple of (hidden_descriptions, scenarios)

    Raises:
        FileNotFoundError: If required files don't exist
        ValueError: If files can't be parsed
    """
    output_path = Path(output_dir)

    # Load hidden descriptions
    descriptions_file = output_path / "hidden_descriptions.json"
    if not descriptions_file.exists():
        raise FileNotFoundError(
            f"Hidden descriptions file not found: {descriptions_file}"
        )

    with open(descriptions_file) as f:
        hidden_descriptions = json.load(f)

    # Load scenarios
    scenarios_file = output_path / "synthetic_scenarios.yaml"
    if not scenarios_file.exists():
        raise FileNotFoundError(f"Scenarios file not found: {scenarios_file}")

    scenarios = Scenario.load_multiple(scenarios_file)

    return hidden_descriptions, scenarios


async def push_to_huggingface_only(
    output_dir: str,
    hf_repo_id: str,
    hf_private: bool = False,
    hf_branch: Optional[str] = None,
    hf_token: Optional[str] = None,
) -> None:
    """
    Load existing data and push to Hugging Face Hub without regenerating.

    Args:
        output_dir: Directory containing the generated files
        hf_repo_id: Hugging Face Hub repo id
        hf_private: Whether to create private repo
        hf_branch: Target branch on the Hub
        hf_token: Hugging Face token
    """
    print(f"Loading existing data from {output_dir}...")
    hidden_descriptions, scenarios = load_existing_data(output_dir)

    print(
        f"Loaded {len(hidden_descriptions)} hidden descriptions and {len(scenarios)} scenarios"
    )
    print(f"Pushing to Hugging Face Hub: {hf_repo_id}")

    _export_and_push_to_hub(
        hidden_descriptions=hidden_descriptions,
        scenarios=scenarios,
        output_dir=output_dir,
        repo_id=hf_repo_id,
        private=hf_private,
        branch=hf_branch,
        token=hf_token,
    )


async def full_synthetic_pipeline(
    rubric_path: str,
    num_descriptions: int = 5,
    model: str = "gpt-4.1-nano",
    hidden_temperature: float = 0.7,
    scenario_temperature: float = 0.1,
    max_concurrent: int = 5,
    output_dir: Optional[str] = None,
    save_intermediates: bool = True,
    hf_repo_id: Optional[str] = None,
    hf_private: bool = False,
    hf_branch: Optional[str] = None,
    hf_token: Optional[str] = None,
    no_push: bool = False,
) -> tuple[list[dict], list]:
    """
    Run the full synthetic scenario generation pipeline.

    Args:
        rubric_path: Path to rubric directory or file
        num_descriptions: Number of hidden descriptions to generate
        model: Model to use for generation
        temperature: Temperature for generation
        max_concurrent: Maximum concurrent requests for scenario generation
        output_dir: Directory to save outputs (if None, uses current directory)
        save_intermediates: Whether to save intermediate hidden descriptions

    Returns:
        Tuple of (hidden_descriptions, scenarios)
    """
    if output_dir is None:
        # Default to outputs/ folder at project root (same level as multistep_extras)
        current_file = Path(__file__)
        project_root = (
            current_file.parent.parent.parent
        )  # Go up from synthetic/ -> multistep_extras/ -> project_root/
        output_dir = str(project_root / "outputs")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    client = OpenAI()
    hidden_model_kwargs = {"temperature": hidden_temperature}
    scenario_model_kwargs = {"temperature": scenario_temperature}

    # Step 1: Load rubric
    print(f"Loading rubric from {rubric_path}...")
    rubric = load_rubric_from_path(rubric_path)
    print(f"Loaded rubric with {len(rubric.requirements)} requirements")

    # Step 2: Generate hidden descriptions
    print(f"Generating {num_descriptions} hidden descriptions...")
    hidden_descriptions = await generate_hidden_descriptions_async(
        requirements=list(rubric.requirements),
        num_descriptions=num_descriptions,
        model=model,
        client=client,
        model_kwargs=hidden_model_kwargs,
    )

    if save_intermediates:
        descriptions_file = output_path / "hidden_descriptions.json"
        with open(descriptions_file, "w") as f:
            json.dump(hidden_descriptions, f, indent=2)
        print(f"Saved hidden descriptions to {descriptions_file}")

    # Step 3: Generate scenarios
    print(f"Generating scenarios from {len(hidden_descriptions)} descriptions...")
    scenarios = await generate_scenarios_parallel(
        hidden_descriptions=hidden_descriptions,
        requirements=list(rubric.requirements),
        model=model,
        client=client,
        model_kwargs=scenario_model_kwargs,
        max_concurrent=max_concurrent,
    )

    # Step 4: Save scenarios
    scenarios_file = output_path / "synthetic_scenarios.yaml"
    save_scenarios(scenarios, str(scenarios_file))
    print(f"Saved {len(scenarios)} scenarios to {scenarios_file}")

    # Optionally build and push Hugging Face datasets
    if hf_repo_id and not no_push:
        _export_and_push_to_hub(
            hidden_descriptions=hidden_descriptions,
            scenarios=scenarios,
            output_dir=str(output_path),
            repo_id=hf_repo_id,
            private=hf_private,
            branch=hf_branch,
            token=hf_token,
        )

    return hidden_descriptions, scenarios


def _export_and_push_to_hub(
    hidden_descriptions: list[dict],
    scenarios: list,
    output_dir: str,
    repo_id: str,
    private: bool = False,
    branch: Optional[str] = None,
    token: Optional[str] = None,
) -> None:
    """Create simple two-column HF dataset and push to Hub."""
    hf_dir = Path(output_dir) / "hf"
    hf_dir.mkdir(parents=True, exist_ok=True)

    # Create simple question-answer pairs
    qa_rows = []
    for idx, scenario in enumerate(scenarios):
        # Question column: JSON with _hidden_description and prompt
        question_data = {
            "_hidden_description": getattr(scenario, "_hidden_description", None),
            "prompt": getattr(scenario, "prompt", None),
        }

        # Answer column: JSON with everything else
        answer_data = {
            "name": getattr(scenario, "name", None),
            "description": getattr(scenario, "description", None),
            "answers": getattr(scenario, "answers", None),
            "revealed_info": getattr(scenario, "revealed_info", None),
        }

        qa_rows.append(
            {
                "question": json.dumps(question_data),
                "answer": json.dumps(answer_data),
            }
        )

    # Write JSONL locally
    qa_path = hf_dir / "scenarios.jsonl"
    with open(qa_path, "w") as f:
        for row in qa_rows:
            f.write(json.dumps(row) + "\n")

    # Create README.md with proper metadata
    readme_content = f"""---
license: apache-2.0
language:
- en
task_categories:
- question-answering
tags:
- synthetic
- scenarios
- multistep-rubric
- open-rubric
pretty_name: "Open Rubric Synthetic Scenarios"
size_categories:
- 1K<n<10K
---

# Open Rubric Synthetic Scenarios

This dataset contains synthetically generated scenarios for multistep rubric evaluation.

## Dataset Description

This dataset was generated using the Open Rubric framework for creating synthetic evaluation scenarios. Each row contains a question-answer pair where:

- **question**: JSON containing the hidden description and prompt for the scenario
- **answer**: JSON containing the scenario details (name, description, answers, revealed_info)

## Dataset Structure

### Data Fields

- `question` (string): JSON string containing:
  - `_hidden_description`: The hidden context for scenario generation
  - `prompt`: The prompt presented to models being evaluated
- `answer` (string): JSON string containing:
  - `name`: Scenario name/title
  - `description`: Scenario description
  - `answers`: Expected answers or outcomes
  - `revealed_info`: Information revealed during the scenario

### Data Splits

The dataset contains {len(qa_rows)} synthetic scenarios in a single split.

## Usage

```python
from datasets import load_dataset
import json

dataset = load_dataset("{repo_id}")

# Access a single example
example = dataset["train"][0]
question_data = json.loads(example["question"])
answer_data = json.loads(example["answer"])

print(f"Prompt: {{question_data['prompt']}}")
print(f"Scenario: {{answer_data['name']}}")
```

## Citation

```bibtex
@misc{{open-rubric-synthetic,
  title={{Open Rubric Synthetic Scenarios}},
  author={{Open Rubric Contributors}},
  year={{2024}},
  url={{https://huggingface.co/datasets/{repo_id}}}
}}
```

## Dataset Creation

This dataset was generated using the Open Rubric synthetic scenario generation pipeline. See the [Open Rubric repository](https://github.com/open-rubric/open-rubric) for more details.
"""

    # Write README.md
    readme_path = hf_dir / "README.md"
    with open(readme_path, "w") as f:
        f.write(readme_content)

    # Build simple Dataset
    qa_ds = Dataset.from_list(qa_rows)

    # Resolve token
    resolved_token = (
        token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
    )
    push_kwargs = {"private": private}
    if branch:
        push_kwargs["branch"] = branch

    qa_ds.push_to_hub(repo_id=repo_id, token=resolved_token, **push_kwargs)
    print(f"Pushed dataset to Hugging Face Hub: {repo_id}")


async def main() -> int:
    """Main entry point for the full synthetic scenario generation pipeline."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic scenarios - full pipeline from rubric to scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 10 scenarios from a rubric directory
  python synthetic.py /path/to/rubric --num-descriptions 10

  # Use custom model and output directory
  python synthetic.py /path/to/rubric --model gpt-4.1 --output-dir ./outputs

  # High concurrency for faster generation
  python synthetic.py /path/to/rubric --max-concurrent 20

  # Push existing data to Hugging Face Hub without regenerating
  python synthetic.py --push-only --hf-repo-id jacobphillips99/open-rubric-first-responder-scenarios --output-dir ./outputs

  # Push with custom Hub settings
  python synthetic.py --push-only --hf-repo-id username/my_scenarios --hf-private --hf-branch main

  # Generate first responder scenarios and push to existing repo
  python synthetic.py first_responder --num-descriptions 50 --hf-repo-id jacobphillips99/open-rubric-first-responder-scenarios
        """,
    )
    parser.add_argument(
        "rubric_path",
        nargs="?",
        help="Path to rubric directory or requirements file (not needed for --push-only)",
    )
    parser.add_argument(
        "--num-descriptions",
        type=int,
        default=5,
        help="Number of hidden descriptions to generate (default: 5)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4.1-nano",
        help="Model to use for generation (default: gpt-4.1-nano)",
    )
    parser.add_argument(
        "--hidden-temp",
        type=float,
        default=0.7,
        help="Temperature for hidden description generation (default: 0.7)",
    )
    parser.add_argument(
        "--scenario-temp",
        type=float,
        default=0.1,
        help="Temperature for scenario generation (default: 0.1)",
    )
    # Hugging Face upload options
    parser.add_argument(
        "--hf-repo-id",
        type=str,
        help="Hugging Face Hub repo id (e.g., username/dataset_name) to push dataset",
    )
    parser.add_argument(
        "--hf-private",
        action="store_true",
        help="Create the dataset repo as private",
    )
    parser.add_argument(
        "--hf-branch",
        type=str,
        help="Target branch on the Hub (optional)",
    )
    parser.add_argument(
        "--hf-token",
        type=str,
        help="Hugging Face token (otherwise uses HF_TOKEN/HUGGINGFACE_HUB_TOKEN)",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Skip pushing to Hugging Face Hub even if --hf-repo-id is provided",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=5,
        help="Maximum concurrent requests for scenario generation (default: 5)",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for generated files (default: outputs/ folder at project root)",
    )
    parser.add_argument(
        "--no-intermediates",
        action="store_true",
        help="Don't save intermediate hidden descriptions file",
    )
    parser.add_argument(
        "--push-only",
        action="store_true",
        help="Skip generation and only push existing data to Hugging Face Hub (requires --hf-repo-id)",
    )

    args = parser.parse_args()

    try:
        # Handle push-only mode
        if args.push_only:
            if not args.hf_repo_id:
                print("Error: --hf-repo-id is required when using --push-only")
                return 1

            # Set default output directory if not provided
            if args.output_dir is None:
                current_file = Path(__file__)
                project_root = current_file.parent.parent.parent
                args.output_dir = str(project_root / "outputs")

            await push_to_huggingface_only(
                output_dir=str(args.output_dir),
                hf_repo_id=args.hf_repo_id,
                hf_private=args.hf_private,
                hf_branch=args.hf_branch,
                hf_token=args.hf_token,
            )

            print("\n✅ Push to Hugging Face Hub completed successfully!")
            return 0

        # Validate rubric_path for non-push-only mode
        if not args.rubric_path:
            print("Error: rubric_path is required when not using --push-only")
            return 1

        # Run full generation pipeline
        hidden_descriptions, scenarios = await full_synthetic_pipeline(
            rubric_path=args.rubric_path,
            num_descriptions=args.num_descriptions,
            model=args.model,
            hidden_temperature=args.hidden_temp,
            scenario_temperature=args.scenario_temp,
            max_concurrent=args.max_concurrent,
            output_dir=args.output_dir,
            save_intermediates=not args.no_intermediates,
            hf_repo_id=args.hf_repo_id,
            hf_private=args.hf_private,
            hf_branch=args.hf_branch,
            hf_token=args.hf_token,
            no_push=args.no_push,
        )

        # Print summary
        print("\n📊 Generation Summary:")
        print(f"  Hidden descriptions: {len(hidden_descriptions)}")
        print(f"  Generated scenarios: {len(scenarios)}")
        print(f"  Model used: {args.model}")
        print(f"  Hidden temp: {args.hidden_temp}")
        print(f"  Scenario temp: {args.scenario_temp}")

        print("\n📝 Generated scenarios:")
        for scenario in scenarios:
            print(f"  - {scenario.name}: {scenario.description}")

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
