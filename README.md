# Open Rubric: Advanced Multi-Step Rubric Evaluation Framework

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository is a specialized fork of [verifiers](https://github.com/willccbb/verifiers) that focuses on **multi-step rubric evaluation capabilities** for LLMs. OpenRubric adds the **MultiStepRubric** for complex, dependency-based evaluation workflows that dynamically adapt based on judge-determined correctness.

## **MultiStepRubric in OpenRubric**
- **Branching workflows**: Support for complex, multi-path evaluation scenarios (e.g. emergency response, debugging, etc.) as a directed acyclic graph (DAG)
- **Dependency-based evaluation**: Requirements can depend on the outcomes of other requirements
- **Judge-driven progression**: Only correct judge evaluations trigger workflow continuation
- **Progressive information revelation**: Additional context is revealed in the environment as requirements are satisfied
- **Compatibility**: The `MultiStepRubric` can be used with the original `SingleTurnEnv` or the new [`MultiTurnEnvironment`](https://github.com/jacobphillips99/open-rubric/blob/main/verifiers/envs/multiturn_env.py).

## **Advanced Tooling**
- **Visual workflow builder**: [Streamlit GUI](https://github.com/jacobphillips99/open-rubric/blob/main/multistep_extras/builders/rubric_gui.py) for creating and editing rubrics
- **Visualization tools**: [Interactive diagrams](https://github.com/jacobphillips99/open-rubric/blob/main/multistep_extras/visualization/visualizer.py) for understanding evaluation flows
- **Synthetic data generation**: Use LLMs to [generate scenarios and ground truth answers](https://github.com/jacobphillips99/open-rubric/blob/main/verifiers/rubrics/multistep/scenario_generator.py) for training.

## 📋 Table of Contents

- [Installation](#installation)
- [Core Concepts](#core-concepts)
- [Quick Start](#quick-start)
- [Examples](#examples)
- [Workflow Builder](#workflow-builder)
- [API Reference](#api-reference)
- [Contributing](#contributing)

## 🛠️ Installation

### From Source 


```bash
# Clone the repository
git clone https://github.com/jacobphillips99/open-rubric.git
cd open-rubric

# Install with all features using uv (recommended)
uv sync --extra all

# If using GPUs for training or inference, install flash-attn
uv pip install flash-attn --no-build-isolation
```


### Setup Requirements

- **Authentication**: Ensure your `wandb` and `huggingface-cli` logins are configured (or set `report_to=None` in training args)
- **API Keys**: Set `*_API_KEY` in your environment for OPENAI, ANTHROPIC, etc. (can be dummy key for vLLM)

## 🧠 Core Concepts

**Rubrics**
Rubrics hold groups of reward functions. In OpenRubric, the rubric is a directed acyclic graph (DAG) of requirements, where each requirement is a reward function. This enables complex, multi-step evaluation workflows as a judge determines if the model's response properly addresses each requirement according to a set of ground truth answers. Rubrics hold `Requirements` which determine the question for the judge to evaluate and the dependencies for the next requirement(s).

The `MultiStepRubric` conducts a topological sort of the requirements to determine the order in which to evaluate them. 

**Scenarios**
Scenarios are the input to the rubric to be evaluated. They contain the prompt, the policy model's response, and the ground truth answers for the rubric. Scenarios can be seeded by a `_hidden_description` field from which an LLM generates a prompt, completion, and ground truth answers.

**Judges**
Judges are the evaluators of the model's response. They are responsible for determining if the model's response properly addresses each requirement according to a set of ground truth answers. Judges assess the model's response against the requirement's question and the ground truth answers; their scoring determines which next steps in the rubric are followed.

**First Responder Example:**
- **Requirement**: "Does the response check if the scene is safe?"
- **Model Response**: "First, I'll ensure the area is secure before approaching..."
- **Ground Truth**: The response should consider if the area is safe and secure before attempting any other steps.
- **Judge Evaluation**: 1.0 (model properly addressed scene safety)
- **Next Step**: Follow the "safe scene" dependency path: `["patient_assessment", "vital_signs"]`



### **MultiStepRubric**
The [core component](https://github.com/jacobphillips99/open-rubric/blob/main/verifiers/rubrics/multistep/multistep_rubric.py) of the system - evaluates requirements in topological order, with judge-driven progression. The MultiStepRubric contains a list of `Requirements` and a list of `Judges` and turns these combinations into nodes in a graph.

# TODO example


### **Requirements**
Requirements are the building blocks of the rubric. They contain the question for the judge to evaluate and the dependencies for the next requirement(s). Requirements having scoring strategies which inform the judge as to how to assess the model's response. Scoring strategies can be discrete or continuous; common uses are binary (yes/no) or continuous (0-1).

### **Scenarios**
[`Scenario`](https://github.com/jacobphillips99/open-rubric/blob/main/verifiers/rubrics/multistep/scenario.py) objects contain the complete evaluation context:

# TODO example, revealed info

### **Reward Strategies**
OpenRubric provides[flexible scoring approaches](https://github.com/jacobphillips99/open-rubric/blob/main/verifiers/rubrics/multistep/reward_strategies.py) in order to attend to different evaluation objectives. For example, you can weight correct answers more heavily for earlier requirements, treat everything as the same topological level, or even just use a simple sum of the requirements:

- **LevelWeightedRewardStrategy**: Earlier requirements worth more
- **CompletionRatioRewardStrategy**: Based on percentage completed  
- **ProgressiveRewardStrategy**: Exponential scaling
- **SumRewardStrategy**: Simple addition
- **MeanRewardStrategy**: Average of completed requirements

## 🚀 Quick Start

### Basic Multi-Step Evaluation

```python
import asyncio
import verifiers as vf
from verifiers.rubrics.multistep import MultiStepRubric, BinaryRequirement, Scenario
from verifiers.rewards.judge_reward import BinaryJudgeRewarder, JUDGE_PROMPT

# Define a simple workflow with dependencies
requirements = [
    BinaryRequirement(
        name="check_prerequisites",
        question="Does the response check if prerequisites are met?",
        dependencies={
            1.0: ["make_decision"],  # If yes, proceed to decision
            0.0: []  # If no, stop workflow
        }
    ),
    BinaryRequirement(
        name="make_decision", 
        question="Does the response make a clear decision?",
        dependencies={
            1.0: ["take_action"],
            0.0: []
        }
    ),
    BinaryRequirement(
        name="take_action",
        question="Does the response specify what action to take?"
    )
]

# Create rubric with judge
judge = BinaryJudgeRewarder(judge_prompt=JUDGE_PROMPT)
rubric = MultiStepRubric(requirements, [judge])

# Evaluate a scenario
scenario = Scenario(
    prompt="Should we deploy the new feature?",
    completion="Let me check our testing status first. All tests pass, so I recommend deploying tonight.",
    answers={
        "check_prerequisites": {"answer": 1.0, "reasoning": "Explicitly checks test status"},
        "make_decision": {"answer": 1.0, "reasoning": "Clear deployment recommendation"},
        "take_action": {"answer": 1.0, "reasoning": "Specifies deployment timing"}
    }
)

# Run evaluation
result = await rubric.evaluate(scenario)
print(f"Evaluation complete. Reward: {result}")
```

### Standard Single-Turn Evaluation (Verifiers Compatible)

```python
import verifiers as vf

# Standard verifiers workflow  
parser = vf.XMLParser(['think', 'answer'])
rubric = vf.Rubric(
    your_reward_function,
    parser.get_format_reward_func(),
    weights=[1.0, 0.2]
)

env = vf.SingleTurnEnv(
    dataset=your_dataset,
    system_prompt=f"Respond in format: {parser.get_format_str()}",
    rubric=rubric
)

# Evaluate with API
from openai import OpenAI
client = OpenAI()
results = await env.evaluate(client, model="gpt-4", num_samples=100)
```

### Interactive Multi-Turn Conversation

```python
from verifiers.envs.multiturn_env import MultiTurnEnvironment

# Create environment with progressive information revelation
env = MultiTurnEnvironment(rubric=rubric, scenarios=[scenario])

# Start conversation
messages = [{"role": "user", "content": "What's the emergency situation?"}]
response, reward, done, info = await env.step(messages)

# Environment provides next information as requirements are satisfied
while not done:
    # Model responds
    messages.append({"role": "assistant", "content": model_response})
    
    # Environment evaluates and potentially reveals new information
    response, reward, done, info = await env.step(messages)
    if response:  # New information revealed
        messages.append({"role": "system", "content": response})
```


## 🎯 Examples

### Emergency Response Workflow

```python
from multistep_extras.example_rubrics import first_responder_reqs, scenarios

# Pre-built first responder evaluation workflow
rubric = MultiStepRubric(first_responder_reqs, [judge])
emergency_scenario = scenarios[0]  # Emergency medical scenario

result = await rubric.evaluate(emergency_scenario)
```

### Debugging Workflow

```python
from multistep_extras.example_rubrics import debugging_reqs, debugging_scenarios

# Technical troubleshooting evaluation
debug_rubric = MultiStepRubric(debugging_reqs, [judge])
bug_scenario = debugging_scenarios[0]

result = await debug_rubric.evaluate(bug_scenario)
```

## 🎨 Workflow Builder

Launch the interactive GUI for building rubrics:

```bash
streamlit run multistep_extras/builders/rubric_gui.py
```

The GUI provides:
- **Visual requirement editor**: Add/edit requirements with dependencies
- **Judge configuration**: Set up evaluation criteria
- **Reward strategy selection**: Choose scoring approaches
- **Export/import**: Save workflows as YAML files
- **Live preview**: Test workflows in real-time

## 📊 Visualization

```python
from multistep_extras.visualization import RubricVisualizer

# Visualize workflow structure
visualizer = RubricVisualizer(rubric)
visualizer.show_workflow_graph()

# Visualize evaluation results
from multistep_extras.visualization import CompletedRubricVisualizer
result_viz = CompletedRubricVisualizer(rubric, evaluation_results)
result_viz.show_evaluation_path()
```

## 🧪 Testing & Development

Run the comprehensive test suite:

```bash
# Run all tests
pytest

# Run multistep-specific tests  
pytest multistep_extras/tests/

# Run with coverage
pytest --cov=verifiers --cov=multistep_extras

# Run async tests
pytest -m asyncio
```

### Example Testing

```python
# Test custom workflows
from multistep_extras.demos import MultiStepTutorial

tutorial = MultiStepTutorial()
await tutorial.demonstrate_evaluation_modes()
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📝 Citation

If you use OpenRubric in your research, please cite both this work and the original verifiers framework:

```bibtex
@software{openrubric2025,
  title={OpenRubric: Multi-Step Rubric Evaluation Framework},
  author={Phillips, Jacob},
  year={2025},
  url={https://github.com/jacobphillips99/open-rubric}
}

@article{brown2025verifiers,
  title={Verifiers: Reinforcement Learning with LLMs in Verifiable Environments},
  author={Brown, William},
  year={2025}
}
```

## 🙏 Acknowledgments

- **Based on verifiers**: [willccbb/verifiers](https://github.com/willccbb/verifiers). OpenRubric is a fork of `verifiers` focused on expanding the Rubrics and Environments to support multi-step evaluation workflows. Thank you to Will Brown for the `verifiers` framework!
