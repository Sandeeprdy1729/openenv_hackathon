"""
tasks/graders.py — Reward grading for the Ad Integrity environment

Each grader returns a float in [0.0, 1.0].
"""

from typing import Dict


SEVERITY_MULTIPLIER: Dict[str, float] = {
    "low":      1.0,
    "medium":   1.1,
    "high":     1.2,
    "critical": 1.3,
}


def grade_action(
    agent_action: str,
    correct_action: str,
    severity: str = "medium",
    step: int = 1,
    max_steps: int = 3,
) -> float:
    """
    Return a reward in [0.0, 1.0] based on how correct the agent's action is.

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

    reward = min(1.0, base * mult + speed_bonus)
    return round(reward, 4)


def grade_episode(rewards: list) -> float:
    """Aggregate per-step rewards into a final episode score in [0.0, 1.0]."""
    if not rewards:
        return 0.0
    return round(sum(rewards) / len(rewards), 4)