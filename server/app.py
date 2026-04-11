"""
server/app.py — FastAPI server for the MetaGuard OpenEnv environment.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional

from server.ad_moderation_environment import AdModerationEnvironment


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class ResetRequest(BaseModel):
    task_id: Optional[str] = "spam_detection"

class StepRequest(BaseModel):
    action: str

class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str


# ---------------------------------------------------------------------------
# App factory (used by openenv validate)
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="MetaGuard — Ad Moderation OpenEnv",
        description="OpenEnv-compliant RL environment for ad content moderation benchmarking.",
        version="2.0.0",
    )

    env = AdModerationEnvironment()

    @app.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(
            status="ok",
            environment="ad_integrity",
            version="2.0.0",
        )

    @app.get("/tasks")
    async def list_tasks():
        from tasks.definitions import ALL_TASKS
        return {
            "tasks": [
                {
                    "task_id": t.task_id,
                    "description": t.description,
                    "difficulty": t.difficulty,
                    "num_cases": len(t.cases),
                }
                for t in ALL_TASKS.values()
            ]
        }

    @app.post("/reset")
    async def reset(req: ResetRequest):
        try:
            obs = env.reset(req.task_id or "spam_detection")
            return {"observation": obs, "task_id": req.task_id}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/step")
    async def step(req: StepRequest):
        try:
            result = env.step(req.action)
            return result
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/state")
    @app.post("/state")
    async def state():
        return env.get_state()

    return app


app = create_app()


# ---------------------------------------------------------------------------
# Entry point (required by openenv validate)
# ---------------------------------------------------------------------------

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()