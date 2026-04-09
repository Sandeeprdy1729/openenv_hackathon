try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with 'uv sync'"
    ) from e

try:
    from ..models import AdModerationAction, AdModerationObservation
    from .ad_moderation_environment import AdModerationEnvironment
except (ModuleNotFoundError, ImportError):
    from models import AdModerationAction, AdModerationObservation
    from server.ad_moderation_environment import AdModerationEnvironment


app = create_app(
    AdModerationEnvironment,
    AdModerationAction,
    AdModerationObservation,
    env_name="ad_moderation",
    max_concurrent_envs=10,
)


def main():
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
