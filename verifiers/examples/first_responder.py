import asyncio
import json
import os
from datasets import Dataset, load_dataset
from openai import AsyncOpenAI, OpenAI
import verifiers as vf
from multistep_extras.example_rubrics import get_workflow
from verifiers.envs.multistep_env import MultiStepMultiTurnEnv
from verifiers.rewards.judge_reward import JUDGE_PROMPT, BinaryJudgeRewarder
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric
from verifiers.rubrics.multistep.reward_strategies import LevelWeightedRewardStrategy

"""
inference:
CUDA_VISIBLE_DEVICES=0 vf-vllm --model your-finetuned-model-name --enforce-eager

training:
CUDA_VISIBLE_DEVICES=1 accelerate launch --num-processes 1 --config-file configs/zero3.yaml verifiers/examples/first_responder.py
"""

hf_repo_name = "jacobphillips99"
project_name = "open-rubric"
group = "first-responder"

# generated synthetic scenarios from synthetic.py
dataset = load_dataset(f'{hf_repo_name}/{project_name}-{group}-scenarios', split='train')

def process_dataset_item(item):
    """Process a single dataset item into the format needed for training."""
    question_data = json.loads(item['question'])
    answer_data = json.loads(item['answer'])

    answer_with_revealed_info = json.dumps({
        **answer_data['answers'],
        "_revealed_info": answer_data.get('revealed_info', {})
    })

    return {
        'prompt': question_data['prompt'],
        'answer': answer_with_revealed_info
    }

# Process the dataset
processed_dataset = dataset.map(process_dataset_item)

# Split for training and evaluation using a ratio
train_ratio = 0.8
n = len(processed_dataset)
if n <= 1:
    num_train = 0
else:
    num_train = max(1, min(n - 1, int(n * train_ratio)))
num_eval = n - num_train
train_dataset = processed_dataset.select(range(num_train))
eval_dataset = processed_dataset.select(range(num_train, num_train + num_eval))

# load rubric from configs
rubric = MultiStepRubric.load("outputs/workflows", "first_responder")

# Model configuration
model_name = "willcb/Qwen3-0.6B"

# Create the multistep environment
vf_env = MultiStepMultiTurnEnv(
    multistep_rubric=rubric,
    max_turns=6,
    dataset=train_dataset,
    message_type="chat",
)

# Training configuration - optimized for multistep environment
args = vf.grpo_defaults(run_name='first_responder_multistep_emergency_response')
args.per_device_train_batch_size = 2 
args.num_generations = 2 
args.gradient_accumulation_steps = 16 
args.max_steps = 1000 
args.eval_strategy = 'steps'
args.eval_steps = 50 
args.report_to = 'wandb'
args.max_tokens = 1024 
args.learning_rate = 3e-6 
args.warmup_steps = 100

# Load model and tokenizer
model, tokenizer = vf.get_model_and_tokenizer(model_name)

# Create trainer
trainer = vf.GRPOTrainer(
    model=model,
    processing_class=tokenizer,
    env=vf_env,
    args=args,
)

if __name__ == "__main__":
    trainer.train()
