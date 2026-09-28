from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from skillhub_selfhost.auth.router import router as auth_router
from skillhub_selfhost.admin.router import router as admin_router
from skillhub_selfhost.skills.router import router as skills_router


def create_app() -> FastAPI:
    app = FastAPI(title="skillhub")
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(skills_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    dist_path = Path(__file__).parent / "dist"
    if dist_path.exists() and (dist_path / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=str(dist_path / "assets")))

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            index = dist_path / "index.html"
            if index.exists():
                return FileResponse(index)
            return {"detail": "Not Found"}

    return app