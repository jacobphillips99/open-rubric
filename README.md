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

### 🚀 Your First Multi-Step Rubric

Let's build a **medical emergency response workflow** to see OpenRubric in action! This example demonstrates how complex decision trees adapt based on real-world conditions.

#### Step 1: Import the Framework

```python
from verifiers.rubrics.multistep import MultiStepRubric, BinaryRequirement, Scenario
from verifiers.rewards.judge_reward import BinaryJudgeRewarder, JUDGE_PROMPT
```

#### Step 2: Design Your Workflow

Create a **branching emergency protocol** where each decision point leads to different response paths:

```python
# Emergency Response Workflow
requirements = [
    # Initial Assessment
    BinaryRequirement(
        name="scene_safety",
        question="Does the response prioritize scene safety before approaching?",
        dependencies={
            1.0: ["patient_consciousness", "vital_signs"],  # Safe → parallel assessments
            0.0: []  # Unsafe → stop workflow
        }
    ),

    # Branching Based on Patient State
    BinaryRequirement(
        name="patient_consciousness",
        question="Does the response assess if the patient is conscious and responsive?",
        dependencies={
            1.0: ["communication", "pain_assessment"],  # Conscious → gather info
            0.0: ["airway_management", "emergency_protocols"]  # Unconscious → life support
        }
    ),

    BinaryRequirement(
        name="vital_signs",
        question="Does the response check vital signs for stability?",
        dependencies={
            1.0: ["transport_decision"],  # Stable → consider transport
            0.0: ["immediate_intervention"]  # Unstable → emergency action
        }
    ),

    # Conscious Patient Path
    BinaryRequirement(
        name="communication",
        question="Does the response attempt to communicate with the patient?"
    ),

    BinaryRequirement(
        name="pain_assessment",
        question="Does the response assess and address patient pain levels?"
    ),

    # Unconscious Patient Path
    BinaryRequirement(
        name="airway_management",
        question="Does the response ensure airway is clear and protected?"
    ),

    BinaryRequirement(
        name="emergency_protocols",
        question="Does the response activate appropriate emergency protocols?"
    ),

    # Terminal Actions
    BinaryRequirement(
        name="immediate_intervention",
        question="Does the response perform immediate life-saving interventions?"
    ),

    BinaryRequirement(
        name="transport_decision",
        question="Does the response make appropriate transport arrangements?"
    )
]
```

#### Step 3: Create Test Scenarios

**Scenario A: Conscious Trauma Patient**
```python
conscious_scenario = Scenario(
    prompt="""You arrive at a car accident. The driver is sitting upright, alert,
    but has a deep cut on their arm bleeding heavily. The scene is secure.""",

    completion="""First, I confirm the scene is safe - no traffic hazards or fuel leaks.
    The patient is conscious and talking, so I'll introduce myself and ask about their
    condition while applying direct pressure to control the bleeding. I'll assess their
    pain level and other injuries, then prepare for ambulance transport.""",

    answers={
        "scene_safety": {"answer": 1.0, "reasoning": "Confirms scene safety first"},
        "patient_consciousness": {"answer": 1.0, "reasoning": "Patient is alert and talking"},
        "communication": {"answer": 1.0, "reasoning": "Introduces self and gathers info"},
        "pain_assessment": {"answer": 1.0, "reasoning": "Assesses pain and bleeding"},
        "transport_decision": {"answer": 1.0, "reasoning": "Prepares for ambulance"}
    }
)
```

**Scenario B: Unconscious Emergency**
```python
unconscious_scenario = Scenario(
    prompt="""You find an unconscious person on the sidewalk. They're not responding
    to verbal stimuli and breathing appears shallow. No obvious hazards present.""",

    completion="""Scene appears safe with no immediate dangers. The patient is
    unconscious and not responding to my voice. I'll check their airway immediately
    and call for advanced life support while beginning CPR protocols.""",

    answers={
        "scene_safety": {"answer": 1.0, "reasoning": "Assesses scene for dangers"},
        "patient_consciousness": {"answer": 0.0, "reasoning": "Patient unconscious, no response"},
        "airway_management": {"answer": 1.0, "reasoning": "Checks airway immediately"},
        "emergency_protocols": {"answer": 1.0, "reasoning": "Calls ALS and begins CPR"}
    }
)
```

#### Step 4: Evaluate and See the Magic

```python
# Create the rubric with judge-based evaluation
rubric = MultiStepRubric(requirements, [BinaryJudgeRewarder(JUDGE_PROMPT)])

# Evaluate different scenarios
conscious_result = await rubric.evaluate(conscious_scenario)
unconscious_result = await rubric.evaluate(unconscious_scenario)

# Each scenario follows a different path through the workflow!
print(f"Conscious path reward: {conscious_result.total_reward}")
print(f"Unconscious path reward: {unconscious_result.total_reward}")
```

#### 🎯 What Just Happened?

- **Dynamic Branching**: Each scenario triggered different workflow paths based on patient consciousness
- **Progressive Evaluation**: Only relevant requirements were evaluated based on dependencies
- **Judge-Driven Scoring**: AI judges determined if each requirement was properly addressed
- **Realistic Training**: Models learn complex decision-making rather than simple pattern matching

### Next Steps

🔧 **Try the Interactive Builder**: `streamlit run multistep_extras/builders/rubric_gui.py`

🧠 **Advanced Scenarios**: Check out `multistep_extras/example_rubrics/` for debugging workflows, complex medical protocols, and more

🚂 **Model Training**: See our [training examples](examples/) for GRPO reinforcement learning with multi-step rubrics

### Synthetic Data Generation (with Hugging Face push)

Generate synthetic scenarios from a rubric and optionally push to the Hugging Face Hub. See full docs in `multistep_extras/synthetic/README.md`.

```bash
# Generate 20 first responder scenarios and save locally
python -m multistep_extras.synthetic.synthetic first_responder \
  --num-descriptions 20 \
  --hidden-temp 0.7 \
  --scenario-temp 0.1 \
  --output-dir ./outputs

# Push dataset to Hugging Face Hub (requires HF token)
export HF_TOKEN=YOUR_TOKEN
python -m multistep_extras.synthetic.synthetic /path/to/rubric \
  --num-descriptions 100 \
  --model gpt-4.1-turbo \
  --max-concurrent 15 \
  --output-dir ./my_scenarios \
  --hf-repo-id username/my_scenarios \
  --hf-private
```

This creates two splits: `hidden` (hidden descriptions) and `scenarios` (full scenarios). Local JSONL exports are saved under `outputs/hf/`.

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
