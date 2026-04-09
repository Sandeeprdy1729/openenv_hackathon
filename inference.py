#!/usr/bin/env python3
import os
import sys
import time
import requests
import json
from typing import Dict, Any, List
from datetime import datetime


API_BASE_URL = os.environ["API_BASE_URL"]
API_KEY = os.environ["API_KEY"]
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:7860")


try:
    from openai import OpenAI

    # Force the client to use the exact proxy URL and injected API key
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


def log_start(task: str, env: str, model: str):
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: str = None):
    error_str = f" error={error}" if error else ""
    print(
        f"[STEP]  step={step} action={action} reward={reward:.4f} done={str(done).lower()}{error_str}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]):
    rewards_str = ",".join([f"{r:.4f}" for r in rewards])
    print(
        f"[END]   success={str(success).lower()} steps={steps} score={score:.4f} rewards={rewards_str}",
        flush=True,
    )


def format_reward(reward: float) -> str:
    return f"{reward:.4f}"


def analyze_and_decide(observation: Dict[str, Any], client) -> Dict[str, Any]:
    """LLM-powered decision making using OpenAI API."""
    current_ad = observation.get("current_ad", {})

    prompt = f"""
    You are an AI Safety moderator. Analyze this ad and respond ONLY with a JSON object containing 'action', 'tool_parameters' (if needed), and 'rationale'.
    Ad Text: {current_ad.get("ad_text")}
    Severity: {current_ad.get("severity_level")}
    Available Actions: APPROVE, FLAG, REJECT, VERIFY_EVIDENCE, CHECK_URL_CHAIN, GENERATE_DOSSIER.
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"action": "APPROVE", "rationale": f"Fallback due to error: {e}"}


def main():
    task = sys.argv[1] if len(sys.argv) > 1 else "easy_prohibited_content"
    MAX_STEPS = 50

    client = None
    if HAS_OPENAI:
        try:
            client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
        except Exception:
            pass

    log_start(task=task, env="MetaGuardPro", model=MODEL_NAME)

    # Reset environment
    try:
        reset_resp = requests.post(
            f"{BASE_URL}/reset", params={"task": task}, timeout=10
        )
        if reset_resp.status_code != 200:
            print(
                f"[DEBUG] Reset failed: {reset_resp.status_code}",
                flush=True,
                file=sys.stderr,
            )
            log_end(success=False, steps=0, score=0.0, rewards=[])
            return
        initial_obs = reset_resp.json().get("observation", {})
    except Exception as e:
        print(f"[DEBUG] Reset error: {e}", flush=True, file=sys.stderr)
        log_end(success=False, steps=0, score=0.0, rewards=[])
        return

    total_reward = 0.0
    steps = 0
    tools_used = 0
    rewards = []
    start_time = time.time()

    while steps < MAX_STEPS:
        # Check state
        try:
            state_resp = requests.get(f"{BASE_URL}/state", timeout=5)
            state = state_resp.json()
            if state.get("queue_size", 0) == 0:
                break
        except Exception as e:
            log_step(step=steps + 1, action="ERROR", reward=0, done=True, error=str(e))
            break

        current_obs = initial_obs.get("current_ad")
        if not current_obs:
            step_resp = requests.post(
                f"{BASE_URL}/step",
                json={"action": "APPROVE", "rationale": "No content"},
            )
            step_result = step_resp.json()
            reward = step_result.get("reward", 0)
            total_reward += reward
            steps += 1
            rewards.append(reward)
            log_step(
                step=steps,
                action="APPROVE",
                reward=reward,
                done=step_result.get("done", False),
            )
            initial_obs = step_result.get("observation", {})
            if step_result.get("done"):
                break
            continue

        # Analyze and decide
        decision = analyze_and_decide(initial_obs, client)
        action_type = decision.get("action", "APPROVE")

        is_tool_call = action_type in [
            "CHECK_URL_CHAIN",
            "CHECK_ADVERTISER",
            "CHECK_COORDINATION",
            "SEARCH_POLICY",
            "VERIFY_CLAIM",
            "SCAN_MEDIA",
            "GENERATE_DOSSIER",
            "VERIFY_EVIDENCE",
            "IMAGE_PROVENANCE_CHECK",
        ]

        if is_tool_call:
            tools_used += 1

            step_resp = requests.post(
                f"{BASE_URL}/step",
                json={
                    "action": action_type,
                    "tool_parameters": decision.get("tool_parameters", {}),
                    "rationale": decision.get("rationale", ""),
                },
            )
            step_result = step_resp.json()

            if step_result.get("done"):
                reward = step_result.get("reward", 0)
                total_reward += reward
                steps += 1
                rewards.append(reward)
                log_step(step=steps, action=action_type, reward=reward, done=True)
                break

            tool_result = step_result.get("info", {}).get("tool_result", {})
            obs = step_result.get("observation", {})

            # Handle VERIFY_EVIDENCE with truth_grounded
            if action_type == "VERIFY_EVIDENCE" and tool_result.get("truth_grounded"):
                status = tool_result.get("status", "UNKNOWN")
                captured_source = tool_result.get("source", "")
                captured_core = tool_result.get("core_assertion", "")

                if status == "FALSE":
                    # Check image provenance then reject
                    step_resp = requests.post(
                        f"{BASE_URL}/step",
                        json={
                            "action": "IMAGE_PROVENANCE_CHECK",
                            "tool_parameters": {},
                            "rationale": f"Evidence verified FALSE by {captured_source}",
                        },
                    )
                    step_result = step_resp.json()
                    if step_result.get("done"):
                        reward = step_result.get("reward", 0)
                        total_reward += reward
                        steps += 1
                        rewards.append(reward)
                        log_step(step=steps, action="REJECT", reward=reward, done=True)
                        break

                    prov_result = step_result.get("info", {}).get("tool_result", {})
                    dsa_rationale = (
                        f"Health disinformation verified FALSE by {captured_source}."
                    )

                    step_resp = requests.post(
                        f"{BASE_URL}/step",
                        json={"action": "REJECT", "rationale": dsa_rationale},
                    )
                    step_result = step_resp.json()
                else:
                    step_resp = requests.post(
                        f"{BASE_URL}/step",
                        json={
                            "action": "APPROVE",
                            "rationale": f"Evidence check: {captured_source}",
                        },
                    )
                    step_result = step_resp.json()

                reward = step_result.get("reward", 0)
                total_reward += reward
                steps += 1
                rewards.append(reward)
                log_step(
                    step=steps,
                    action="REJECT" if status == "FALSE" else "APPROVE",
                    reward=reward,
                    done=step_result.get("done", False),
                )
                initial_obs = step_result.get("observation", {})
                if step_result.get("done"):
                    break
                continue

            # Handle other tool results
            if action_type == "VERIFY_CLAIM" and tool_result.get("verified"):
                status = tool_result.get("status", "UNKNOWN")
                if status == "FALSE":
                    step_resp = requests.post(
                        f"{BASE_URL}/step",
                        json={
                            "action": "REJECT",
                            "rationale": f"DISINFO: Fact-check verified FALSE. Source: {tool_result.get('source')}",
                        },
                    )
                else:
                    step_resp = requests.post(
                        f"{BASE_URL}/step",
                        json={
                            "action": "APPROVE",
                            "rationale": "No fact-check match found",
                        },
                    )
            elif action_type == "CHECK_COORDINATION" and tool_result.get(
                "is_coordinated"
            ):
                step_resp = requests.post(
                    f"{BASE_URL}/step",
                    json={
                        "action": "REJECT",
                        "rationale": f"CIB: Bot farm pattern - {tool_result.get('posting_pattern')}",
                    },
                )
            elif action_type == "CHECK_URL_CHAIN" and tool_result.get("is_suspicious"):
                step_resp = requests.post(
                    f"{BASE_URL}/step",
                    json={
                        "action": "REJECT",
                        "rationale": f"Bridge page: {tool_result.get('redirection_scheme')}",
                    },
                )
            elif action_type == "GENERATE_DOSSIER" and tool_result.get("generated"):
                step_resp = requests.post(
                    f"{BASE_URL}/step",
                    json={
                        "action": "REJECT",
                        "rationale": decision.get("rationale", ""),
                        "dossier": tool_result.get("content", ""),
                    },
                )
            else:
                step_resp = requests.post(
                    f"{BASE_URL}/step",
                    json={
                        "action": "APPROVE",
                        "rationale": f"Tool {action_type}: No issues found",
                    },
                )
        else:
            step_resp = requests.post(
                f"{BASE_URL}/step",
                json={
                    "action": action_type,
                    "rationale": decision.get("rationale", ""),
                },
            )

        step_result = step_resp.json()
        reward = step_result.get("reward", 0)
        total_reward += reward
        steps += 1
        rewards.append(reward)
        done = step_result.get("done", False)

        log_step(step=steps, action=action_type, reward=reward, done=done)
        initial_obs = step_result.get("observation", {})

        if done:
            break

    # Calculate final score
    elapsed = time.time() - start_time
    final_state = requests.get(f"{BASE_URL}/state").json()
    accuracy = final_state.get("accuracy", 0.0)

    # Normalize total reward to 0-1 range
    score = min(max(total_reward / 12.0, 0.0), 1.0)  # 12 is max steps * max reward
    success = score >= 0.5

    log_end(success=success, steps=steps, score=score, rewards=rewards)

    print(
        f"[DEBUG] Elapsed: {elapsed:.1f}s | Accuracy: {accuracy:.2f} | Tools: {tools_used}",
        flush=True,
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
