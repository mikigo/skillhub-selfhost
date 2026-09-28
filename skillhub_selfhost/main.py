from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from skillhub_selfhost.auth.router import router as auth_router


def create_app() -> FastAPI:
    app = FastAPI(title="skillhub")
    app.include_router(auth_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    dist_path = Path(__file__).parent / "dist"
    if dist_path.exists() and (dist_path / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(dist_path), html=True))

    return app