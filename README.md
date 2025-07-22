# Open Rubric: Advanced Multi-Step Rubric Evaluation Framework

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository is a specialized fork of [verifiers](https://github.com/willccbb/verifiers) that focuses on **multi-step rubric evaluation capabilities** for LLMs. Built on top of verifiers' robust RL framework with GRPO training, async inference, and OpenAI-compatible API support, Open Rubric adds the **MultiStepRubric** system for complex, dependency-based evaluation workflows that dynamically adapt based on judge-determined correctness.

## 🚀 Core Features

### **MultiStepRubric System** (Open Rubric Extension)
- **Dependency-based evaluation**: Requirements can depend on the outcomes of other requirements
- **Judge-driven progression**: Only correct judge evaluations trigger workflow continuation
- **Progressive information revelation**: Additional context is revealed as requirements are satisfied
- **Branching workflows**: Support for complex, multi-path evaluation scenarios

### **Robust RL Framework** (Inherited from Verifiers)
- **GRPO Training**: Group-Relative Policy Optimization with async inference
- **Multi-turn tool use**: Native support for agentic RL workflows
- **API Integration**: Direct OpenAI-compatible client support for evaluation and data collection
- **Async execution**: High-performance parallel rollouts and rubric evaluation

### **Comprehensive Environment Support**
- **Single-turn**: Evaluate final responses against complete workflows (`SingleTurnEnv`)
- **Multi-turn**: Interactive conversations that adapt based on real-time evaluation (`MultiTurnEnv`)
- **Tool environments**: Multi-turn tool use with Python functions (`ToolEnv`)
- **Code execution**: Interactive Python environments (`CodeMathEnv`)
- **Reasoning tasks**: Direct integration with reasoning-gym (`ReasoningGymEnv`)

### **Advanced Tooling**
- **Visual workflow builder**: Streamlit GUI for creating and editing rubrics
- **Visualization tools**: Interactive diagrams for understanding evaluation flows
- **Synthetic data generation**: API evaluation → dataset creation → training pipeline
- **SFT warmup support**: Supervised fine-tuning on filtered high-quality responses
- **Parser utilities**: XML, JSON, and custom format parsing (`XMLParser`, etc.)
- **Testing framework**: Extensive test suite with async support

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
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
uv sync --extra all && uv pip install flash-attn --no-build-isolation

# Or using pip
pip install -e ".[all]" && pip install flash-attn==2.7.4.post1 --no-build-isolation
```

### CPU-Only Development

For API-only usage without training capabilities:

```bash
# Clone first, then install core dependencies only
git clone https://github.com/jacobphillips99/open-rubric.git
cd open-rubric
uv pip install -e .
```

### Setup Requirements

- **Authentication**: Ensure your `wandb` and `huggingface-cli` logins are configured (or set `report_to=None` in training args)
- **API Keys**: Set `OPENAI_API_KEY` in your environment (can be dummy key for vLLM)
- **System Limits**: For high concurrency, increase open socket limits: `ulimit -n 4096`

### Troubleshooting

- **NCCL Issues**: If experiencing GPU communication problems, try setting `NCCL_P2P_DISABLE=1`
- **Memory Issues**: Reduce `per_device_train_batch_size` and increase `gradient_accumulation_steps`
- **Flash Attention**: On some systems, install without build isolation: `--no-build-isolation`

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

## 🚀 GRPO Training Setup

### Basic Training Workflow

For GRPO training with 4 GPUs (2 inference + 2 training):

```bash
# Launch inference server
CUDA_VISIBLE_DEVICES=0,1 vf-vllm --model 'Qwen/Qwen2.5-1.5B-Instruct' --tensor-parallel-size 2

# Launch training script
CUDA_VISIBLE_DEVICES=2,3 accelerate launch --num-processes 2 --config-file configs/zero3.yaml train.py
```

### Resource Requirements

- **Minimum**: 2 GPUs with sufficient memory for small-scale experimentation
- **Recommended**: 8xH100 nodes for large-scale training
- **Budget Option**: 2-GPU setups available for <$1/hr on cloud platforms

### GRPO Best Practices

**Performance & Stability Tips:**

- **Start Simple**: Always evaluate your model/API performance first
  - If <10% non-zero rewards → task too hard (simplify, add SFT warmup)
  - If >80% accuracy → task too easy (consider pre-filtering)

- **Increase Performance** (risk of collapse):
  - Set KL penalty `beta = 0` (removes reference model)
  - Increase learning rate
  - Increase update steps per batch (`num_iterations`)

- **Increase Stability** (slower training):
  - Increase group size (`num_generations`)
  - Increase batch size (`per_device_train_batch_size`, `gradient_accumulation_steps`)
  - Decrease gradient clipping (`max_grad_norm`)
  - Use larger models (14B+)
  - Use LoRA adapters

- **Free Performance Gains**:
  - Learning rate warm-up (10-20 steps)
  - Periodic reference model updates (`sync_ref_model`)
  - One-step off-policy training

## 🧠 Core Concepts

### **MultiStepRubric**
The core component of the system - evaluates requirements in dependency order, with judge-driven progression:

```python
class MultiStepRubric:
    def __init__(self, requirements, judge_options, reward_strategy=None):
        # Builds dependency graph and evaluation nodes
        
    async def evaluate(self, scenario):
        # Evaluates scenario following dependency paths
        
    def get_next_conversation_step(self, messages, state):
        # Drives multi-turn conversations with progressive revelation
```

### **Requirements**
Define evaluation criteria with conditional dependencies:

```python
BinaryRequirement(
    name="scene_safety",
    question="Is the scene safe to approach?",
    dependencies={
        1.0: ["patient_assessment", "vital_signs"],  # If safe, assess patient
        0.0: []  # If unsafe, stop workflow
    }
)
```

### **Scenarios**
Contain the complete evaluation context:

```python
Scenario(
    prompt="Initial situation description...",
    completion="Model's response to evaluate...",
    answers={"req_name": {"answer": 1.0, "reasoning": "..."}},
    revealed_info={"req_name": "Info revealed when requirement satisfied"}
)
```

### **Reward Strategies**
Flexible scoring approaches:

- **LevelWeightedRewardStrategy**: Earlier requirements worth more
- **CompletionRatioRewardStrategy**: Based on percentage completed  
- **ProgressiveRewardStrategy**: Exponential scaling
- **SumRewardStrategy**: Simple addition
- **MeanRewardStrategy**: Average of completed requirements

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

## 📚 API Reference

### Core Classes

- **`MultiStepRubric`**: Main evaluation engine
- **`BinaryRequirement`**: Yes/no evaluation requirements  
- **`ContinuousRequirement`**: Numeric score requirements
- **`Scenario`**: Complete evaluation context
- **`RewardStrategy`**: Pluggable scoring algorithms

### Builder Tools

- **`RubricBuilder`**: Programmatic rubric construction
- **`ScenarioBuilder`**: Scenario creation utilities
- **`ScenarioGenerator`**: LLM-powered scenario generation

### Visualization

- **`RubricVisualizer`**: Workflow structure visualization
- **`RequirementsVisualizer`**: Individual requirement display
- **`CompletedRubricVisualizer`**: Evaluation result visualization

## 🔄 Compatibility with Original Verifiers

This fork maintains full compatibility with the original verifiers API while providing additional multistep capabilities:

```python
# Original verifiers rubric
from verifiers.rubrics.rubric import Rubric

# Multistep-focused rubric (backward compatible)
from verifiers.rubrics.multistep import MultiStepRubric

# All original environments still work
from verifiers.envs.singleturn_env import SingleTurnEnvironment
```

### Levels of Exploration

**Level 0**: Inspect and run included examples:
- `verifiers/examples/reverse_text.py` (`SingleTurnEnv`)
- `verifiers/examples/math_python.py` (`ToolEnv`)

**Level 1**: Implement custom reasoning tasks with verifiable rewards:

```python
import verifiers as vf
parser = vf.XMLParser(['think', 'answer'])
rubric = vf.Rubric(
    your_custom_reward_func,
    parser.get_format_reward_func(),
    weights=[1.0, 0.2]
)
env = vf.SingleTurnEnv(
    dataset=...,  # HF Dataset with 'question' + 'answer' columns
    system_prompt=f"... Format: {parser.get_format_str()}",
    rubric=rubric
)
```

**Level 2**: Evaluate API models and collect synthetic data:

```python
from openai import OpenAI
client = OpenAI(base_url="https://api.deepseek.com", api_key=os.getenv('DEEPSEEK_API_KEY'))

# Evaluation
results = env.evaluate(client, model="deepseek-chat", num_samples=100)
print(results['rewards_avg'])

# Synthetic dataset generation
dataset = env.make_dataset(results)
dataset = dataset.sort("reward", reverse=True).select(range(50))
dataset.push_to_hub("your-username/high-quality-responses")
```

**Level 3**: Train models using GRPO:

```python
model, tokenizer = vf.get_model_and_tokenizer(model_name)
trainer = vf.GRPOTrainer(
    model=model,
    processing_class=tokenizer,
    env=env,
    args=vf.grpo_defaults(run_name="my-multistep-experiment")
)
trainer.train()
```

**Level 4+**: Implement custom multi-turn environments:

```python
# Multi-step rubric with tool use
env = vf.ToolEnv(
    dataset=...,
    system_prompt=...,
    tools=[python, search, ask, calculator],
    max_steps=5
)

# Or create fully custom environments
class CustomMultiTurnEnv(vf.MultiTurnEnv):
    def is_completed(self, messages, state, **kwargs):
        # Define completion logic
        
    def env_response(self, messages, state, **kwargs):
        # Define environment response logic
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** with tests
4. **Run the test suite**: `pytest`
5. **Submit a pull request**

### Development Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run linting
ruff check .
ruff format .
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📝 Citation

If you use Open Rubric in your research, please cite both this work and the original verifiers framework:

```bibtex
@software{openrubric2025,
  title={Open Rubric: Advanced Multi-Step Rubric Evaluation Framework},
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

## 🔄 Complete ML Workflow

Open Rubric supports the full machine learning pipeline:

1. **API Evaluation**: Test existing models in your environments
2. **Synthetic Data Collection**: Generate high-quality training data
3. **SFT Warmup**: Supervised fine-tuning on filtered responses
4. **GRPO Training**: Reinforcement learning with group-relative optimization
5. **Model Evaluation**: Test trained models against benchmarks

```bash
# Complete workflow example
python evaluate_apis.py          # Step 1: Evaluate baseline models
python collect_data.py           # Step 2: Generate synthetic training data
python sft_warmup.py            # Step 3: SFT on high-quality responses
python grpo_train.py            # Step 4: RL training with GRPO
python evaluate_trained.py      # Step 5: Final model evaluation
```

## 🙏 Acknowledgments

- **Based on verifiers**: [willccbb/verifiers](https://github.com/willccbb/verifiers) - provides the foundational RL evaluation framework and GRPO implementation
- **Core Technologies**: Built with OpenAI API, vLLM, Streamlit, PyTorch, Transformers, HuggingFace ecosystem
- **Community**: Thanks to the open-source ML community for tools, feedback, and contributions


**Interested in multi-step evaluation workflows?** Start with our [Quick Start](#quick-start) guide or explore the [examples](examples/) directory! 