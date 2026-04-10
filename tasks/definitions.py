"""
tasks/definitions.py — Task definitions for the Ad Integrity environment
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class TaskDefinition:
    task_id: str
    description: str
    difficulty: str          # "easy" | "medium" | "hard"
    correct_action: str      # ground-truth for default scenario
    reward_range: tuple = (0.0, 1.0)
    tags: List[str] = field(default_factory=list)


TASK_DEFINITIONS = [
    TaskDefinition(
        task_id="spam_detection",
        description=(
            "Identify spam advertisements including phishing, prize scams, "
            "get-rich-quick schemes, and suspicious links. "
            "Correct decision: REJECT."
        ),
        difficulty="easy",
        correct_action="reject",
        tags=["spam", "phishing", "fraud"],
    ),
    TaskDefinition(
        task_id="hate_speech_detection",
        description=(
            "Detect advertisements containing hate speech, slurs, discrimination "
            "based on ethnicity, religion, gender, or other protected characteristics. "
            "Correct decision: REJECT."
        ),
        difficulty="medium",
        correct_action="reject",
        tags=["hate_speech", "discrimination", "safety"],
    ),
    TaskDefinition(
        task_id="misinformation_detection",
        description=(
            "Identify ads promoting false medical claims, pseudoscience, "
            "conspiracy theories, or dangerous health misinformation. "
            "Correct decision: REJECT."
        ),
        difficulty="medium",
        correct_action="reject",
        tags=["misinformation", "health", "pseudoscience"],
    ),
    TaskDefinition(
        task_id="safe_content",
        description=(
            "Approve legitimate, high-quality advertisements from real brands "
            "that follow all community guidelines and contain no violations. "
            "Correct decision: APPROVE."
        ),
        difficulty="easy",
        correct_action="approve",
        tags=["safe", "legitimate", "brand"],
    ),
    TaskDefinition(
        task_id="multi_violation_detection",
        description=(
            "Detect complex ads that combine multiple policy violations — "
            "e.g., hate speech + misinformation + spam. "
            "Requires nuanced multi-signal reasoning. Correct decision: REJECT."
        ),
        difficulty="hard",
        correct_action="reject",
        tags=["multi_violation", "complex", "hard"],
    ),
]

TASK_MAP = {t.task_id: t for t in TASK_DEFINITIONS}