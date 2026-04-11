"""
server/ad_moderation_environment.py — Core RL environment for MetaGuard.

Each episode randomly selects one AdCase from the active task's case pool.
The observation gives the agent the ad text plus contextual signals.
The step function grades the action and returns a calibrated reward.
"""

import random
from typing import Any, Dict, Optional

from tasks.definitions import ALL_TASKS, AdCase, TaskDefinition
from tasks.graders import grade_action, grade_episode


class AdModerationEnvironment:
    """
    OpenEnv-compliant RL environment for ad content moderation.

    Episode flow
    ------------
    1. reset(task_id)  → selects a random AdCase, returns initial observation
    2. step(action)    → grades action, advances state, returns (obs, reward, done, info)
    3. Repeat step until done == True (max_steps reached)
    """

    MAX_STEPS = 3

    def __init__(self) -> None:
        self._task: Optional[TaskDefinition] = None
        self._current_case: Optional[AdCase] = None
        self._step_count: int = 0
        self._rewards: list[float] = []
        self._done: bool = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(self, task_id: str) -> Dict[str, Any]:
        """Start a new episode for the given task. Returns the first observation."""
        if task_id not in ALL_TASKS:
            raise ValueError(
                f"Unknown task '{task_id}'. "
                f"Available: {list(ALL_TASKS.keys())}"
            )

        self._task = ALL_TASKS[task_id]
        self._current_case = random.choice(self._task.cases)
        self._step_count = 0
        self._rewards = []
        self._done = False

        return self._build_observation()

    def step(self, action: str) -> Dict[str, Any]:
        """
        Take one action in the current episode.

        Returns a dict with keys: observation, reward, done, info.
        """
        if self._done or self._current_case is None:
            raise RuntimeError("Call reset() before step().")

        self._step_count += 1

        reward = grade_action(
            agent_action=action,
            correct_action=self._current_case.correct_action,
            severity=self._current_case.severity,
            step=self._step_count,
            max_steps=self.MAX_STEPS,
            adversarial=self._current_case.adversarial,
        )
        self._rewards.append(reward)

        done = self._step_count >= self.MAX_STEPS

        if done:
            self._done = True
            # Rotate to a new case for the final observation (summary mode)
            next_obs = self._build_summary_observation(reward)
        else:
            # Pick a new case for the next step within the same episode
            self._current_case = random.choice(self._task.cases)  # type: ignore[arg-type]
            next_obs = self._build_observation()

        info = {
            "correct_action": self._current_case.correct_action if not done else None,
            "episode_score": grade_episode(self._rewards) if done else None,
            "step": self._step_count,
            "adversarial": self._current_case.adversarial if not done else None,
        }

        return {
            "observation": next_obs,
            "reward": reward,
            "done": done,
            "info": info,
        }

    def get_state(self) -> Dict[str, Any]:
        """Return current environment state snapshot."""
        return {
            "task_id": self._task.task_id if self._task else None,
            "step": self._step_count,
            "done": self._done,
            "rewards_so_far": self._rewards,
            "episode_score": grade_episode(self._rewards) if self._done else None,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_observation(self) -> Dict[str, Any]:
        """Build the structured observation dict for the current case."""
        assert self._current_case is not None
        assert self._task is not None

        case = self._current_case
        task = self._task

        prompt = self._build_prompt(case, task)

        return {
            "text": prompt,
            "task_id": task.task_id,
            "ad_content": case.ad_text,
            "severity": case.severity,
            "category": task.policy_focus,
            "flags": self._derive_flags(case),
            "step": self._step_count,
            "max_steps": self.MAX_STEPS,
        }

    def _build_prompt(self, case: AdCase, task: TaskDefinition) -> str:
        """Construct the natural language prompt shown to the agent."""
        flag_list = self._derive_flags(case)
        flags_str = ", ".join(flag_list) if flag_list else "none detected"

        return (
            f"## Ad Moderation Task: {task.task_id}\n\n"
            f"**Policy focus:** {task.policy_focus}\n"
            f"**Severity signal:** {case.severity}\n"
            f"**Pre-detection flags:** {flags_str}\n\n"
            f"---\n\n"
            f"**Advertisement content:**\n\n"
            f"{case.ad_text}\n\n"
            f"---\n\n"
            f"Based on the advertisement above and the pre-detection signals, "
            f"choose one of the following actions:\n\n"
            f"- **approve** — Ad is legitimate and complies with policy\n"
            f"- **reject** — Ad violates policy and must be removed\n"
            f"- **flag** — Ad is borderline or politically sensitive — escalate for human review\n\n"
            f"Respond with ONLY the action word: approve, reject, or flag."
        )

    def _build_summary_observation(self, final_reward: float) -> Dict[str, Any]:
        """Final step observation after episode ends."""
        return {
            "text": f"Episode complete. Final step reward: {final_reward:.4f}.",
            "task_id": self._task.task_id if self._task else None,
            "ad_content": "",
            "severity": "low",
            "category": "",
            "flags": [],
            "step": self._step_count,
            "max_steps": self.MAX_STEPS,
        }

    @staticmethod
    def _derive_flags(case: AdCase) -> list[str]:
        """
        Derive pre-detection flags from the ad case metadata.
        These give the agent contextual signals without giving away the answer.
        """
        flags = []
        text_lower = case.ad_text.lower()

        if any(w in text_lower for w in ["limited", "only", "expires", "hurry", "now", "today only"]):
            flags.append("urgency_language")
        if any(w in text_lower for w in ["click", "verify", "confirm", "account", "credential"]):
            flags.append("credential_request")
        if any(w in text_lower for w in ["doctor", "medical", "clinical", "cure", "treat", "heal"]):
            flags.append("medical_claim")
        if any(w in text_lower for w in ["they", "these people", "wrong kind", "our culture", "globalist"]):
            flags.append("othering_language")
        if any(w in text_lower for w in ["natural", "detox", "cleanse", "frequency", "vibration", "alkaline"]):
            flags.append("pseudoscience_indicator")
        if any(w in text_lower for w in ["paid for by", "vote", "elect", "senator", "congress"]):
            flags.append("political_content")

        return flags