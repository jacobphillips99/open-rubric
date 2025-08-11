---
license: apache-2.0
language:
- en
task_categories:
- question-answering
tags:
- synthetic
- scenarios
- multistep-rubric
- open-rubric
pretty_name: "Open Rubric Synthetic Scenarios"
size_categories:
- 1K<n<10K
---

# Open Rubric Synthetic Scenarios

This dataset contains synthetically generated scenarios for multistep rubric evaluation.

## Dataset Description

This dataset was generated using the Open Rubric framework for creating synthetic evaluation scenarios. Each row contains a question-answer pair where:

- **question**: JSON containing the hidden description and prompt for the scenario
- **answer**: JSON containing the scenario details (name, description, answers, revealed_info)

## Dataset Structure

### Data Fields

- `question` (string): JSON string containing:
  - `_hidden_description`: The hidden context for scenario generation
  - `prompt`: The prompt presented to models being evaluated
- `answer` (string): JSON string containing:
  - `name`: Scenario name/title
  - `description`: Scenario description
  - `answers`: Expected answers or outcomes
  - `revealed_info`: Information revealed during the scenario

### Data Splits

The dataset contains 815 synthetic scenarios in a single split.

## Usage

```python
from datasets import load_dataset
import json

dataset = load_dataset("jacobphillips99/open-rubric-first-responder-scenarios")

# Access a single example
example = dataset["train"][0]
question_data = json.loads(example["question"])
answer_data = json.loads(example["answer"])

print(f"Prompt: {question_data['prompt']}")
print(f"Scenario: {answer_data['name']}")
```

## Citation

```bibtex
@misc{open-rubric-synthetic,
  title={Open Rubric Synthetic Scenarios},
  author={Open Rubric Contributors},
  year={2024},
  url={https://huggingface.co/datasets/jacobphillips99/open-rubric-first-responder-scenarios}
}
```

## Dataset Creation

This dataset was generated using the Open Rubric synthetic scenario generation pipeline. See the [Open Rubric repository](https://github.com/open-rubric/open-rubric) for more details.
