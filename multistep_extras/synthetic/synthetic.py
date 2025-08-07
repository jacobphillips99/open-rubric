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
import traceback
from pathlib import Path
from typing import Optional

from openai import OpenAI

from .generate_hidden_descriptions import (generate_hidden_descriptions_async,
                                           load_rubric_from_path)
from .generate_scenarios import generate_scenarios_parallel, save_scenarios

# Hugging Face datasets
from datasets import Dataset, DatasetDict
import os
import json


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
        output_dir = "."
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
        requirements=rubric.requirements,
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
        requirements=rubric.requirements,
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
    """Create HF datasets splits locally and push to Hub."""
    hf_dir = Path(output_dir) / "hf"
    hf_dir.mkdir(parents=True, exist_ok=True)

    hidden_path = hf_dir / "hidden.jsonl"
    scenarios_path = hf_dir / "scenarios.jsonl"

    # Normalize hidden descriptions
    hidden_rows = []
    for d in hidden_descriptions:
        hidden_rows.append(
            {
                "id": d.get("id"),
                "title": d.get("title"),
                "hidden_description": d.get("hidden_description"),
            }
        )

    # Map scenario rows with linkage to hidden id if available
    scenario_rows = []
    for idx, s in enumerate(scenarios):
        scenario_rows.append(
            {
                "id": idx,
                "name": getattr(s, "name", None),
                "description": getattr(s, "description", None),
                "prompt": getattr(s, "prompt", None),
                "answers": getattr(s, "answers", None),
                "revealed_info": getattr(s, "revealed_info", None),
                "_hidden_description": getattr(s, "_hidden_description", None),
                # Best-effort linkage: assume same order
                "source_id": hidden_descriptions[idx].get("id") if idx < len(hidden_descriptions) else None,
            }
        )

    # Write JSONL locally
    with open(hidden_path, "w") as f:
        for row in hidden_rows:
            f.write(json.dumps(row) + "\n")
    with open(scenarios_path, "w") as f:
        for row in scenario_rows:
            f.write(json.dumps(row) + "\n")

    # Build DatasetDict
    hidden_ds = Dataset.from_list(hidden_rows)
    scenarios_ds = Dataset.from_list(scenario_rows)
    ds_dict = DatasetDict({"hidden": hidden_ds, "scenarios": scenarios_ds})

    # Resolve token
    resolved_token = token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
    push_kwargs = {"private": private}
    if branch:
        push_kwargs["branch"] = branch

    ds_dict.push_to_hub(repo_id=repo_id, token=resolved_token, **push_kwargs)
    print(f"Pushed dataset to Hugging Face Hub: {repo_id}")


async def main() -> None:
    """Main entry point for the full synthetic scenario generation pipeline."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic scenarios - full pipeline from rubric to scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 10 scenarios from a rubric directory
  python synthetic.py /path/to/rubric --num-descriptions 10

  # Use custom model and output directory
  python synthetic.py /path/to/rubric --model gpt-4.1-turbo --output-dir ./outputs

  # High concurrency for faster generation
  python synthetic.py /path/to/rubric --max-concurrent 20
        """,
    )
    parser.add_argument(
        "rubric_path",
        help="Path to rubric directory or requirements file",
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
        help="Output directory for generated files (default: current directory)",
    )
    parser.add_argument(
        "--no-intermediates",
        action="store_true",
        help="Don't save intermediate hidden descriptions file",
    )

    args = parser.parse_args()

    try:
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
