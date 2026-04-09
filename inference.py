#!/usr/bin/env python3
"""
inference.py — Ad Moderation OpenEnv Agent
==========================================
Runs an LLM agent through all 4 content moderation tasks.

Required environment variables:
    API_BASE_URL      LLM API endpoint
    MODEL_NAME        Model identifier
    HF_TOKEN          HuggingFace / API key
    LOCAL_IMAGE_NAME  (optional) Docker image to launch as env server

Stdout format:
    [START] task=<task> env=<benchmark> model=<model>
    [STEP]  step=<n> action=<action> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...>
"""

import os
import textwrap
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI

from models import AdModerationAction
from client import AdModerationClient

IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")
BENCHMARK = "ad_moderation"

MAX_STEPS = 3
SUCCESS_SCORE_THRESHOLD = 0.5
TEMPERATURE = 0.2
MAX_TOKENS = 1024

TASKS = [
    "spam_detection",
    "hate_speech_detection",
    "misinformation_detection",
    "safe_content",
]

SYSTEM_PROMPT = textwrap.dedent("""
    You are an AI content moderator for social media advertisements.
    You will receive ad content with severity indicators and metadata.

    Choose exactly one action:
      APPROVE  — Content is legitimate and follows community guidelines
      REJECT  — Content violates guidelines (spam, hate speech, misinformation)
      FLAG    — Content needs additional review

    Reply with EXACTLY ONE WORD: APPROVE, REJECT, or FLAG.
    No explanation. No punctuation. No extra text.
""").strip()


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(
    step: int, action: str, reward: float, done: bool, error: Optional[str]
) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


def get_model_action(client: OpenAI, observation: str, history: List[str]) -> str:
    """Ask the LLM to decide APPROVE / REJECT / FLAG."""
    history_block = "\n".join(history[-3:]) if history else "None"
    user_prompt = f"""Ad Content:
{observation}

Previous decisions this episode:
{history_block}

Your decision (APPROVE, REJECT, or FLAG):"""

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        import re

        text = (completion.choices[0].message.content or "").strip().upper()

        text_no_think = re.sub(r"<THINK>.*?</THINK>", "", text, flags=re.DOTALL)
        text_no_think = re.sub(r"<THINK>.*", "", text_no_think, flags=re.DOTALL)

        for action in ("APPROVE", "REJECT", "FLAG"):
            if action in text_no_think:
                return action.lower()

        for action in ("APPROVE", "REJECT", "FLAG"):
            if action in text:
                return action.lower()

        print(
            f"[DEBUG] Unexpected model output: {text[:100]!r} — defaulting to approve"
        )
        return "approve"

    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}")
        return "approve"


def run_task(client: OpenAI, task_name: str) -> None:
    """Run one full episode for the given task."""

    if IMAGE_NAME:
        env_instance = AdModerationClient.from_docker_image(IMAGE_NAME, task=task_name)
    else:
        env_instance = AdModerationClient(base_url=ENV_BASE_URL)

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    last_error: Optional[str] = None

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        with env_instance.sync() as env:
            if not IMAGE_NAME:
                result = env.reset(task_id=task_name)
            else:
                result = env.reset()

            for step in range(1, MAX_STEPS + 1):
                if result.done:
                    break

                observation_text = result.observation.text
                action_str = get_model_action(client, observation_text, history)

                try:
                    result = env.step(AdModerationAction(action=action_str))
                    last_error = None
                except Exception as exc:
                    last_error = str(exc)
                    result.done = True

                reward = result.reward or 0.0
                done = result.done

                rewards.append(reward)
                steps_taken = step

                log_step(
                    step=step,
                    action=action_str,
                    reward=reward,
                    done=done,
                    error=last_error,
                )
                history.append(f"Step {step}: {action_str} → reward {reward:.2f}")

                if done:
                    break

        score = sum(rewards) / len(rewards) if rewards else 0.0
        score = max(1e-6, min(score, 1 - 1e-6))
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as exc:
        print(f"[DEBUG] Task {task_name} error: {exc}")
        last_error = str(exc)

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    for task_name in TASKS:
        run_task(client, task_name)


if __name__ == "__main__":
    main()
