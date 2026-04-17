"""
env_loader.py - loads .env for local dev; on Vercel the env vars are already
injected by the platform, so the file loader is simply skipped silently.
"""

import os
from pathlib import Path


def load_env_file(env_path: str | Path | None = None) -> None:
    """
    Try to load a .env file when running locally.
    On Vercel (or any host that pre-injects env vars) the file won't exist,
    which is fine: we skip it silently so the app still starts correctly.
    """
    if env_path is None:
        env_path = Path(__file__).resolve().parent / ".env"

    env_path = Path(env_path)
    if not env_path.exists():
        return

    with env_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value
