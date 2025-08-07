# Synthetic Scenario Generation

This package provides tools for generating synthetic scenarios from rubrics using large language models. It enables automatic creation of comprehensive evaluation datasets for multistep rubrics.

## Overview

The synthetic generation pipeline creates datasets given a rubric.
- `generate_hidden_descriptions.py` generates hidden descriptionsfor scenes from the rubric
- `generate_scenarios.py` generates scenarios from the hidden descriptions
- `synthetic.py` is the main entrypoint orchestrating the full pipeline

## Files

- `generate_hidden_descriptions.py` - Generate comprehensive scenario descriptions from rubrics
- `generate_scenarios.py` - Convert hidden descriptions into complete scenarios
- `synthetic.py` - Main entrypoint orchestrating the full pipeline
- `__init__.py` - Package exports for programmatic use

## Quick Start

### Full Pipeline (Recommended)

Generate complete synthetic scenarios in one command:

```bash
# Generate 10 scenarios from first responder rubric (built-in workflow)
python -m multistep_extras.synthetic.synthetic first_responder --num-descriptions 10 \
    --hidden-temp 0.7 --scenario-temp 0.1

# With custom settings and Hugging Face upload
python -m multistep_extras.synthetic.synthetic /path/to/rubric \
    --num-descriptions 100 \
    --model gpt-4.1-turbo \
    --hidden-temp 0.7 \
    --scenario-temp 0.1 \
    --max-concurrent 15 \
    --output-dir ./my_scenarios \
    --hf-repo-id username/my_scenarios \
    --hf-private
```

### Step-by-Step Process

For more control over the generation process:

```bash
# Step 1: Generate hidden descriptions
python -m multistep_extras.synthetic.generate_hidden_descriptions \
    first_responder \
    hidden_descriptions.json \
    --num-descriptions 50

# Step 2: Generate scenarios from descriptions
python -m multistep_extras.synthetic.generate_scenarios \
    /path/to/rubric \
    hidden_descriptions.json \
    scenarios.yaml \
    --max-concurrent 10
```

### Pushing to Hugging Face Hub

You can push the generated dataset (two splits: `hidden` and `scenarios`) directly to the Hub using the full pipeline. Set an auth token via `HF_TOKEN` or pass `--hf-token`.

```bash
# Push to a private repo
export HF_TOKEN=YOUR_TOKEN
python -m multistep_extras.synthetic.synthetic /path/to/rubric \
  --num-descriptions 100 \
  --hidden-temp 0.7 \
  --scenario-temp 0.1 \
  --max-concurrent 15 \
  --output-dir ./my_scenarios \
  --hf-repo-id username/my_scenarios \
  --hf-private

# Skip pushing but still export Hugging Face-ready JSONL files locally
python -m multistep_extras.synthetic.synthetic first_responder \
  --num-descriptions 20 \
  --no-push \
  --output-dir ./outputs
```

## Using Built-in Example Rubrics

You can use the pre-built example rubrics:

```bash
# Generate scenarios from first responder workflow
python -m multistep_extras.synthetic.synthetic first_responder --num-descriptions 20

# Generate scenarios from debugging workflow  
python -m multistep_extras.synthetic.synthetic debugging --num-descriptions 15
```

## Input Formats

### Rubric Loading

The scripts support multiple rubric input formats:

1. **Directory with rubric files**:
   ```
   my_rubric/
   ├── rubric_requirements.yaml
   └── rubric_config.yaml
   ```
   Usage: `python script.py my_rubric/`

2. **Direct requirements file**:
   ```
   my_rubric_requirements.yaml
   ```
   Usage: `python script.py my_rubric_requirements.yaml`

3. **Built-in workflow names**:
   - `first_responder` - Emergency medical response scenarios
   - `debugging` - Software debugging investigation scenarios

### Hidden Descriptions Format

Hidden descriptions are stored as JSON with this structure:

```json
{
  "descriptions": [
    {
      "id": 1,
      "title": "Brief descriptive title",
      "hidden_description": "Comprehensive detailed description with all ground truth information..."
    }
  ]
}
```

## Output Formats

### Scenarios (YAML)

Generated scenarios are saved in YAML format using the built-in `Scenario.save_multiple()` method:

```yaml
scenarios:
  - name: synthetic_scenario_0
    description: Generated scenario description
    prompt: "Initial situation description..."
    answers:
      scene_safety:
        answer: 1.0
        reasoning: "Scene is safe because..."
    revealed_info:
      scene_safety: "Additional information revealed when correct"
    _hidden_description: "Complete ground truth description..."
```

### Hidden Descriptions (JSON)

Intermediate hidden descriptions are saved as JSON for reuse and inspection:

```json
[
  {
    "id": 0,
    "title": "Emergency Response Scenario",
    "hidden_description": "A 34-year-old electrician was working on power lines..."
  }
]
```

## Configuration Options

### Model Settings

- `--model`: LLM model to use (default: `gpt-4.1-nano`)
- `--hidden-temp`: Temperature for hidden descriptions (default: `0.7` for diversity)
- `--scenario-temp`: Temperature for scenarios (default: `0.1` for consistency)

