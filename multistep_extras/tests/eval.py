import argparse
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from datasets import Dataset, load_dataset
from openai import OpenAI

from verifiers.envs.multistep_env import MultiStepMultiTurnEnv
from verifiers.rubrics.multistep.multistep_rubric import MultiStepRubric


def _process_dataset_item(item: dict[str, Any]) -> dict[str, Any]:
    """Process one HF row into env-ready format.

    Expects fields 'question' and 'answer' as JSON strings with:
      question: {"prompt": str | list[{role, content}]}
      answer:   {"answers": dict, "revealed_info": dict}
    """
    question_data = json.loads(item["question"]) if isinstance(item["question"], str) else item["question"]
    answer_data = json.loads(item["answer"]) if isinstance(item["answer"], str) else item["answer"]

    raw_prompt = question_data["prompt"]
    if isinstance(raw_prompt, list):
        prompt_messages = raw_prompt
    else:
        prompt_messages = [{"role": "user", "content": raw_prompt}]

    answer_with_revealed_info = json.dumps({
        **answer_data["answers"],
        "_revealed_info": answer_data.get("revealed_info", {}),
    })

    return {"prompt": prompt_messages, "answer": answer_with_revealed_info}


def load_eval_dataset(hf_repo: str) -> Dataset:
    ds = load_dataset(hf_repo, split="train")
    # Process the dataset
    processed_dataset = ds.map(_process_dataset_item)
    # Split for training and evaluation using a ratio
    train_ratio = 0.8
    n = len(processed_dataset)
    if n <= 1:
        num_train = 0
    else:
        num_train = max(1, min(n - 1, int(n * train_ratio)))
    num_eval = n - num_train
    eval_dataset = processed_dataset.select(range(num_train, num_train + num_eval))
    return eval_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate test split and save per-episode rewards")
    parser.add_argument("--hf_repo", type=str, default="jacobphillips99/open-rubric-first-responder-scenarios")
    parser.add_argument("--workflow_dir", type=str, default="example_rubrics/workflows")
    parser.add_argument("--workflow_name", type=str, default="first_responder")
    parser.add_argument("--model", type=str, default="gpt-4.1")
    parser.add_argument("--base_url", type=str, default=os.getenv("OPENAI_BASE_URL", ""))
    parser.add_argument("--api_key", type=str, default=os.getenv("OPENAI_API_KEY", ""))
    parser.add_argument("--max_concurrent", type=int, default=64)
    parser.add_argument("--num_examples", type=int, default=-1)
    parser.add_argument("--rollouts_per_example", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max_tokens", type=int, default=1024)
    parser.add_argument("--out", type=Path, default=Path("outputs/first_responder_test_rewards.csv"))
    args = parser.parse_args()

    eval_dataset = load_eval_dataset(args.hf_repo)
    # fixme
    eval_dataset = eval_dataset.select(np.arange(10))

    # Load rubric
    rubric = MultiStepRubric.load(args.workflow_dir, args.workflow_name)

    # Build environment with eval dataset
    env = MultiStepMultiTurnEnv(
        multistep_rubric=rubric,
        max_turns=6,
        eval_dataset=eval_dataset,
        message_type="chat",
    )

    # OpenAI/vLLM-compatible client
    if args.base_url:
        client = OpenAI(api_key=args.api_key or "EMPTY", base_url=args.base_url)
    else:
        client = OpenAI(api_key=args.api_key or os.getenv("OPENAI_API_KEY"))

    # Run evaluation in parallel
    results = env.evaluate(
        client=client,
        model=args.model,
        sampling_args={"temperature": args.temperature, "max_tokens": args.max_tokens},
        num_examples=args.num_examples,
        rollouts_per_example=args.rollouts_per_example,
        score_rollouts=True,
        max_concurrent=args.max_concurrent,
    )
    breakpoint()

    # Save per-episode rewards
    rewards = results.reward
    indices = list(range(len(rewards)))
    df = pd.DataFrame({"episode": indices, "reward": rewards})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)

    # Also save as JSONL alongside CSV for flexibility
    jsonl_path = args.out.with_suffix(".jsonl")
    with open(jsonl_path, "w") as f:
        for i, r in enumerate(rewards):
            f.write(json.dumps({"episode": i, "reward": r}) + "\n")

    mean_reward = float(df["reward"].mean()) if len(df) > 0 else 0.0
    print(f"Saved {len(df)} rewards to {args.out}")
    print(f"Mean reward: {mean_reward:.4f}")


if __name__ == "__main__":
    main()

