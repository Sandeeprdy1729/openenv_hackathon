"""
server/app.py — Ad Integrity OpenEnv FastAPI Server
====================================================
Implements /reset, /step, /state, /health endpoints compliant
with the OpenEnv spec.
"""

import random
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from tasks.graders import grade_action

# ── In-memory episode state ────────────────────────────────────────────────────
_state: Dict[str, Any] = {}

# ── Ad bank: (ad_content, severity, correct_action, category) ─────────────────
AD_BANK: Dict[str, List[Dict]] = {
    "spam_detection": [
        {
            "ad_content": "🚨 WINNER! You've been selected for a FREE iPhone 15! Click NOW → bit.ly/free-iphone-scam123. Limited to first 100 clickers! ACT FAST!!!",
            "severity": "high",
            "correct_action": "reject",
            "category": "spam",
            "flags": ["urgency_language", "suspicious_url", "prize_bait"],
        },
        {
            "ad_content": "Make $5000/week from home! No skills needed. WhatsApp +1-555-SCAM to join our exclusive money-making system. 100% guaranteed results!",
            "severity": "high",
            "correct_action": "reject",
            "category": "spam",
            "flags": ["financial_fraud", "unrealistic_claims", "direct_contact_bypass"],
        },
        {
            "ad_content": "URGENT: Your account has been compromised. Verify immediately at secure-login-meta.tk or lose all data!",
            "severity": "critical",
            "correct_action": "reject",
            "category": "spam",
            "flags": ["phishing", "impersonation", "urgency_language"],
        },
    ],
    "hate_speech_detection": [
        {
            "ad_content": "Buy our products — made by REAL [nationality] people, not those [slur] who steal our jobs. Support your own kind!",
            "severity": "critical",
            "correct_action": "reject",
            "category": "hate_speech",
            "flags": ["ethnic_slur", "xenophobia", "dehumanization"],
        },
        {
            "ad_content": "Our gym is for REAL men only. [gender slur]s not welcome. Join the brotherhood — no weaklings allowed.",
            "severity": "high",
            "correct_action": "reject",
            "category": "hate_speech",
            "flags": ["gender_discrimination", "exclusionary_language"],
        },
        {
            "ad_content": "Tired of [religion] taking over your neighborhood? Our community group fights back. Join 50,000 patriots today.",
            "severity": "critical",
            "correct_action": "reject",
            "category": "hate_speech",
            "flags": ["religious_discrimination", "incitement"],
        },
    ],
    "misinformation_detection": [
        {
            "ad_content": "DOCTORS HATE HIM! This one weird trick CURES cancer in 3 days using lemon juice and baking soda. Big Pharma doesn't want you to know!",
            "severity": "critical",
            "correct_action": "reject",
            "category": "misinformation",
            "flags": ["health_misinformation", "conspiracy_language", "false_medical_claim"],
        },
        {
            "ad_content": "COVID vaccines contain microchips that track your location. Our anti-5G pendant blocks the signal and restores your freedom. Only $99!",
            "severity": "critical",
            "correct_action": "reject",
            "category": "misinformation",
            "flags": ["vaccine_misinformation", "conspiracy", "pseudoscience_product"],
        },
        {
            "ad_content": "BREAKING: Scientists CONFIRM the Earth is flat. NASA has been lying for 60 years. Buy our truth-revealing documentary — $19.99.",
            "severity": "high",
            "correct_action": "reject",
            "category": "misinformation",
            "flags": ["scientific_misinformation", "conspiracy"],
        },
    ],
    "safe_content": [
        {
            "ad_content": "Introducing Nike Air Max 2025 — engineered for peak performance. Available in 12 colors. Free shipping on orders over $75. Shop at nike.com.",
            "severity": "low",
            "correct_action": "approve",
            "category": "safe",
            "flags": [],
        },
        {
            "ad_content": "Learn Python in 30 days with our structured online course. Taught by Google engineers. Certificate included. Enroll at coursera.org — 50% off this week.",
            "severity": "low",
            "correct_action": "approve",
            "category": "safe",
            "flags": [],
        },
        {
            "ad_content": "Freshly roasted single-origin coffee, delivered to your door within 48 hours of roasting. Try our Ethiopia Yirgacheffe — rated 94 by SCA. First bag free.",
            "severity": "low",
            "correct_action": "approve",
            "category": "safe",
            "flags": [],
        },
    ],
    "multi_violation_detection": [
        {
            "ad_content": "🔥 ONLY [ethnic group] LOSERS buy from mainstream stores! Our products are for REAL patriots. Limited offer — cure your chronic pain INSTANTLY with our hemp oil. Doctors BANNED this!",
            "severity": "critical",
            "correct_action": "reject",
            "category": "multi_violation",
            "flags": ["hate_speech", "health_misinformation", "urgency_language"],
        },
        {
            "ad_content": "WIN $10,000 FREE! Scientists say this supplement reverses aging by 20 years — Big Pharma banned in 12 countries. Click the secret link to order NOW before they remove this ad!",
            "severity": "critical",
            "correct_action": "reject",
            "category": "multi_violation",
            "flags": ["spam", "health_misinformation", "financial_fraud", "urgency_language"],
        },
    ],
}

