"""
Synthetic scenario generation package.

This package provides tools for generating synthetic scenarios from rubrics:
- generate_hidden_descriptions: Generate comprehensive scenario descriptions from rubrics
- generate_scenarios: Convert hidden descriptions into complete scenarios
- synthetic: Main entrypoint that orchestrates the full pipeline
"""

from .generate_hidden_descriptions import (generate_hidden_descriptions_async,
                                           load_rubric_from_path)
from .generate_scenarios import (generate_scenario_async,
                                 generate_scenarios_parallel)

__all__ = [
    "generate_hidden_descriptions_async",
    "generate_scenarios_parallel",
    "generate_scenario_async",
    "load_rubric_from_path",
]
