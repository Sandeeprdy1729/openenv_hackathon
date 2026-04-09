from typing import Dict, Any

from openenv.core import EnvClient
from openenv.core.client_types import StepResult

try:
    from .models import AdModerationAction, AdModerationObservation, AdModerationState
except ImportError:
    from models import AdModerationAction, AdModerationObservation, AdModerationState


class AdModerationClient(
    EnvClient[AdModerationAction, AdModerationObservation, AdModerationState]
):
    """Client for the Ad Moderation Environment."""

    def _step_payload(self, action: AdModerationAction) -> Dict[str, Any]:
        return action.model_dump()

    def _parse_result(
        self, payload: Dict[str, Any]
    ) -> StepResult[AdModerationObservation]:
        obs_data = payload.get("observation", {})

        observation = AdModerationObservation(
            text=obs_data.get("text", payload.get("text", "")),
            task_id=obs_data.get("task_id", payload.get("task_id", "")),
            ad_content=obs_data.get("ad_content", ""),
            severity=obs_data.get("severity", "none"),
            reward=payload.get("reward"),
            done=payload.get("done", False),
            metadata=payload.get("info", payload.get("metadata", {})),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> AdModerationState:
        return AdModerationState(
            task_id=payload.get("task_id", ""),
            step=payload.get("step", 0),
            max_steps=payload.get("max_steps", 0),
            history=payload.get("history", []),
            done=payload.get("done", False),
        )
