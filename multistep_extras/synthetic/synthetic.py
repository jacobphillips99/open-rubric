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


async def full_synthetic_pipeline(
    rubric_path: str,
    num_descriptions: int = 5,
    model: str = "gpt-4.1-nano",
    temperature: float = 0.1,
    max_concurrent: int = 5,
    output_dir: Optional[str] = None,
    save_intermediates: bool = True,
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
    model_kwargs = {"temperature": temperature}

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
        model_kwargs=model_kwargs,
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
        model_kwargs=model_kwargs,
        max_concurrent=max_concurrent,
    )

    # Step 4: Save scenarios
    scenarios_file = output_path / "synthetic_scenarios.yaml"
    save_scenarios(scenarios, str(scenarios_file))
    print(f"Saved {len(scenarios)} scenarios to {scenarios_file}")

    return hidden_descriptions, scenarios


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
        "--temperature",
        type=float,
        default=0.1,
        help="Temperature for generation (default: 0.1)",
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
            temperature=args.temperature,
            max_concurrent=args.max_concurrent,
            output_dir=args.output_dir,
            save_intermediates=not args.no_intermediates,
        )

        # Print summary
        print("\n📊 Generation Summary:")
        print(f"  Hidden descriptions: {len(hidden_descriptions)}")
        print(f"  Generated scenarios: {len(scenarios)}")
        print(f"  Model used: {args.model}")
        print(f"  Temperature: {args.temperature}")

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
