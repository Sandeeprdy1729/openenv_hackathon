from typing import List, Optional
from openenv.core.env_server.types import Action, Observation, State


class AdModerationAction(Action):
    """Agent action: approve / reject / flag an advertisement."""
    action: str  # "approve", "reject", or "flag"


class AdModerationObservation(Observation):
    """What the agent sees each step."""
    text: str                        # full prompt text shown to the agent
    task_id: str
    ad_content: str
    severity: str                    # "low" | "medium" | "high" | "critical"
    category: Optional[str] = None   # spam | hate_speech | misinformation | safe | multi_violation
    flags: Optional[List[str]] = None


class AdModerationState(State):
    """Internal environment state (not shown to agent directly)."""
    task_id: str
    step: int
    max_steps: int
    history: List[str]
    done: bool
    correct_action: Optional[str] = None  # ground-truth label for grading