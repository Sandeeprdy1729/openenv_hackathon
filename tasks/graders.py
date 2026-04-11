"""
tasks/graders.py — Reward grading for the Ad Integrity environment.

The grading is intentionally shaped to be validator-safe while still producing
meaningful spread between:
- strong exact decisions,
- reasonable but cautious FLAG decisions,
- over-censorship on legitimate ads,
- and catastrophic misses that approve harmful content.
"""

from typing import Dict


SEVERITY_MULTIPLIER: Dict[str, float] = {
    "low":      1.0,
    "medium":   1.1,
    "high":     1.2,
    "critical": 1.3,
}

SEVERITY_BONUS: Dict[str, float] = {
    "low": 0.00,
    "medium": 0.03,
    "high": 0.06,
    "critical": 0.09,
}

# Rewards are logged with 2 decimals, so keep them far enough from the bounds
# that formatting can never turn them into 0.00 or 1.00.
REWARD_EPS = 0.01

# Episode scores are logged with 3 decimals.
SCORE_EPS = 0.001


def grade_action(
    agent_action: str,
    correct_action: str,
    severity: str = "medium",
    step: int = 1,
    max_steps: int = 3,
    adversarial: bool = False,
) -> float:
    """
    Return a reward strictly inside (0, 1) based on moderation quality.

    Scoring philosophy:
      - REJECT is strongest on clearly harmful content, but no longer saturates to 0.99.
      - APPROVE on legitimate ads earns high but slightly lower scores than severe rejects.
      - FLAG is rewarded as a calibrated ambiguity action, not as a free near-perfect answer.
      - Over-censorship is penalized, but still scores better than letting harmful content through.
      - Approving harmful content remains the worst-case outcome.
    """
    agent_action   = agent_action.lower().strip()
    correct_action = correct_action.lower().strip()
    severity_bonus = SEVERITY_BONUS.get(severity, 0.0)

    if agent_action == correct_action:
        exact_reward = {
            "approve": 0.84,
            "reject": 0.88,
            "flag": 0.72,
        }
        base = exact_reward.get(correct_action, 0.80)
        speed_bonus = max(0.0, (max_steps - step + 1) * 0.015)
    elif agent_action == "flag" and correct_action == "reject":
        base = 0.42
        speed_bonus = 0.0
    elif agent_action == "flag" and correct_action == "approve":
        base = 0.34
        speed_bonus = 0.0
    elif agent_action == "reject" and correct_action == "flag":
        base = 0.48
        speed_bonus = 0.0
    elif agent_action == "approve" and correct_action == "flag":
        base = 0.22
        speed_bonus = 0.0
    elif agent_action == "reject" and correct_action == "approve":
        base = 0.12
        speed_bonus = 0.0
    elif agent_action == "approve" and correct_action == "reject":
        base = 0.0
        speed_bonus = 0.0
    else:
        base = 0.08
        speed_bonus = 0.0

    # Adversarial cases should preserve reward ordering while slightly reducing
    # partial-credit outcomes, which helps harder examples separate models.
    if adversarial and 0.0 < base < 1.0:
        base *= 0.85

    reward = max(REWARD_EPS, min(base + severity_bonus + speed_bonus, 1.0 - REWARD_EPS))
    return round(reward, 4)


def grade_episode(rewards: list) -> float:
    """Aggregate per-step rewards into a final episode score strictly in (0, 1)."""
    if not rewards:
        return round(SCORE_EPS, 4)
    score = sum(rewards) / len(rewards)
    score = max(SCORE_EPS, min(score, 1.0 - SCORE_EPS))
    return round(score, 4)
