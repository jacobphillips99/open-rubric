import json
from datasets import Dataset, load_dataset
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

# Load the first responder scenarios dataset from HuggingFace
dataset = load_dataset('jacobphillips99/open-rubric-first-responder-scenarios', split='train')

def process_dataset_item(item):
    """Process a single dataset item into the format needed for training."""
    # Parse the JSON strings
    question_data = json.loads(item['question'])
    answer_data = json.loads(item['answer'])
    
    # Add revealed info for multistep environment
    answer_with_revealed_info = {
        **answer_data['answers'],
        "_revealed_info": answer_data.get('revealed_info', {})
    }
    
    return {
        # Use 'question' so the chat formatter injects the system prompt
        'question': question_data['prompt'],
        'answer': answer_with_revealed_info  # The ground truth answers dict with revealed info
    }

# Process the dataset
processed_dataset = dataset.map(process_dataset_item)

# Split for training and evaluation  
num_train = min(len(processed_dataset) - 1, 8)  # Leave at least 1 for eval
num_eval = max(1, len(processed_dataset) - num_train)
train_dataset = processed_dataset.select(range(num_train))
eval_dataset = processed_dataset.select(range(num_train, num_train + num_eval))

# System prompt for first responder training
system_prompt = """You are a highly trained first responder (EMT/Paramedic) responding to emergency medical situations. Your primary responsibilities are to assess the scene, evaluate the patient, and provide appropriate emergency medical care.

For each emergency scenario, provide a comprehensive response that addresses all aspects of emergency medical assessment and intervention. Think through your response step by step, considering:

1. Scene safety and environmental hazards
2. Initial patient assessment (consciousness, responsiveness)
3. Primary survey (Airway, Breathing, Circulation)
4. Vital signs and stability assessment
5. Trauma evaluation and injury assessment
6. Patient communication and symptom gathering
7. Pain assessment and management
8. Medical history collection when possible
9. Appropriate interventions and protocols
10. Stabilization and transport preparation

Respond in a clear, professional manner that demonstrates proper emergency medical procedures and decision-making. Consider the urgency of the situation and prioritize life-threatening conditions first.

Your response should be thorough but practical, reflecting real-world emergency response protocols and best practices."""

# Get first responder workflow from example rubrics
workflow_name = "first_responder"
requirements, scenarios = get_workflow(workflow_name, advanced=True)

# Create multistep rubric for first responder evaluation
judge_rewarders = [BinaryJudgeRewarder(judge_prompt=JUDGE_PROMPT)]

rubric = MultiStepRubric(
    requirements,
    judge_rewarders,
    reward_strategy=LevelWeightedRewardStrategy(),
)

# Model configuration
model_name = 'microsoft/Phi-3.5-mini-instruct'  # Good base model for instruction following

# Create the multistep environment
vf_env = MultiStepMultiTurnEnv(
    multistep_rubric=rubric,
    max_turns=6,  # Allow up to 6 turns for complex emergency response
    dataset=train_dataset,
    eval_dataset=eval_dataset,
    message_type="chat",
    system_prompt=system_prompt,
)

# Training configuration - optimized for multistep environment
args = vf.grpo_defaults(run_name='first_responder_multistep_emergency_response')
args.per_device_train_batch_size = 2  # Smaller batch size for multistep complexity
args.num_generations = 2  # Fewer generations due to multistep overhead
args.gradient_accumulation_steps = 32  # Increase to maintain effective batch size
args.max_steps = 1000  # More steps for complex multistep reasoning
args.eval_strategy = 'steps'
args.eval_steps = 50  # Less frequent evaluation due to complexity
args.report_to = 'wandb'
args.max_tokens = 1024  # Reasonable length for each turn
args.learning_rate = 3e-6  # Lower learning rate for stability in multistep
args.warmup_steps = 100
args.score_rollouts = True  # Enable scoring for multistep environment

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
