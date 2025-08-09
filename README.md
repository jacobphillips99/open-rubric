# OpenRubric: Multi‑Step Rubric Evaluation

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

OpenRubric adds multi‑step, dependency‑aware evaluation on top of [verifiers](https://github.com/willccbb/verifiers). Define rubrics as DAGs of requirements, let an AI judge score each step, and branch only when the judge says the model is correct.

## Features

- **Branching workflows**: Requirements connected as a DAG; paths advance on correct judgments
- **Judge‑driven progression**: External judge determines correctness and reveals next steps
- **Flexible scoring**: Level‑weighted, progressive, mean, sum, and more
- **GUI builder**: Visual editor and YAML import/export
- **Synthetic data**: Generate hidden descriptions and full scenarios; optional HF Hub push

## Installation

```bash
git clone https://github.com/jacobphillips99/open-rubric.git
cd open-rubric
uv sync --extra all

# Optional: GPU‑optimized attention
uv pip install flash-attn --no-build-isolation
```

Configure credentials as needed (`OPENAI`, `ANTHROPIC`, `wandb`, `huggingface-cli`). For remote setup, see `install.sh`.

## Core Concepts

- **Rubric**: A DAG of named requirements
- **Requirement**: A question to evaluate (binary or discrete/continuous), optionally with conditional dependencies
- **Scenario**: Prompt + model completion + ground‑truth answers
- **Judge**: Scores a requirement given the prompt/completion/answer
- **Reward strategy**: Aggregates per‑requirement results into a single score

## Quick Start

Minimal branching example with two paths and an async evaluation call you can run directly.

```python
import asyncio
from verifiers.rubrics.multistep import MultiStepRubric, BinaryRequirement, Scenario
from verifiers.rewards.judge_reward import BinaryJudgeRewarder, JUDGE_PROMPT

# Define a tiny workflow
requirements = [
    BinaryRequirement(
        name="scene_safety",
        question="Does the response prioritize scene safety before approaching?",
        dependencies={
            1.0: ["patient_consciousness"],
            0.0: [],
        },
    ),
    BinaryRequirement(
        name="patient_consciousness",
        question="Does the response assess if the patient is conscious?",
        dependencies={
            1.0: ["communication"],
            0.0: ["airway_management"],
        },
    ),
    BinaryRequirement(name="communication", question="Do they communicate with the patient?"),
    BinaryRequirement(name="airway_management", question="Do they secure the airway?"),
]

rubric = MultiStepRubric(requirements, [BinaryJudgeRewarder(JUDGE_PROMPT)])

scenario = Scenario(
    prompt="You arrive at a minor crash; the scene is safe.",
    completion="I confirm safety, speak to the patient, and proceed.",
    answers={
        "scene_safety": {"answer": 1.0},
        "patient_consciousness": {"answer": 1.0},
        "communication": {"answer": 1.0},
    },
)

async def main() -> None:
    results = await rubric.evaluate(scenario)
    print(results)  # dict keyed by level: {"0": {...}, "1": {...}, ...}

asyncio.run(main())
```

## Workflow Builder (GUI)

```bash
streamlit run multistep_extras/builders/rubric_gui.py
```

The builder supports visual editing, judge configuration, reward strategy selection, and YAML import/export.

![Rubric Builder](rubric_gui.png)
![Multistep Rubric](rubric_viz.png)

## Synthetic Data Generation

Generate scenarios from any rubric. See `multistep_extras/synthetic/README.md` for details.

```bash
# Local generation
python -m multistep_extras.synthetic.synthetic first_responder \
  --num-descriptions 20 \
  --hidden-temp 0.7 \
  --scenario-temp 0.1 \
  --output-dir ./outputs

# Optional: push to Hugging Face Hub
export HF_TOKEN=YOUR_TOKEN
python -m multistep_extras.synthetic.synthetic /path/to/rubric \
  --num-descriptions 100 \
  --model gpt-4.1 \
  --max-concurrent 15 \
  --output-dir ./my_scenarios \
  --hf-repo-id username/my_scenarios \
  --hf-private
```

Outputs include two splits: `hidden` (hidden descriptions) and `scenarios` (full scenarios). Local JSONL files are written under `outputs/hf/`.

## Training

GRPO training examples with multi‑step rubrics live under `examples/` (e.g., `train_gsm8k.py`, `train_math_group.py`, `train_wordle.py`).

## License

MIT — see `LICENSE`.

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

Built on top of [verifiers](https://github.com/willccbb/verifiers) by Will Brown.
