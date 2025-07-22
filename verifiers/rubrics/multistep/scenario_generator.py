"""
LLM-based scenario generation from hidden descriptions and rubrics.

This module provides functionality to generate complete scenarios (prompt, answers,
revealed_info, etc.) from a comprehensive hidden description and a rubric using
language model calls.
"""

import json
import traceback
from typing import Optional

from openai import OpenAI

from verifiers.parsers.xml_parser import XMLParser
from verifiers.rubrics.multistep.requirement import Requirement
from verifiers.rubrics.multistep.scenario import Scenario

SCENARIO_GENERATION_PROMPT = """
You are an expert scenario designer for evaluation rubrics. Your task is to generate a complete scenario from a comprehensive hidden description.

HIDDEN DESCRIPTION (complete ground truth):
{hidden_description}

RUBRIC REQUIREMENTS:
{requirements_text}

Based on the hidden description, generate:

1. INITIAL PROMPT: A brief initial situation description that presents limited information to start the evaluation. This should be what the responder initially sees/knows.
2. GROUND TRUTH ANSWERS: For each requirement, determine the correct answer (1.0 or 0.0) based on what the hidden description reveals, along with reasoning.
3. REVEALED INFO: For requirements that should reveal additional information when satisfied, provide progressive information snippets that gradually unveil details from the hidden description.

Format your response as valid JSON:
{{
    "prompt": "Initial situation description with limited information...",
    "answers": {{
        "requirement_name": {{
            "answer": 1.0,
            "reasoning": "Why this answer is correct based on hidden description"
        }}
    }},
    "revealed_info": {{
        "requirement_name": "Information to reveal when this requirement is satisfied"
    }}
}}

Important guidelines:
- The initial prompt should provide enough context to start but withhold key details
- Ground truth answers must be logically consistent with the hidden description
- Revealed info should progressively unveil details from the hidden description
- Keep revealed info snippets concise but informative
- Use exact requirement names from the provided list

Begin the response by first thinking about the response. Start with <think> and end with </think> once you have thought about your response.
Begin the actual valid JSON response inside <answer> and </answer>.
"""


def generate_scenario_from_hidden_description(
    hidden_description: str,
    requirements: list[Requirement],
    name: Optional[str] = None,
    description: Optional[str] = None,
    model: str = "gpt-4.1-nano",
    client: OpenAI = OpenAI(),
    model_kwargs: Optional[dict] = None,
) -> Scenario:
    """
    Generate a complete scenario from a hidden description and rubric requirements.

    This function takes a comprehensive hidden description containing all the ground truth
    details and uses an LLM to generate:
    - An appropriate initial prompt (with limited information)
    - Ground truth answers for each requirement
    - Revealed information snippets for progressive disclosure

    Args:
        hidden_description: Complete ground truth description of the scenario
        requirements: List of requirements from the rubric to evaluate against
        name: Optional name for the generated scenario
        description: Optional description of what this scenario tests
        llm_call_func: Optional custom LLM function. If None, uses a default implementation
        temperature: Temperature setting for LLM generation (default: 0.1 for consistency)

    Returns:
        Complete Scenario object with generated components

    Example:
        hidden_description = '''
        A 34-year-old electrician was working on power lines when electrocuted and fell
        12 feet onto concrete. Multiple active hazards present: live electrical wires
        down and sparking in 15-foot radius. Worker unconscious with visible burns on
        hands/arms, shallow irregular breathing, no pulse detected at wrist. Scene is
        on a busy highway with ongoing traffic. Additional crew needed for electrical
        safety before approach.
        '''

        scenario = generate_scenario_from_hidden_description(
            hidden_description, first_responder_requirements
        )
    """
    if model_kwargs is None:
        model_kwargs = {}

    # Build the generation prompt
    requirements_text = _format_requirements_for_prompt(requirements)
    prompt = SCENARIO_GENERATION_PROMPT.format(
        hidden_description=hidden_description,
        requirements_text=requirements_text,
    )
    parser = XMLParser(fields=["think", "answer"])
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        **model_kwargs,
    )
    parsed = parser.parse(response.choices[0].message.content)
    try:
        generated_data = json.loads(parsed.answer)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM response was not valid JSON: {e}; {traceback.format_exc()}"
        ) from e

    # Validate the generated data has required fields
    if "prompt" not in generated_data:
        raise ValueError("Generated data missing 'prompt' field")
    if "answers" not in generated_data:
        raise ValueError("Generated data missing 'answers' field")

    # Create and return the scenario
    return Scenario(
        name=name,
        description=description,
        prompt=generated_data["prompt"],
        answers=generated_data["answers"],
        revealed_info=generated_data.get("revealed_info", {}),
        _hidden_description=hidden_description,
    )


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


if __name__ == "__main__":
    from multistep_extras.example_rubrics import get_workflow

    reqs, scenarios = get_workflow("first_responder")
    hidden_description = scenarios[0]._hidden_description

    new_scenario = generate_scenario_from_hidden_description(
        hidden_description=hidden_description,
        requirements=reqs,
        name="test",
        description="test",
        model="gpt-4.1-nano",
        client=OpenAI(),
        model_kwargs={},
    )
