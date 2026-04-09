from typing import List, Optional
from openenv.core.env_server.types import Action, Observation, State


class AdModerationAction(Action):
    action: str  # "approve", "reject", "flag"


class AdModerationObservation(Observation):
    text: str
    task_id: str
    ad_content: str
    severity: str


class AdModerationState(State):
    task_id: str
    step: int
    max_steps: int
    history: List[str]
    done: bool
