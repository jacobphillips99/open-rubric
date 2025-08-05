# Open Rubric: Multi-Step Rubric Evaluation Framework

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A framework for complex, dependency-based reasoning model training and evaluation. OpenRubric extends [verifiers](https://github.com/willccbb/verifiers) with **multi-step rubrics** that dynamically adapt based on judge-determined correctness.

## Key Features

**Branching Workflows**: Complex, multi-path evaluation scenarios as directed acyclic graphs (DAG)

**Dependency-Based Evaluation**: Requirements depend on outcomes of other requirements

**Judge-Driven Progression**: Only correct evaluations trigger workflow continuation

**Progressive Information Revelation**: Additional context revealed as requirements are satisfied

**Advanced Tooling**: Visual workflow builder, interactive diagrams, and synthetic data generation

**Training with Prime Intellect**: Instructions and artifacts from model training on [Prime Intellect](https://prime-intellect.com/). See [Training](#training) for more details.

## Table of Contents

- [Installation](#installation)
- [Core Concepts](#core-concepts)
- [Quick Start](#quick-start)
- [Workflow Builder](#workflow-builder)
- [Training](#training)
- [License](#license)

## Installation
<details>
<summary>Click to expand</summary>

```bash
# Clone and install
git clone https://github.com/jacobphillips99/open-rubric.git
cd open-rubric
uv sync --extra all

# For GPU support
uv pip install flash-attn --no-build-isolation
```

**Setup**: Configure `wandb` and `huggingface-cli` logins, set API keys for `OPENAI`, `ANTHROPIC`, etc.

For remote node setup, see [install.sh](https://github.com/jacobphillips99/open-rubric/blob/main/install.sh)

</details>

## Core Concepts

**Rubrics**: Directed acyclic graphs of requirements, where each requirement is evaluated by a judge against ground truth answers.

**Requirements**: Building blocks containing evaluation questions and dependencies for next steps. Support various scoring strategies like binary (yes/no) or continuous (0-1).

**Scenarios**: Input containing the prompt, model response, and ground truth answers for evaluation.

**Judges**: Evaluators that determine if responses properly address requirements. Their scoring determines workflow progression.

**Reward Strategies**: Flexible scoring approaches including level-weighted, completion ratio, progressive, sum, and mean strategies.

## Quick Start

```python
from verifiers.rubrics.multistep import MultiStepRubric, BinaryRequirement, Scenario
from verifiers.rewards.judge_reward import BinaryJudgeRewarder, JUDGE_PROMPT

# Define workflow
requirements = [
    BinaryRequirement(
        name="check_prerequisites",
        question="Does the response check if prerequisites are met?",
        dependencies={1.0: ["make_decision"], 0.0: []}
    ),
    BinaryRequirement(
        name="make_decision", 
        question="Does the response make a clear decision?",
        dependencies={1.0: ["take_action"], 0.0: []}
    ),
    BinaryRequirement(
        name="take_action",
        question="Does the response specify what action to take?"
    )
]

# Create and evaluate
rubric = MultiStepRubric(requirements, [BinaryJudgeRewarder(JUDGE_PROMPT)])
scenario = Scenario(
    prompt="Should we deploy the new feature?",
    completion="Let me check our testing status first. All tests pass, so I recommend deploying tonight.",
    answers={
        "check_prerequisites": {"answer": 1.0, "reasoning": "Explicitly checks test status"},
        "make_decision": {"answer": 1.0, "reasoning": "Clear deployment recommendation"},
        "take_action": {"answer": 1.0, "reasoning": "Specifies deployment timing"}
    }
)

result = await rubric.evaluate(scenario)
```

## Workflow Builder

Launch the interactive GUI:

```bash
streamlit run multistep_extras/builders/rubric_gui.py
```

Features include visual requirement editing, judge configuration, reward strategy selection, and YAML export/import.


## Training
# TODO

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

```bibtex
@software{openrubric2025,
  title={OpenRubric: Multi-Step Rubric Evaluation Framework},
  author={Phillips, Jacob},
  year={2025},
  url={https://github.com/jacobphillips99/open-rubric}
}
```

## Acknowledgments

Based on [verifiers](https://github.com/willccbb/verifiers) by Will Brown. OpenRubric extends the framework to support multi-step evaluation workflows.
