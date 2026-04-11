"""
tasks/graders.py — Reward grading for the Ad Integrity environment.

All externally visible rewards and scores are kept strictly within (0, 1)
so they pass OpenEnv's phase-2 validation checks after stdout formatting.
"""

from typing import Dict


SEVERITY_MULTIPLIER: Dict[str, float] = {
    "low":      1.0,
    "medium":   1.1,
    "high":     1.2,
    "critical": 1.3,
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
) -> float:
    """
    Return a reward strictly inside (0, 1) based on how correct the action is.

    Scoring philosophy:
      - Full credit for exact match, scaled by severity (critical violations matter more).
      - Partial credit for FLAG when REJECT was correct (the agent noticed something).
      - Zero credit for APPROVE on a harmful ad (worst outcome — content slips through).
      - Speed bonus for faster correct decisions.
    """
    agent_action   = agent_action.lower().strip()
    correct_action = correct_action.lower().strip()
    mult           = SEVERITY_MULTIPLIER.get(severity, 1.0)

    if agent_action == correct_action:
        base = 1.0
        speed_bonus = max(0.0, (max_steps - step + 1) * 0.05)
    elif agent_action == "flag" and correct_action == "reject":
        base = 0.4      # partial — noticed a problem, not decisive
        speed_bonus = 0.0
    elif agent_action == "flag" and correct_action == "approve":
        base = 0.5      # overly cautious but not catastrophically wrong
        speed_bonus = 0.0
    elif agent_action == "approve" and correct_action == "reject":
        base = 0.0      # worst case: harmful content approved
        speed_bonus = 0.0
    elif agent_action == "reject" and correct_action == "approve":
        base = 0.1      # over-censorship — bad but less dangerous than the reverse
        speed_bonus = 0.0
    else:
        base = 0.1
        speed_bonus = 0.0

    reward = max(REWARD_EPS, min(base * mult + speed_bonus, 1.0 - REWARD_EPS))
    return round(reward, 4)


def grade_episode(rewards: list) -> float:
    """Aggregate per-step rewards into a final episode score strictly in (0, 1)."""
    if not rewards:
        return round(SCORE_EPS, 4)
    score = sum(rewards) / len(rewards)
    score = max(SCORE_EPS, min(score, 1.0 - SCORE_EPS))
    return round(score, 4)