### Concurrency Settings

- `--max-concurrent`: Maximum parallel requests for scenario generation (default: `5`)
- Batch processing is automatic for large datasets

### Output Settings

- `--output-dir`: Directory to save all outputs (default: current directory)
- `--no-intermediates`: Skip saving intermediate hidden descriptions (synthetic.py only)

### Hugging Face Upload

- `--hf-repo-id`: Target Hub repo id (`username/dataset_name`) to push dataset
- `--hf-private`: Create the dataset repo as private
- `--hf-branch`: Optional target branch
- `--hf-token`: Token to authenticate (falls back to `HF_TOKEN` or `HUGGINGFACE_HUB_TOKEN`)
- `--no-push`: Skip pushing even if `--hf-repo-id` is provided

## Programmatic Usage

You can also use the components programmatically:

```python
from multistep_extras.synthetic import (
    generate_hidden_descriptions_async,
    generate_scenarios_parallel,
    load_rubric_from_path
)
from openai import OpenAI

# Load rubric
rubric = load_rubric_from_path("path/to/rubric")

# Generate hidden descriptions
client = OpenAI()
descriptions = await generate_hidden_descriptions_async(
    requirements=rubric.requirements,
    num_descriptions=10,
    client=client
)

# Generate scenarios
scenarios = await generate_scenarios_parallel(
    hidden_descriptions=descriptions,
    requirements=rubric.requirements,
    client=client,
    max_concurrent=5
)
```

## Large-Scale Generation

For generating large datasets (100+ scenarios), use these optimizations:

### Batch Processing

The pipeline automatically handles batching for memory efficiency. For very large runs:

```bash
# Generate 1000 scenarios with high concurrency
python -m multistep_extras.synthetic.synthetic first_responder \
    --num-descriptions 1000 \
    --max-concurrent 20 \
    --output-dir ./large_dataset
```

### Cost Optimization

- Use `gpt-4.1-nano` for cost-effective generation
- Lower `--scenario-temp` (0.1) for more consistent scenario generation
- Increase `--max-concurrent` to reduce total time
- Monitor intermediate files to resume if interrupted

## Error Handling

The scripts include robust error handling:

- **Individual scenario failures**: Continue processing other scenarios
- **Batch failures**: Save intermediate results and provide clear error messages
- **Rate limiting**: Automatic handling with semaphore-based concurrency control
- **Resume capability**: Intermediate files allow manual resume of large jobs

## Output Structure

When using the full pipeline, outputs are organized as:

```
output_directory/
├── hidden_descriptions.json    # All generated descriptions
├── synthetic_scenarios.yaml    # All generated scenarios
└── hf/                         # Hugging Face-ready exports
    ├── hidden.jsonl            # Hidden descriptions split
    └── scenarios.jsonl         # Scenarios split
```

## Example Workflows

### Emergency Response Dataset

```bash
# Generate comprehensive first responder dataset
python -m multistep_extras.synthetic.synthetic first_responder \
    --num-descriptions 200 \
    --model gpt-4.1-turbo \
    --output-dir ./emergency_response_dataset
```

### Software Debugging Dataset

```bash
# Generate debugging investigation scenarios
python -m multistep_extras.synthetic.synthetic debugging \
    --num-descriptions 100 \
    --temperature 0.2 \
    --output-dir ./debugging_scenarios
```

### Custom Rubric Dataset

```bash
# Generate from your own rubric
python -m multistep_extras.synthetic.synthetic ./my_custom_rubric/ \
    --num-descriptions 50 \
    --output-dir ./custom_scenarios
```

## Dependencies

Required packages:
- `openai` - LLM API access
- `pyyaml` - YAML file handling
- `asyncio` - Async processing
- Core verifiers package components

## Tips and Best Practices

1. **Start Small**: Test with 5-10 scenarios before large runs
2. **Monitor Costs**: Track API usage for large datasets
3. **Save Intermediates**: Always keep intermediate files for large runs
4. **Use Appropriate Concurrency**: Balance speed vs. rate limits (5-20 concurrent)
5. **Review Outputs**: Manually inspect a sample of generated scenarios
6. **Version Control**: Save generation parameters for reproducibility

## Troubleshooting

### Common Issues

1. **Rate Limiting**: Reduce `--max-concurrent` if hitting API limits
2. **Memory Issues**: Process in smaller batches for very large datasets
3. **Invalid JSON**: Check model output format, try lower temperature
4. **Missing Requirements**: Ensure rubric has proper dependency structure

### Getting Help

- Check output logs for detailed error messages
- Verify rubric format using existing examples
- Test with built-in workflows first
- Review intermediate files to understand failures

## Integration with Other Tools

The generated scenarios can be used with:

- **Multistep Rubric Evaluation**: Direct compatibility with `MultiStepRubric.evaluate()`
- **Training Pipelines**: Convert to HuggingFace datasets for model training
- **Visualization Tools**: Use with `multistep_extras.visualization` for analysis
- **GUI Builder**: Import into `multistep_extras.builders.rubric_gui` for editing