MAX_STEPS = 3


def _build_obs_text(ad: Dict, step: int, task_id: str) -> str:
    flags_str = ", ".join(ad.get("flags", [])) or "none detected"
    return (
        f"=== AD MODERATION TASK: {task_id.upper().replace('_', ' ')} ===\n"
        f"Step: {step}/{MAX_STEPS}\n\n"
        f"Ad Content:\n{ad['ad_content']}\n\n"
        f"Severity Level: {ad['severity'].upper()}\n"
        f"Category: {ad.get('category', 'unknown')}\n"
        f"Auto-Detected Flags: {flags_str}\n\n"
        f"Make your moderation decision: APPROVE, REJECT, or FLAG"
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Ad Integrity OpenEnv", version="2.0.0")

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "2.0.0"}

    @app.post("/reset")
    def reset(body: Optional[BaseModel] = None):
        # Accept task_id from body or default to spam_detection
        task_id = "spam_detection"
        if hasattr(body, "__dict__"):
            raw = body.__dict__
            task_id = raw.get("task_id", task_id)

        # Parse raw JSON if body is a dict
        if task_id not in AD_BANK:
            task_id = "spam_detection"

        ads     = AD_BANK[task_id]
        ad      = random.choice(ads)
        obs_text = _build_obs_text(ad, step=1, task_id=task_id)

        _state.clear()
        _state.update({
            "task_id":        task_id,
            "step":           1,
            "max_steps":      MAX_STEPS,
            "history":        [],
            "done":           False,
            "current_ad":     ad,
            "rewards":        [],
        })

        return {
            "observation": {
                "text":        obs_text,
                "task_id":     task_id,
                "ad_content":  ad["ad_content"],
                "severity":    ad["severity"],
                "category":    ad.get("category"),
                "flags":       ad.get("flags", []),
            },
            "reward": 0.0,
            "done":   False,
            "info":   {"task_id": task_id},
        }

    @app.post("/step")
    def step(body: dict):
        if not _state:
            raise HTTPException(status_code=400, detail="Call /reset first")

        action = (body.get("action") or "").lower().strip()
        if action not in ("approve", "reject", "flag"):
            action = "reject"

        ad             = _state["current_ad"]
        correct_action = ad["correct_action"]
        severity       = ad["severity"]
        step_num       = _state["step"]

        reward = grade_action(
            agent_action=action,
            correct_action=correct_action,
            severity=severity,
            step=step_num,
            max_steps=MAX_STEPS,
        )

        _state["history"].append(f"step={step_num} action={action} correct={correct_action} reward={reward:.2f}")
        _state["rewards"].append(reward)
        _state["step"] += 1

        done = (_state["step"] > MAX_STEPS) or (action == correct_action)
        _state["done"] = done

        # Pick next ad if continuing
        if not done:
            ads = AD_BANK[_state["task_id"]]
            ad  = random.choice(ads)
            _state["current_ad"] = ad
        else:
            ad = _state["current_ad"]

        obs_text = _build_obs_text(ad, step=_state["step"], task_id=_state["task_id"])

        return {
            "observation": {
                "text":       obs_text,
                "task_id":    _state["task_id"],
                "ad_content": ad["ad_content"],
                "severity":   ad["severity"],
                "category":   ad.get("category"),
                "flags":      ad.get("flags", []),
            },
            "reward": reward,
            "done":   done,
            "info": {
                "correct_action": correct_action,
                "agent_action":   action,
                "step":           step_num,
            },
        }

    @app.post("/state")
    def state():
        if not _state:
            return {"task_id": "none", "step": 0, "max_steps": MAX_STEPS, "history": [], "done": True}
        return {
            "task_id":   _state["task_id"],
            "step":      _state["step"],
            "max_steps": _state["max_steps"],
            "history":   _state["history"],
            "done":      _state["done"],
        }

    @app.get("/tasks")
    def list_tasks():
        return {"tasks": list(AD_BANK.keys())}

    return app


app = create_app()

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
