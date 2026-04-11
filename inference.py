#!/usr/bin/env python3
"""
inference.py — Ad Integrity OpenEnv Agent
==========================================
Runs an LLM agent through all 5 content moderation tasks.

Required environment variables:
  API_BASE_URL   LLM API endpoint
  MODEL_NAME     Model identifier
  HF_TOKEN       HuggingFace / API key

Stdout format (MANDATORY — do not change):
  [START] task=<task> env=<benchmark> model=<model>
  [STEP]  step=<n> action=<action> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...>
"""

import os
import re
import textwrap
from typing import List, Optional

from tasks.graders import grade_episode, REWARD_EPS

# ── CRITICAL FIX: always use .get() with a default so no KeyError ──────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-3B-Instruct")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "dummy-key")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")

BENCHMARK             = "ad_integrity"
MAX_STEPS             = 5
SUCCESS_SCORE_THRESHOLD = 0.5
TEMPERATURE           = 0.1   # low temp → deterministic moderation decisions
MAX_TOKENS            = 64

# ── Tasks in order easy → hard ──────────────────────────────────────────────────
TASKS = [
    "spam_detection",
    "hate_speech_detection",
    "misinformation_detection",
    "safe_content",
    "multi_violation_detection",
]

SYSTEM_PROMPT = textwrap.dedent("""
    You are a world-class AI content moderator reviewing social media advertisements.
    You will receive an ad along with metadata (severity, category, flags).

    Your job is to make ONE decision. Choose exactly one:
      APPROVE  — Ad is legitimate, safe, follows all community guidelines
      REJECT   — Ad violates guidelines (spam, hate speech, false claims, illegal content)
      FLAG     — Ad is borderline and requires human review

    Respond with EXACTLY ONE WORD: APPROVE, REJECT, or FLAG.
    No explanation. No punctuation. No extra text. No reasoning.
""").strip()


# ── Logging helpers (mandatory format) ─────────────────────────────────────────
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val  = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


# ── LLM decision helper ─────────────────────────────────────────────────────────
def get_model_action(client, observation: str, history: List[str]) -> str:
    """Ask the LLM to make a moderation decision."""
    history_block = "\n".join(history[-3:]) if history else "None"
    user_prompt = textwrap.dedent(f"""
        Ad Content:
        {observation}

        Previous decisions this session:
        {history_block}

        Your moderation decision (APPROVE, REJECT, or FLAG):
    """).strip()

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip().upper()

        # Strip any chain-of-thought tags some models produce
        text = re.sub(r"<THINK>.*?</THINK>", "", text, flags=re.DOTALL)
        text = re.sub(r"<THINK>.*",          "", text, flags=re.DOTALL).strip()

        for decision in ("REJECT", "APPROVE", "FLAG"):   # REJECT first — safer default
            if decision in text:
                return decision.lower()

        print(f"[DEBUG] Unexpected model output: {text[:120]!r} — defaulting to reject", flush=True)
        return "reject"

    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return "reject"


# ── Single task runner ──────────────────────────────────────────────────────────
def run_task(client, task_name: str) -> None:
    """Run one full episode for a given task using direct HTTP calls."""
    import urllib.request
    import json

    history: List[str]  = []
    rewards: List[float]  = []
    steps_taken          = 0
    score                = 0.0
    success              = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    def http_post(path: str, payload: dict) -> dict:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            f"{ENV_BASE_URL}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    try:
        # ── reset ────────────────────────────────────────────────────────────
        reset_resp = http_post("/reset", {"task_id": task_name})
        obs_text   = (
            reset_resp.get("observation", {}).get("text", "")
            or reset_resp.get("observation", {}).get("ad_content", "")
            or str(reset_resp.get("observation", ""))
        )
        done = reset_resp.get("done", False)

        # ── steps ────────────────────────────────────────────────────────────
        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            action_str = get_model_action(client, obs_text, history)
            last_error: Optional[str] = None

            try:
                step_resp = http_post("/step", {"action": action_str})
                obs_text  = (
                    step_resp.get("observation", {}).get("text", "")
                    or step_resp.get("observation", {}).get("ad_content", "")
                    or obs_text
                )
                reward    = float(step_resp.get("reward", REWARD_EPS))
                done      = bool(step_resp.get("done", False))
            except Exception as exc:
                last_error = str(exc)
                reward     = REWARD_EPS
                done       = True

            rewards.append(reward)
            steps_taken = step
            log_step(step=step, action=action_str, reward=reward, done=done, error=last_error)
            history.append(f"Step {step}: {action_str} → reward {reward:.2f}")

            if done:
                break

        score   = grade_episode(rewards)
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as exc:
        print(f"[DEBUG] Task {task_name} setup error: {exc}", flush=True)
        if not rewards:
            rewards = [REWARD_EPS]
        score   = grade_episode(rewards)
        success = False

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


# ── Entry point ─────────────────────────────────────────────────────────────────
def main() -> None:
    from openai import OpenAI
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    for task_name in TASKS:
        run_task(client, task_name)


if __name__ == "__main__":
    main()
