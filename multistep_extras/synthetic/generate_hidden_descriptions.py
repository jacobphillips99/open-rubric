"""
Generate hidden descriptions for scenarios based on a rubric.

This script takes a rubric and generates comprehensive hidden descriptions
that can later be used to create full scenarios with the scenario generator.
"""

import argparse
import asyncio
import json
import traceback
from pathlib import Path
from typing import Optional

from openai import OpenAI

from verifiers.parsers.xml_parser import XMLParser
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.requirement import Requirement

HIDDEN_DESCRIPTION_GENERATION_PROMPT = """
You are an expert scenario designer for evaluation rubrics. Your task is to generate comprehensive hidden descriptions that capture all the ground truth information needed to evaluate scenarios against a rubric.

RUBRIC REQUIREMENTS:
{requirements_text}

Based on these requirements, generate {num_descriptions} unique, comprehensive hidden descriptions. Each description should be a complete, detailed scenario that contains all the information needed to correctly evaluate every requirement in the rubric.

Each hidden description should include:
1. Complete environmental context and conditions
2. All relevant participant/subject details and status
3. All facts that would inform correct requirement answers
4. Timeline of events and current situation
5. Any hazards, complications, or special circumstances
6. Enough detail to derive appropriate initial prompts, ground truth answers, and progressive revelations

Format your response as valid JSON:
{{
    "descriptions": [
        {{
            "id": 1,
            "title": "Brief descriptive title",
            "hidden_description": "Comprehensive detailed description with all ground truth information..."
        }},
        {{
            "id": 2,
            "title": "Brief descriptive title",
            "hidden_description": "Comprehensive detailed description with all ground truth information..."
        }}
    ]
}}

Important guidelines:
- Each description should be self-contained and complete
- Include enough detail to determine correct answers for ALL requirements
- Vary the scenarios to cover different situations the rubric might encounter
- Make scenarios realistic and internally consistent
- Include both straightforward and edge case scenarios
- Ensure descriptions contain all facts needed for evaluation

Begin the response by first thinking about the response. Start with <think> and end with </think> once you have thought about your response.
Begin the actual valid JSON response inside <answer> and </answer>.
"""


async def generate_hidden_descriptions_async(
    requirements: list[Requirement],
    num_descriptions: int = 5,
    model: str = "gpt-4.1-nano",
    client: Optional[OpenAI] = None,
    model_kwargs: Optional[dict] = None,
) -> list[dict]:
    """
    Generate multiple hidden descriptions for scenarios based on rubric requirements.

    Args:
        requirements: List of requirements from the rubric
        num_descriptions: Number of descriptions to generate
        model: Model to use for generation
        client: OpenAI client to use
        model_kwargs: Additional model parameters

    Returns:
        List of dictionaries with id, title, and hidden_description
    """
    if model_kwargs is None:
        model_kwargs = {}

    if client is None:
        client = OpenAI()

    # Format requirements for prompt
    requirements_text = _format_requirements_for_prompt(requirements)

    # Build generation prompt
    prompt = HIDDEN_DESCRIPTION_GENERATION_PROMPT.format(
        requirements_text=requirements_text,
        num_descriptions=num_descriptions,
    )

    parser = XMLParser(fields=["think", "answer"])

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
        **model_kwargs,
    )

    parsed = parser.parse(response.choices[0].message.content)

    try:
        generated_data = json.loads(parsed.answer)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM response was not valid JSON: {e}; {traceback.format_exc()}"
        ) from e

    if "descriptions" not in generated_data:
        raise ValueError("Generated data missing 'descriptions' field")

    return generated_data["descriptions"]


def _format_requirements_for_prompt(requirements: list[Requirement]) -> str:
    """Format requirements list for inclusion in the generation prompt."""
    req_text = ""
    for req in requirements:
        req_text += f"- {req.name}: {req.question}\n"
        if req.dependencies:
            dep_info = []
            for score, deps in req.dependencies.items():
                if deps:
                    dep_info.append(f"If {score}: leads to {', '.join(deps)}")
            if dep_info:
                req_text += f"  Dependencies: {'; '.join(dep_info)}\n"
    return req_text


def load_rubric_from_path(rubric_path: str) -> MultiStepRubric:
    """Load a rubric from a directory path."""
    rubric_path = Path(rubric_path)

    if rubric_path.is_dir():
        # Load from directory (assumes 'rubric' as base name)
        return MultiStepRubric.load(rubric_path, "rubric")
    else:
        # Assume it's a file path pattern like path/to/rubric_requirements.yaml
        # Extract directory and base name
        if rubric_path.name.endswith("_requirements.yaml"):
            directory = rubric_path.parent
            base_name = rubric_path.name[: -len("_requirements.yaml")]
            return MultiStepRubric.load(directory, base_name)
        else:
            raise ValueError(
                f"Invalid rubric path: {rubric_path}. "
                "Expected directory or file ending with '_requirements.yaml'"
            )


async def main() -> None:
    """Main entry point for generating hidden descriptions from a rubric."""
    parser = argparse.ArgumentParser(
        description="Generate hidden descriptions for scenarios based on a rubric"
    )
    parser.add_argument(
        "rubric_path",
        help="Path to rubric directory or requirements file",
    )
    parser.add_argument(
        "output_file",
        help="Output JSON file to save hidden descriptions",
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

    args = parser.parse_args()

    try:
        # Load rubric
        print(f"Loading rubric from {args.rubric_path}...")
        rubric = load_rubric_from_path(args.rubric_path)
        print(f"Loaded rubric with {len(rubric.requirements)} requirements")

        # Generate hidden descriptions
        print(f"Generating {args.num_descriptions} hidden descriptions...")
        client = OpenAI()
        model_kwargs = {"temperature": args.temperature}

        descriptions = await generate_hidden_descriptions_async(
            requirements=rubric.requirements,
            num_descriptions=args.num_descriptions,
            model=args.model,
            client=client,
            model_kwargs=model_kwargs,
        )

        # Save to file
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(descriptions, f, indent=2)

        print(f"Saved {len(descriptions)} hidden descriptions to {output_path}")

        # Print summary
        for desc in descriptions:
            print(f"  - {desc['id']}: {desc['title']}")

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
