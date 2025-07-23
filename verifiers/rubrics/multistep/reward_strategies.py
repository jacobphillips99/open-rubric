"""Reward calculation strategies for multistep rubric evaluation."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Union

from verifiers.rubrics.multistep.enums import EvaluationMode
from verifiers.rubrics.multistep.results import EvaluationResult


class RewardStrategy(ABC):
    """Abstract base class for reward calculation strategies."""

    @abstractmethod
    def calculate_reward(
        self,
        result: Union[Dict[str, Any], EvaluationResult],
        mode: EvaluationMode,
        **kwargs,
    ) -> float:
        """
        Calculate reward from evaluation results.

        Args:
            result: Either evaluation state dict or EvaluationResult object
            mode: The evaluation mode used
            **kwargs: Additional context for reward calculation

        Returns:
            float: The calculated reward
        """
        pass

    @property
    def name(self) -> str:
        """Return a human-readable name for this strategy."""
        return self.__class__.__name__.replace("RewardStrategy", "").lower()


class LevelWeightedRewardStrategy(RewardStrategy):
    """Current implementation: weighted sum where level number acts as weight."""

    def __init__(self, base_weight: float = 1.0, level_multiplier: float = 1.0):
        """
        Initialize the level weighted reward strategy.

        Args:
            base_weight: Base weight for all scores
            level_multiplier: Multiplier for level-based weighting
        """
        self.base_weight = base_weight
        self.level_multiplier = level_multiplier

    def calculate_reward(
        self,
        result: Union[Dict[str, Any], EvaluationResult],
        mode: EvaluationMode,
        **kwargs,
    ) -> float:
        """
        Calculate reward using level-weighted scoring.

        Args:
            result: Evaluation result or state dictionary
            mode: The evaluation mode used
            **kwargs: Additional context for reward calculation

        Returns:
            float: The calculated weighted reward
        """
        if isinstance(result, EvaluationResult):
            state = result.state
        else:
            state = result

        reward = 0.0
        for level_idx, level_scores in state.items():
            if isinstance(level_scores, dict):
                # Extract answer values from JudgeResponse dictionaries
                level_sum = sum(
                    score_data["answer"]
                    for score_data in level_scores.values()
                )
                # Convert level_idx to float for numeric operations
                level_num = (
                    float(level_idx)
                    if isinstance(level_idx, (str, int, float))
                    else 0.0
                )
                weight = self.base_weight + (level_num * self.level_multiplier)
                reward += weight * level_sum
        return reward


class SumRewardStrategy(RewardStrategy):
    """Simple sum of all scores across all levels."""

    def calculate_reward(
        self,
        result: Union[Dict[str, Any], EvaluationResult],
        mode: EvaluationMode,
        **kwargs,
    ) -> float:
        """
        Calculate reward as the sum of all scores.

        Args:
            result: Evaluation result or state dictionary
            mode: The evaluation mode used
            **kwargs: Additional context for reward calculation

        Returns:
            float: The sum of all scores
        """
        if isinstance(result, EvaluationResult):
            state = result.state
        else:
            state = result

        total = 0.0
        for level_scores in state.values():
            if isinstance(level_scores, dict):
                # Extract answer values from JudgeResponse dictionaries
                total += sum(
                    score_data["answer"] if isinstance(score_data, dict) and "answer" in score_data else score_data
                    for score_data in level_scores.values()
                )
        return total


class MeanRewardStrategy(RewardStrategy):
    """Average of all scores across all levels."""

    def calculate_reward(
        self,
        result: Union[Dict[str, Any], EvaluationResult],
        mode: EvaluationMode,
        **kwargs,
    ) -> float:
        """
        Calculate reward as the average of all scores.

        Args:
            result: Evaluation result or state dictionary
            mode: The evaluation mode used
            **kwargs: Additional context for reward calculation

        Returns:
            float: The average of all scores
        """
        if isinstance(result, EvaluationResult):
            state = result.state
        else:
            state = result

        total = 0.0
        count = 0
        for level_scores in state.values():
            if isinstance(level_scores, dict):
                # Extract answer values from JudgeResponse dictionaries
                total += sum(
                    score_data["answer"] if isinstance(score_data, dict) and "answer" in score_data else score_data
                    for score_data in level_scores.values()
                )
                count += len(level_scores)

        return total / count if count > 0 else 0.0


class LevelBasedRewardStrategy(RewardStrategy):
    """Reward based on the deepest level reached and completion."""

    def __init__(self, max_level_bonus: float = 1.0, completion_bonus: float = 0.5):
        """
        Initialize the level-based reward strategy.

        Args:
            max_level_bonus: Bonus for reaching deeper levels
            completion_bonus: Bonus multiplier based on completion ratio
        """
        self.max_level_bonus = max_level_bonus
        self.completion_bonus = completion_bonus

    def calculate_reward(
        self,
        result: Union[Dict[str, Any], EvaluationResult],
        mode: EvaluationMode,
        **kwargs,
    ) -> float:
        """
        Calculate reward based on deepest level and completion ratio.

        Args:
            result: Evaluation result or state dictionary
            mode: The evaluation mode used
            **kwargs: Additional context for reward calculation

        Returns:
            float: The calculated level-based reward
        """
        if isinstance(result, EvaluationResult):
            state = result.state
            completion_ratio = (
                result.completion_ratio if hasattr(result, "completion_ratio") else 0.0
            )
        else:
            state = result
            completion_ratio = 1.0  # Assume complete for non-EvaluationResult

        if not state:
            return 0.0

        # Base reward from deepest level reached
        max_level_key = max(state.keys()) if state else 0
        max_level = (
            float(max_level_key)
            if isinstance(max_level_key, (str, int, float))
            else 0.0
        )
        level_reward = max_level * self.max_level_bonus

        # Completion bonus
        completion_reward = completion_ratio * self.completion_bonus

        return level_reward + completion_reward


class CompletionRatioRewardStrategy(RewardStrategy):
    """Reward primarily based on completion ratio with quality bonus."""

    def __init__(self, ratio_weight: float = 1.0, quality_weight: float = 0.5):
        """
        Initialize the completion ratio reward strategy.

        Args:
            ratio_weight: Weight for completion ratio component
            quality_weight: Weight for average score quality component
        """
        self.ratio_weight = ratio_weight
        self.quality_weight = quality_weight

    def calculate_reward(
        self,
        result: Union[Dict[str, Any], EvaluationResult],
        mode: EvaluationMode,
        **kwargs,
    ) -> float:
        """
        Calculate reward based on completion ratio and quality.

        Args:
            result: Evaluation result or state dictionary
            mode: The evaluation mode used
            **kwargs: Additional context for reward calculation

        Returns:
            float: The calculated completion-based reward
        """
        if isinstance(result, EvaluationResult):
            state = result.state
            completion_ratio = (
                result.completion_ratio if hasattr(result, "completion_ratio") else 0.0
            )
        else:
            state = result
            # Estimate completion ratio for non-EvaluationResult
            total_requirements = kwargs.get("total_requirements", 1)
            completed = sum(
                len(level_scores)
                for level_scores in state.values()
                if isinstance(level_scores, dict)
            )
            completion_ratio = completed / total_requirements

        # Completion ratio component
        ratio_reward = completion_ratio * self.ratio_weight

        # Quality component (average of all scores)
        total_score = 0.0
        count = 0
        for level_scores in state.values():
            if isinstance(level_scores, dict):
                # Extract answer values from JudgeResponse dictionaries
                total_score += sum(
                    score_data["answer"] if isinstance(score_data, dict) and "answer" in score_data else score_data
                    for score_data in level_scores.values()
                )
                count += len(level_scores)

        quality_reward = (
            total_score / count if count > 0 else 0.0
        ) * self.quality_weight

        return ratio_reward + quality_reward


class ProgressiveRewardStrategy(RewardStrategy):
    """Exponentially increasing rewards for deeper levels."""

    def __init__(self, base_reward: float = 1.0, growth_factor: float = 1.5):
        """
        Initialize the progressive reward strategy.

        Args:
            base_reward: Base reward for level 0
            growth_factor: Exponential growth factor for deeper levels
        """
        self.base_reward = base_reward
        self.growth_factor = growth_factor

    def calculate_reward(
        self,
        result: Union[Dict[str, Any], EvaluationResult],
        mode: EvaluationMode,
        **kwargs,
    ) -> float:
        """
        Calculate reward with exponential growth for deeper levels.

        Args:
            result: Evaluation result or state dictionary
            mode: The evaluation mode used
            **kwargs: Additional context for reward calculation

        Returns:
            float: The calculated progressive reward
        """
        if isinstance(result, EvaluationResult):
            state = result.state
        else:
            state = result

        total_reward = 0.0
        for level_idx, level_scores in state.items():
            if isinstance(level_scores, dict):
                # Convert level_idx to float for numeric operations
                level_num = (
                    float(level_idx)
                    if isinstance(level_idx, (str, int, float))
                    else 0.0
                )
                level_multiplier = self.base_reward * (self.growth_factor**level_num)
                # Extract answer values from JudgeResponse dictionaries
                level_sum = sum(
                    score_data["answer"] if isinstance(score_data, dict) and "answer" in score_data else score_data
                    for score_data in level_scores.values()
                )
                total_reward += level_multiplier * level_sum

        return total_reward


NAME_TO_REWARD_STRATEGY_CLASS = {
    "levelweighted": LevelWeightedRewardStrategy,
    "sum": SumRewardStrategy,
    "mean": MeanRewardStrategy,
    "levelbased": LevelBasedRewardStrategy,
    "completionratio": CompletionRatioRewardStrategy,
    "progressive": ProgressiveRewardStrategy,
}


def make_reward_strategy(reward_strategy_type: str, **kwargs) -> RewardStrategy:
    """Make a reward strategy based on the reward_strategy_type."""
    return NAME_TO_REWARD_STRATEGY_CLASS[reward_strategy_type](**kwargs)


def make_reward_strategies(reward_strategies: list[dict]) -> list[RewardStrategy]:
    """Make a list of reward strategies based on the reward_strategies."""
    return [make_reward_strategy(r["type"], **r) for r in reward_strategies]
