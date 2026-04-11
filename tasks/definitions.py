"""
tasks/definitions.py — Task and case definitions for the MetaGuard benchmark.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal


Severity = Literal["low", "medium", "high", "critical"]
Difficulty = Literal["easy", "medium", "hard"]
Action = Literal["approve", "reject", "flag"]


@dataclass(frozen=True)
class AdCase:
    ad_text: str
    correct_action: Action
    severity: Severity
    adversarial: bool = False
    notes: str = ""


@dataclass(frozen=True)
class TaskDefinition:
    task_id: str
    description: str
    difficulty: Difficulty
    policy_focus: str
    cases: List[AdCase] = field(default_factory=list)


TASK_DEFINITIONS: List[TaskDefinition] = [
    TaskDefinition(
        task_id="spam_detection",
        description="Detect phishing, deceptive giveaways, fake support notices, and ambiguous lead-gen spam.",
        difficulty="medium",
        policy_focus="Spam, phishing, deceptive urgency, and suspicious account/payment recovery flows.",
        cases=[
            AdCase("WIN a FREE iPhone 15 today. Click the secure claim form now before your prize expires tonight.", "reject", "high"),
            AdCase("Meta Commerce Notice: seller payouts are paused until you verify at meta-support-payments.help.", "reject", "critical", adversarial=True),
            AdCase("Earn from home with our verified partner marketplace. Applications close Friday due to mentor capacity.", "flag", "medium", adversarial=True),
        ],
    ),
    TaskDefinition(
        task_id="hate_speech_detection",
        description="Detect explicit hate speech, dehumanization, and softer coded exclusion language.",
        difficulty="hard",
        policy_focus="Hate speech, protected-class discrimination, coded exclusion, and identity-targeting dog whistles.",
        cases=[
            AdCase("Support your own kind, not those [slur] who steal our jobs.", "reject", "critical"),
            AdCase("Rent only to families who share our traditions and values, not to people who bring foreign customs.", "reject", "high", adversarial=True),
            AdCase("Choose a neighborhood that matches your family's values and avoids rapid cultural change.", "flag", "medium", adversarial=True),
        ],
    ),
    TaskDefinition(
        task_id="misinformation_detection",
        description="Identify dangerous medical misinformation, conspiracy-style health claims, and softer wellness claims requiring review.",
        difficulty="hard",
        policy_focus="Medical misinformation, pseudoscience, conspiracy framing, and borderline health claims.",
        cases=[
            AdCase("This silver tonic neutralizes spike proteins after vaccination and restores cellular balance naturally.", "reject", "critical", adversarial=True),
            AdCase("Doctors hate him: this trick cures cancer in 3 days with lemon juice and baking soda.", "reject", "critical"),
            AdCase("Boost your immunity naturally with citrus, ginger, and herbal tea inspired by traditional wellness practices.", "flag", "medium", adversarial=True),
        ],
    ),
    TaskDefinition(
        task_id="safe_content",
        description="Approve legitimate advertisements even when they use urgency, discounts, trials, or regulated-service wording.",
        difficulty="medium",
        policy_focus="Legitimate commerce, promotions, subscriptions, and regulated offers without policy violations.",
        cases=[
            AdCase("Nike running shoes: 50% off before weekend inventory resets. Official support and return policy at checkout.", "approve", "medium", adversarial=True),
            AdCase("Book a free consultation with licensed financial planners at Fidelity. Risks disclosed clearly before signup.", "approve", "medium", adversarial=True),
            AdCase("Freshly roasted single-origin coffee delivered within 48 hours of roasting. First bag free.", "approve", "low"),
        ],
    ),
    TaskDefinition(
        task_id="multi_violation_detection",
        description="Detect ads combining multiple policy violations and mixed-signal cases where FLAG may be more appropriate than immediate REJECT.",
        difficulty="hard",
        policy_focus="Combined hate speech, misinformation, fraud, and conspiracy cues with nuanced escalation decisions.",
        cases=[
            AdCase("Patriots only: stop migrant families replacing your neighborhood. Our detox capsules remove vaccine toxins in 48 hours.", "reject", "critical", adversarial=True),
            AdCase("Schools are hiding a fluoride sterilization program targeted at traditional families. Buy our shield patch now and win cash.", "reject", "critical", adversarial=True),
            AdCase("A private wellness group says mainstream media suppresses detox methods used by patriotic families. Join the waitlist while research is reviewed.", "flag", "high", adversarial=True),
        ],
    ),
]


TASK_MAP: Dict[str, TaskDefinition] = {task.task_id: task for task in TASK_DEFINITIONS}
ALL_TASKS: Dict[str, TaskDefinition] = TASK_MAP
