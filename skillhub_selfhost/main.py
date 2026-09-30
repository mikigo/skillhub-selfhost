from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from skillhub_selfhost.auth.router import router as auth_router
from skillhub_selfhost.admin.router import router as admin_router
from skillhub_selfhost.skills.router import router as skills_router
from skillhub_selfhost.config import Config


def create_app() -> FastAPI:
    app = FastAPI(title="skillhub")
    config = Config()
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(skills_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/config")
    async def get_config():
        return JSONResponse({"logo_text": config.logo_text, "logo": config.logo, "default_lang": config.default_lang})

    @app.get("/api/config/logo")
    async def get_logo():
        if not config.logo:
            return JSONResponse({"detail": "No logo configured"}, status_code=404)
        logo_path = config.base_dir / config.logo
        if logo_path.is_file():
            return FileResponse(logo_path)
        return JSONResponse({"detail": "Logo file not found"}, status_code=404)

    @app.get("/favicon.ico")
    async def favicon():
        if config.favicon:
            fav_path = config.base_dir / config.favicon
            if fav_path.is_file():
                return FileResponse(fav_path)
        fav_default = Path(__file__).parent / "dist" / "favicon.ico"
        if fav_default.is_file():
            return FileResponse(fav_default)
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    dist_path = Path(__file__).parent / "dist"
    if dist_path.exists() and (dist_path / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=str(dist_path / "assets")))

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            # 没匹配上的 /api/* 不能落到 SPA 兜底上：否则会返回 200 + HTML，
            # 调用方要等到解析 JSON 才发现不对（旧地址 /api/skills/{name} 就是这种）
            if full_path == "api" or full_path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            index = dist_path / "index.html"
            if index.exists():
                return FileResponse(index)
            return {"detail": "Not Found"}

    return app