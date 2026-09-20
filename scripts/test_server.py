"""Disposable local demo with deterministic AI. Run with backend/.venv/bin/python."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


async def fake_detection(content, created_at):
    from fastapi import HTTPException
    from app.services.ai import TaskDetection

    print("[TEST AI] provider attempt", flush=True)
    if content.startswith("[quota]"):
        raise HTTPException(503, detail={"code": "AI_PROVIDER_RATE_LIMITED", "retryable": False})
    if content.startswith("[error]"):
        raise HTTPException(503, detail={"code": "AI_UNAVAILABLE", "retryable": False})
    if content.startswith("[task]"):
        return TaskDetection(is_task=True, task_name=content.removeprefix("[task]").strip() or "Test chore")
    return TaskDetection(is_task=False)


def main():
    # Build against this server's origin, ignoring stale frontend .env tunnel URLs.
    subprocess.run(["npm", "run", "build"], cwd=ROOT / "frontend",
                   env={**os.environ, "VITE_API_URL": "", "VITE_WS_URL": ""}, check=True)
    with tempfile.TemporaryDirectory(prefix="liferoom-local-test-") as directory:
        os.environ.update(
            DATABASE_URL=f"sqlite:///{directory}/test.db",
            ENVIRONMENT="testing",
            APP_NAME="LifeRoom LOCAL TEST — simulated AI",
            GEMINI_API_KEY="",
            GEMINI_MODEL="",
            CORS_ORIGINS=",".join(filter(None, ["http://127.0.0.1:8002", "http://localhost:8002", os.environ.get("TEST_PUBLIC_ORIGIN")])),
        )
        sys.path.insert(0, str(ROOT / "backend"))
        from app.services import ai
        from app.main import app
        import uvicorn

        ai.detect_task = fake_detection
        print("LOCAL TEST: http://127.0.0.1:8002 — simulated AI, temporary DB", flush=True)
        print("Messages: [task] Do dishes | [quota] test | [error] test | ㅋㅋㅋ", flush=True)
        uvicorn.run(app, host="127.0.0.1", port=8002, workers=1)


if __name__ == "__main__":
    main()
