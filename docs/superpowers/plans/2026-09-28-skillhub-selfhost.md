# skillhub-selfhost 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个面向小团队内网部署的 AI 技能市场平台 —— pip install 一键部署，React 前端 + FastAPI 后端，默认 SQLite。

**Architecture:** FastAPI 后端通过 `importlib.resources` serve 前端 dist，Tortoise ORM 管理 SQLite，CLI 通过 typer。前端 React + react-router-dom v7 + shadcn/ui，React Context 管理认证状态。

**Tech Stack:** FastAPI, Tortoise ORM, SQLite, typer, Python 3.10+, React 18, Vite, react-router-dom v7, shadcn/ui, Tailwind CSS, bcrypt, PyJWT.

---

## 文件结构

```
skillhub-selfhost/
├── pyproject.toml
├── skillhub_selfhost/
│   ├── __init__.py              # 空
│   ├── main.py                  # FastAPI app 创建 + SPA fallback
│   ├── cli.py                   # typer CLI（admin-init, server start）
│   ├── config.py                # 配置读取
│   ├── db.py                    # Tortoise ORM 初始化
│   ├── logging_config.py        # 日志配置
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── models.py            # User model
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── service.py           # 业务逻辑
│   │   ├── router.py            # API 路由
│   │   └── dependencies.py      # Depends
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── models.py            # Skill + SkillVersion + DownloadLog
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── service.py           # 业务逻辑
│   │   └── router.py            # API 路由
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── schemas.py           # Pydantic schemas
│   │   └── router.py            # 管理员 API
│   └── dist/                    # 前端构建产物（CI 自动产出，开发阶段先放占位）
│       └── .gitkeep
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── contexts/
│       │   └── AuthContext.tsx
│       ├── api/
│       │   └── client.ts
│       ├── pages/
│       │   ├── Home.tsx
│       │   ├── Login.tsx
│       │   ├── Register.tsx
│       │   ├── SkillDetail.tsx
│       │   ├── Upload.tsx
│       │   ├── MySkills.tsx
│       │   └── Admin.tsx
│       └── components/
│           ├── Layout.tsx
│           └── ui/              # shadcn/ui components
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_auth_service.py
    ├── test_auth_router.py
    ├── test_skills_service.py
    ├── test_skills_router.py
    └── test_admin_router.py
```

---

### Task 1: 项目脚手架

**Files:**
- Create: `pyproject.toml`
- Create: `skillhub_selfhost/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "skillhub-selfhost"
version = "0.1.0"
description = "A self-hosted AI skill marketplace"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "tortoise-orm[asyncpg]>=0.20.0",
    "aiosqlite>=0.20.0",
    "python-multipart>=0.0.9",
    "bcrypt>=4.1.0",
    "PyJWT>=2.8.0",
    "typer>=0.12.0",
    "aiofiles>=23.2.0",
]
license = {text = "Apache-2.0"}

[project.scripts]
skillhub-selfhost = "skillhub_selfhost.cli:app"

[tool.setuptools.packages.find]
include = ["skillhub_selfhost*"]

[tool.setuptools.package-data]
skillhub_selfhost = ["dist/**"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: 创建空文件**

`skillhub_selfhost/__init__.py` 和 `tests/__init__.py` 空文件。

- [ ] **Step 3: 创建测试 fixture**

```python
# tests/conftest.py
import pytest
from tortoise.contrib.test import initializer, finalizer

@pytest.fixture(autouse=True)
def setup_db():
    initializer(
        ["skillhub_selfhost.auth.models", "skillhub_selfhost.skills.models"],
        db_url="sqlite://:memory:",
    )
    yield
    finalizer()
```

- [ ] **Step 4: 安装依赖**

```bash
pip install -e ".[dev]"
```

- [ ] **Step 5: 运行 pytest 确认框架就绪**

```bash
pytest -v
```
Expected: 0 tests collected（尚无测试，但 pytest 正常运行）

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml skillhub_selfhost/ tests/
git commit -m "chore: project scaffolding with pyproject.toml and test framework"
```

---

### Task 2: 配置模块

**Files:**
- Create: `skillhub_selfhost/config.py`

- [ ] **Step 1: 实现配置模块**

```python
# skillhub_selfhost/config.py
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Config:
    base_dir: Path = field(default_factory=lambda: Path.cwd())
    host: str = "0.0.0.0"
    port: int = 8000
    db_url: str = ""
    secret_key: str = ""
    skills_dir: Path | None = None
    log_level: str = "INFO"

    def __post_init__(self):
        if not self.db_url:
            self.db_url = f"sqlite://{self.base_dir / 'metadata.db'}"
        if not self.secret_key:
            self.secret_key = self._load_or_generate_secret()
        if self.skills_dir is None:
            self.skills_dir = self.base_dir / "skills"

    def _load_or_generate_secret(self) -> str:
        secret_file = self.base_dir / ".secret"
        if secret_file.exists():
            return secret_file.read_text().strip()
        key = secrets.token_urlsafe(32)
        secret_file.write_text(key)
        return key

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            host=os.getenv("SKILLHUB_HOST", "0.0.0.0"),
            port=int(os.getenv("SKILLHUB_PORT", "8000")),
            db_url=os.getenv("SKILLHUB_DB_URL", ""),
            secret_key=os.getenv("SKILLHUB_SECRET_KEY", ""),
            skills_dir=Path(os.getenv("SKILLHUB_SKILLS_DIR")) if os.getenv("SKILLHUB_SKILLS_DIR") else None,
            log_level=os.getenv("SKILLHUB_LOG_LEVEL", "INFO"),
        )
```

- [ ] **Step 2: Commit**

```bash
git add skillhub_selfhost/config.py
git commit -m "feat: add config module"
```

---

### Task 3: 数据库初始化

**Files:**
- Create: `skillhub_selfhost/db.py`

- [ ] **Step 1: 实现数据库初始化**

```python
# skillhub_selfhost/db.py
from tortoise import Tortoise

async def init_db(db_url: str):
    await Tortoise.init(
        db_url=db_url,
        modules={
            "models": [
                "skillhub_selfhost.auth.models",
                "skillhub_selfhost.skills.models",
            ]
        },
    )
    await Tortoise.generate_schemas()

async def close_db():
    await Tortoise.close_connections()
```

- [ ] **Step 2: Commit**

```bash
git add skillhub_selfhost/db.py
git commit -m "feat: add database initialization module"
```

---

### Task 4: 日志配置

**Files:**
- Create: `skillhub_selfhost/logging_config.py`

- [ ] **Step 1: 实现日志配置**

```python
# skillhub_selfhost/logging_config.py
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

def setup_logging(base_dir: Path, level: str = "INFO"):
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    handler = TimedRotatingFileHandler(
        filename=logs_dir / "skillhub.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    handler.suffix = "%Y-%m-%d"
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    ))

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=[handler, console],
    )
```

- [ ] **Step 2: Commit**

```bash
git add skillhub_selfhost/logging_config.py
git commit -m "feat: add logging configuration with daily rotation"
```

---

### Task 5: CLI 命令

**Files:**
- Create: `skillhub_selfhost/cli.py`

- [ ] **Step 1: 实现 CLI**

```python
# skillhub_selfhost/cli.py
import typer
from pathlib import Path

app = typer.Typer()

@app.command()
def admin_init():
    """交互式创建管理员用户"""
    from skillhub_selfhost.config import Config
    from skillhub_selfhost.db import init_db, close_db
    from skillhub_selfhost.auth.service import register_user
    import asyncio

    config = Config()
    asyncio.run(init_db(config.db_url))

    username = typer.prompt("管理员用户名")
    password = typer.prompt("管理员密码", hide_input=True)

    asyncio.run(register_user(username, password, is_admin=True, status="active"))
    asyncio.run(close_db())
    typer.echo(f"管理员 {username} 创建成功")

@app.command()
def server_start(
    host: str = typer.Option("0.0.0.0", help="监听地址"),
    port: int = typer.Option(8000, help="监听端口"),
):
    """启动 skillhub 服务"""
    import uvicorn
    import asyncio
    from skillhub_selfhost.config import Config
    from skillhub_selfhost.db import init_db
    from skillhub_selfhost.logging_config import setup_logging

    config = Config(host=host, port=port)
    setup_logging(config.base_dir, config.log_level)

    config.skills_dir.mkdir(parents=True, exist_ok=True)
    asyncio.run(init_db(config.db_url))

    typer.echo(f"skillhub 启动: http://{host}:{port}")
    uvicorn.run(
        "skillhub_selfhost.main:create_app",
        factory=True,
        host=host,
        port=port,
        log_config=None,
    )

if __name__ == "__main__":
    app()
```

- [ ] **Step 2: 创建 main.py 入口**

```python
# skillhub_selfhost/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

def create_app() -> FastAPI:
    app = FastAPI(title="skillhub")

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    # Serve frontend SPA
    import importlib.resources
    dist_path = Path(__file__).parent / "dist"
    if dist_path.exists():
        app.mount("/", StaticFiles(directory=str(dist_path), html=True))

    return app
```

- [ ] **Step 3: 验证 CLI 可执行**

```bash
pip install -e .
skillhub-selfhost --help
skillhub-selfhost server start --help
skillhub-selfhost admin-init --help
```

- [ ] **Step 4: 验证 server start 可启动**

```bash
skillhub-selfhost server start --port 8000
# Ctrl+C 停止，确认无报错
```

- [ ] **Step 5: Commit**

```bash
git add skillhub_selfhost/cli.py skillhub_selfhost/main.py
git commit -m "feat: add CLI with admin-init and server start commands"
```

---

### Task 6: User 模型

**Files:**
- Create: `skillhub_selfhost/auth/__init__.py`
- Create: `skillhub_selfhost/auth/models.py`

- [ ] **Step 1: 实现 User 模型**

```python
# skillhub_selfhost/auth/models.py
from tortoise.models import Model
from tortoise import fields

class User(Model):
    id = fields.UUIDField(pk=True)
    username = fields.CharField(max_length=64, unique=True, index=True)
    password_hash = fields.CharField(max_length=256)
    status = fields.CharField(max_length=16, default="pending")
    is_admin = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"
```

- [ ] **Step 2: 创建 Pydantic schemas**

```python
# skillhub_selfhost/auth/schemas.py
from pydantic import BaseModel, Field
from datetime import datetime

class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str

class RefreshRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: str
    username: str
    status: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Commit**

```bash
git add skillhub_selfhost/auth/
git commit -m "feat: add User model and auth schemas"
```

---

### Task 7: Auth Service

**Files:**
- Create: `skillhub_selfhost/auth/service.py`
- Online Create: `tests/test_auth_service.py`

- [ ] **Step 1: 编写测试**

```python
# tests/test_auth_service.py
import pytest
from skillhub_selfhost.auth.service import register_user, login, refresh_token, get_user_by_id
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.config import Config

@pytest.fixture
def config():
    return Config()

@pytest.mark.asyncio
async def test_register_user(config):
    user = await register_user("alice", "password123")
    assert user.username == "alice"
    assert user.status == "pending"
    assert user.is_admin is False
    assert len(user.password_hash) > 0

@pytest.mark.asyncio
async def test_register_duplicate_username(config):
    await register_user("bob", "pass1")
    with pytest.raises(ValueError, match="用户名已存在"):
        await register_user("bob", "pass2")

@pytest.mark.asyncio
async def test_login_success(config):
    await register_user("carol", "password123", status="active")
    tokens = await login("carol", "password123", config.secret_key)
    assert "access_token" in tokens
    assert "refresh_token" in tokens

@pytest.mark.asyncio
async def test_login_pending_user(config):
    await register_user("dave", "password123", status="pending")
    with pytest.raises(ValueError, match="账号尚未通过审批"):
        await login("dave", "password123", config.secret_key)

@pytest.mark.asyncio
async def test_login_disabled_user(config):
    await register_user("eve", "password123", status="disabled")
    with pytest.raises(ValueError, match="账号已被禁用"):
        await login("eve", "password123", config.secret_key)

@pytest.mark.asyncio
async def test_login_wrong_password(config):
    await register_user("frank", "password123", status="active")
    with pytest.raises(ValueError, match="用户名或密码错误"):
        await login("frank", "wrongpass", config.secret_key)

@pytest.mark.asyncio
async def test_refresh_token(config):
    await register_user("grace", "password123", status="active")
    tokens = await login("grace", "password123", config.secret_key)
    new_tokens = await refresh_token(tokens["refresh_token"], config.secret_key)
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["access_token"] != tokens["access_token"]
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_auth_service.py -v
```
Expected: ALL FAIL (service 尚未实现)

- [ ] **Step 3: 实现 Auth Service**

```python
# skillhub_selfhost/auth/service.py
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from skillhub_selfhost.auth.models import User

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

def create_token(data: dict, secret: str, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret, algorithm="HS256")

def decode_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=["HS256"])

async def register_user(username: str, password: str, is_admin: bool = False, status: str = "pending") -> User:
    existing = await User.filter(username=username).first()
    if existing:
        raise ValueError("用户名已存在")
    user = await User.create(
        username=username,
        password_hash=hash_password(password),
        is_admin=is_admin,
        status=status,
    )
    return user

async def login(username: str, password: str, secret: str) -> dict:
    user = await User.filter(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("用户名或密码错误")
    if user.status == "pending":
        raise ValueError("账号尚未通过审批，请联系管理员")
    if user.status == "disabled":
        raise ValueError("账号已被禁用")

    access_token = create_token(
        {"sub": str(user.id), "username": user.username},
        secret,
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_token(
        {"sub": str(user.id), "type": "refresh"},
        secret,
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return {"access_token": access_token, "refresh_token": refresh_token}

async def refresh_token(token: str, secret: str) -> dict:
    try:
        payload = decode_token(token, secret)
        if payload.get("type") != "refresh":
            raise ValueError()
        user_id = payload.get("sub")
        user = await User.filter(id=user_id).first()
        if not user:
            raise ValueError()
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError):
        raise ValueError("无效的 refresh token")

    access_token = create_token(
        {"sub": str(user.id), "username": user.username},
        secret,
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh_token = create_token(
        {"sub": str(user.id), "type": "refresh"},
        secret,
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return {"access_token": access_token, "refresh_token": new_refresh_token}

async def get_user_by_id(user_id: str) -> User | None:
    return await User.filter(id=user_id).first()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_auth_service.py -v
```
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add skillhub_selfhost/auth/service.py tests/
git commit -m "feat: add auth service with register, login, and token refresh"
```

---

### Task 8: Auth Dependencies

**Files:**
- Create: `skillhub_selfhost/auth/dependencies.py`

- [ ] **Step 1: 实现认证依赖**

```python
# skillhub_selfhost/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from skillhub_selfhost.auth.service import decode_token, get_user_by_id
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.config import Config

security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User | None:
    if credentials is None:
        return None
    config = Config()
    try:
        payload = decode_token(credentials.credentials, config.secret_key)
        if payload.get("type") == "refresh":
            return None
        user_id = payload.get("sub")
        user = await get_user_by_id(user_id)
        return user
    except Exception:
        return None

async def require_user(
    user: User | None = Depends(get_current_user),
) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    return user

async def require_admin(
    user: User = Depends(require_user),
) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user
```

- [ ] **Step 2: Commit**

```bash
git add skillhub_selfhost/auth/dependencies.py
git commit -m "feat: add auth dependencies for route protection"
```

---

### Task 9: Auth Router

**Files:**
- Create: `skillhub_selfhost/auth/router.py`
- Online Create: `tests/test_auth_router.py`

- [ ] **Step 1: 编写路由测试**

```python
# tests/test_auth_router.py
import pytest
from httpx import ASGITransport, AsyncClient
from skillhub_selfhost.main import create_app
from skillhub_selfhost.auth.service import register_user

@pytest.fixture
def app():
    return create_app()

@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_register(client):
    resp = await client.post("/api/auth/register", json={"username": "newuser", "password": "pass123"})
    assert resp.status_code == 204

@pytest.mark.asyncio
async def test_register_duplicate(client):
    await register_user("dup", "pass1")
    resp = await client.post("/api/auth/register", json={"username": "dup", "password": "pass2"})
    assert resp.status_code == 409

@pytest.mark.asyncio
async def test_login_success(client):
    await register_user("loginuser", "pass123", status="active")
    resp = await client.post("/api/auth/login", json={"username": "loginuser", "password": "pass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data

@pytest.mark.asyncio
async def test_login_pending(client):
    await register_user("pend", "pass123", status="pending")
    resp = await client.post("/api/auth/login", json={"username": "pend", "password": "pass123"})
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_me_unauthorized(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_me_authorized(client):
    user = await register_user("meuser", "pass123", status="active")
    tokens_resp = await client.post("/api/auth/login", json={"username": "meuser", "password": "pass123"})
    token = tokens_resp.json()["access_token"]
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "meuser"

@pytest.mark.asyncio
async def test_refresh(client):
    await register_user("refuser", "pass123", status="active")
    tokens = await client.post("/api/auth/login", json={"username": "refuser", "password": "pass123"})
    refresh = tokens.json()["refresh_token"]
    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["access_token"] != tokens.json()["access_token"]
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_auth_router.py -v
```
Expected: ALL FAIL

- [ ] **Step 3: 实现 Auth Router**

```python
# skillhub_selfhost/auth/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from skillhub_selfhost.auth.schemas import RegisterRequest, LoginRequest, RefreshRequest, TokenResponse, UserResponse
from skillhub_selfhost.auth.service import register_user, login, refresh_token, get_user_by_id
from skillhub_selfhost.auth.dependencies import require_user
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.config import Config

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", status_code=204)
async def register(body: RegisterRequest):
    try:
        await register_user(body.username, body.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/login", response_model=TokenResponse)
async def login_route(body: LoginRequest):
    config = Config()
    try:
        return await login(body.username, body.password, config.secret_key)
    except ValueError as e:
        status_code = 403 if "审批" in str(e) or "禁用" in str(e) else 401
        raise HTTPException(status_code=status_code, detail=str(e))

@router.post("/refresh", response_model=TokenResponse)
async def refresh_route(body: RefreshRequest):
    config = Config()
    try:
        return await refresh_token(body.refresh_token, config.secret_key)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(require_user)):
    return user
```

- [ ] **Step 4: 更新 main.py 注册路由**

```python
# skillhub_selfhost/main.py 中 create_app 函数添加:
from skillhub_selfhost.auth.router import router as auth_router
app.include_router(auth_router)
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_auth_router.py -v
```
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add skillhub_selfhost/auth/router.py skillhub_selfhost/main.py tests/test_auth_router.py
git commit -m "feat: add auth API routes"
```

---

### Task 10: Skill 模型

**Files:**
- Create: `skillhub_selfhost/skills/__init__.py`
- Create: `skillhub_selfhost/skills/models.py`

- [ ] **Step 1: 实现 Skill + SkillVersion + DownloadLog 模型**

```python
# skillhub_selfhost/skills/models.py
from tortoise.models import Model
from tortoise import fields

class Skill(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=128, unique=True, index=True)
    display_name = fields.CharField(max_length=256)
    description = fields.TextField()
    tags = fields.JSONField(default=[])
    author = fields.ForeignKeyField("models.User", related_name="skills")
    download_count = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "skills"

class SkillVersion(Model):
    id = fields.UUIDField(pk=True)
    skill = fields.ForeignKeyField("models.Skill", related_name="versions")
    version = fields.CharField(max_length=32)
    release_notes = fields.TextField(null=True)
    file_size = fields.IntField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "skill_versions"
        unique_together = ("skill_id", "version")

class DownloadLog(Model):
    id = fields.UUIDField(pk=True)
    skill = fields.ForeignKeyField("models.Skill", related_name="download_logs")
    version = fields.CharField(max_length=32)
    downloaded_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "download_logs"
```

- [ ] **Step 2: 创建 Skill Pydantic schemas**

```python
# skillhub_selfhost/skills/schemas.py
from pydantic import BaseModel
from datetime import datetime

class AuthorInfo(BaseModel):
    username: str
    status: str

class SkillListItem(BaseModel):
    name: str
    display_name: str
    description: str
    author: AuthorInfo
    latest_version: str
    tags: list[str]
    download_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class SkillVersionItem(BaseModel):
    version: str
    release_notes: str | None
    file_size: int
    created_at: datetime

    model_config = {"from_attributes": True}

class SkillDetailResponse(BaseModel):
    name: str
    display_name: str
    description: str
    author: AuthorInfo
    tags: list[str]
    download_count: int
    created_at: datetime
    updated_at: datetime
    versions: list[SkillVersionItem]

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    size: int

class TransferRequest(BaseModel):
    target_user: str
```

- [ ] **Step 3: Commit**

```bash
git add skillhub_selfhost/skills/
git commit -m "feat: add Skill, SkillVersion, DownloadLog models and schemas"
```

---

### Task 11: Skill Service —— 上传

**Files:**
- Create: `skillhub_selfhost/skills/service.py`
- Create: `tests/test_skills_service.py`

- [ ] **Step 1: 编写上传测试**

```python
# tests/test_skills_service.py
import io
import tarfile
import pytest
from skillhub_selfhost.skills.service import upload_skill
from skillhub_selfhost.skills.models import Skill, SkillVersion
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.config import Config

def make_tar(skill_name: str, has_skill_md: bool = True, extra_file: str | None = None) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        if has_skill_md:
            info = tarfile.TarInfo(name=f"{skill_name}/SKILL.md")
            info.size = 10
            tar.addfile(info, io.BytesIO(b"# Test"))
        if extra_file:
            info = tarfile.TarInfo(name=f"{skill_name}/{extra_file}")
            info.size = 5
            tar.addfile(info, io.BytesIO(b"hello"))
    return buf.getvalue()

@pytest.fixture
def config():
    return Config()

@pytest.fixture
async def user():
    return await User.create(username="uploader", password_hash="x", status="active")

@pytest.mark.asyncio
async def test_upload_new_skill(config, user):
    tar_bytes = make_tar("my-linter")
    skill = await upload_skill(
        file_content=tar_bytes,
        display_name="My Linter",
        description="A linter",
        tags=["python"],
        version="1.0.0",
        author=user,
        skills_dir=config.skills_dir,
    )
    assert skill.name == "my-linter"
    assert skill.display_name == "My Linter"
    assert skill.author_id == user.id
    versions = await SkillVersion.filter(skill=skill).all()
    assert len(versions) == 1
    assert versions[0].version == "1.0.0"

@pytest.mark.asyncio
async def test_upload_missing_skill_md(config, user):
    tar_bytes = make_tar("bad-skill", has_skill_md=False)
    with pytest.raises(ValueError, match="必须包含 SKILL.md"):
        await upload_skill(tar_bytes, "Bad", "desc", [], "1.0.0", user, config.skills_dir)

@pytest.mark.asyncio
async def test_upload_duplicate_version(config, user):
    tar_bytes = make_tar("dup-skill")
    await upload_skill(tar_bytes, "Dup", "desc", [], "1.0.0", user, config.skills_dir)
    with pytest.raises(ValueError, match="已存在"):
        await upload_skill(tar_bytes, "Dup2", "desc2", [], "1.0.0", user, config.skills_dir)

@pytest.mark.asyncio
async def test_upload_auto_version(config, user):
    tar_bytes = make_tar("auto-skill")
    await upload_skill(tar_bytes, "Auto", "desc", [], "1.0.0", user, config.skills_dir)
    skill2 = await upload_skill(tar_bytes, "Auto", "desc", [], "", user, config.skills_dir)
    versions = await SkillVersion.filter(skill__name="auto-skill").all()
    assert len(versions) == 2
    assert versions[1].version == "1.0.1"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_skills_service.py -v -k upload
```
Expected: FAIL

- [ ] **Step 3: 实现上传服务**

```python
# skillhub_selfhost/skills/service.py
import io
import tarfile
import re
import os
from pathlib import Path
from skillhub_selfhost.skills.models import Skill, SkillVersion
from skillhub_selfhost.auth.models import User

SKILL_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

def _extract_skill_name_from_tar(file_content: bytes) -> str:
    buf = io.BytesIO(file_content)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        for member in tar.getmembers():
            parts = member.name.split("/", 1)
            if len(parts) >= 2 and parts[1] == "SKILL.md":
                return parts[0]
    raise ValueError("tar.gz 内必须包含 SKILL.md，且文件需放在以 skill 名称命名的根目录下")

def _validate_skill_name(name: str):
    if not SKILL_NAME_RE.match(name) or len(name) > 128:
        raise ValueError("skill 名称不合法，需以字母或数字开头，仅含字母、数字、连字符、下划线、点号")

def _validate_version(version: str):
    if not SEMVER_RE.match(version):
        raise ValueError("版本号格式不正确，请使用 x.y.z 格式")

def _bump_patch(version: str) -> str:
    parts = version.split(".")
    return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"

async def upload_skill(
    file_content: bytes,
    display_name: str,
    description: str,
    tags: list[str],
    version: str,
    author: User,
    skills_dir: Path,
    release_notes: str | None = None,
) -> Skill:
    skill_name = _extract_skill_name_from_tar(file_content)
    _validate_skill_name(skill_name)

    existing = await Skill.filter(name=skill_name).prefetch_related("author").first()
    if existing and existing.author_id != author.id:
        raise ValueError("skill 名称已被占用")

    if not version:
        if existing:
            latest = await SkillVersion.filter(skill=existing).order_by("-created_at").first()
            version = _bump_patch(latest.version)
        else:
            version = "1.0.0"
    _validate_version(version)

    if existing:
        dup = await SkillVersion.filter(skill=existing, version=version).first()
        if dup:
            raise ValueError(f"版本 {version} 已存在")
    else:
        existing = await Skill.create(
            name=skill_name,
            display_name=display_name,
            description=description,
            tags=tags,
            author=author,
        )

    file_size = len(file_content)

    version_dir = skills_dir / author.username / skill_name / version
    version_dir.mkdir(parents=True, exist_ok=True)

    buf = io.BytesIO(file_content)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        for member in tar.getmembers():
            rel = member.name[len(skill_name) + 1:]
            if not rel or ".." in rel or rel.startswith("/"):
                continue
            target = version_dir / rel
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as src:
                    target.write_bytes(src.read())

    await SkillVersion.create(
        skill=existing,
        version=version,
        release_notes=release_notes,
        file_size=file_size,
    )

    existing.updated_at = SkillVersion._meta.fields_map["created_at"].default()  # keep auto_now
    await existing.save()
    return existing
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_skills_service.py -v -k upload
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skillhub_selfhost/skills/service.py tests/test_skills_service.py
git commit -m "feat: add skill upload service with validation"
```

---

### Task 12: Skill Service —— 列表/搜索/下载

**Files:**
- Modify: `skillhub_selfhost/skills/service.py`
- Modify: `tests/test_skills_service.py`

- [ ] **Step 1: 追加列表/搜索/下载测试**

```python
# 追加到 tests/test_skills_service.py

@pytest.mark.asyncio
async def test_list_skills(config, user):
    tar = make_tar("list-skill")
    await upload_skill(tar, "List Skill", "desc", ["python"], "1.0.0", user, config.skills_dir)
    items, total = await list_skills(page=1, size=20)
    assert total >= 1

@pytest.mark.asyncio
async def test_search_skills(config, user):
    tar = make_tar("search-skill")
    await upload_skill(tar, "Search Skill", "a unique desc word", ["go"], "1.0.0", user, config.skills_dir)
    items, total = await search_skills(q="unique desc")
    assert total >= 1

@pytest.mark.asyncio
async def test_filter_by_tag(config, user):
    tar1 = make_tar("tag-a")
    tar2 = make_tar("tag-b")
    await upload_skill(tar1, "Tag A", "desc", ["python", "linter"], "1.0.0", user, config.skills_dir)
    await upload_skill(tar2, "Tag B", "desc", ["python"], "1.0.0", user, config.skills_dir)
    items, _ = await search_skills(tags=["python", "linter"])
    assert len(items) >= 1
    for item in items:
        skills = await Skill.filter(name=item.name).first()
        assert skills and "python" in skills.tags and "linter" in skills.tags

@pytest.mark.asyncio
async def test_download_increments_count(config, user):
    tar = make_tar("dl-count")
    await upload_skill(tar, "DL Count", "desc", [], "1.0.0", user, config.skills_dir)
    path, filename, content = await download_skill("dl-count")
    skill = await Skill.filter(name="dl-count").first()
    assert skill.download_count == 1
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_skills_service.py -v -k "list or search or filter or download"
```
Expected: FAIL

- [ ] **Step 3: 实现列表/搜索/下载**

```python
# 追加到 skillhub_selfhost/skills/service.py
import io
from tortoise.expressions import Q
from datetime import datetime, timedelta, timezone

async def list_skills(page: int = 1, size: int = 20, sort: str = "downloads") -> tuple[list[dict], int]:
    qs = Skill.all().prefetch_related("author")
    if sort == "downloads":
        qs = qs.order_by("-download_count")
    elif sort == "weekly":
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        # 用子查询：按最近7天下载量排序
        from tortoise.expressions import RawSQL
        qs = qs.annotate(
            weekly_downloads=RawSQL(
                "SELECT COUNT(*) FROM download_logs WHERE download_logs.skill_id = skills.id AND download_logs.downloaded_at >= ?",
                [week_ago],
            )
        ).order_by("-weekly_downloads")
    elif sort == "newest":
        qs = qs.order_by("-created_at")

    total = await qs.count()
    skills = await qs.offset((page - 1) * size).limit(size).all()

    items = []
    for s in skills:
        latest = await SkillVersion.filter(skill=s).order_by("-created_at").first()
        items.append({
            "name": s.name,
            "display_name": s.display_name,
            "description": s.description,
            "author": {"username": s.author.username, "status": s.author.status},
            "latest_version": latest.version if latest else "",
            "tags": s.tags,
            "download_count": s.download_count,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        })
    return items, total

async def search_skills(q: str | None = None, tags: list[str] | None = None, author_username: str | None = None,
                        page: int = 1, size: int = 20, sort: str = "downloads") -> tuple[list[dict], int]:
    qs = Skill.all().prefetch_related("author")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(display_name__icontains=q) | Q(description__icontains=q))
    if tags:
        from tortoise.expressions import Q as TQ
        tag_q = TQ()
        for tag in tags:
            tag_q &= TQ(tags__contains=tag)
        qs = qs.filter(tag_q)
    if author_username:
        qs = qs.filter(author__username=author_username)

    if sort == "downloads":
        qs = qs.order_by("-download_count")
    elif sort == "newest":
        qs = qs.order_by("-created_at")

    total = await qs.count()
    skills = await qs.offset((page - 1) * size).limit(size).all()

    items = []
    for s in skills:
        latest = await SkillVersion.filter(skill=s).order_by("-created_at").first()
        items.append({
            "name": s.name,
            "display_name": s.display_name,
            "description": s.description,
            "author": {"username": s.author.username, "status": s.author.status},
            "latest_version": latest.version if latest else "",
            "tags": s.tags,
            "download_count": s.download_count,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        })
    return items, total

async def get_skill_detail(name: str) -> dict | None:
    skill = await Skill.filter(name=name).prefetch_related("author").first()
    if not skill:
        return None
    versions = await SkillVersion.filter(skill=skill).order_by("-created_at").all()
    return {
        "name": skill.name,
        "display_name": skill.display_name,
        "description": skill.description,
        "author": {"username": skill.author.username, "status": skill.author.status},
        "tags": skill.tags,
        "download_count": skill.download_count,
        "created_at": skill.created_at,
        "updated_at": skill.updated_at,
        "versions": [
            {"version": v.version, "release_notes": v.release_notes, "file_size": v.file_size, "created_at": v.created_at}
            for v in versions
        ],
    }

async def get_skill_readme(name: str, version: str | None = None, skills_dir: Path | None = None) -> str:
    skill = await Skill.filter(name=name).prefetch_related("author").first()
    if not skill:
        raise ValueError("skill 不存在")
    if not version:
        latest = await SkillVersion.filter(skill=skill).order_by("-created_at").first()
        version = latest.version
    if skills_dir is None:
        skills_dir = Path.cwd() / "skills"
    readme_path = skills_dir / skill.author.username / name / version / "SKILL.md"
    if not readme_path.exists():
        raise ValueError("SKILL.md 不存在")
    return readme_path.read_text(encoding="utf-8")

async def download_skill(name: str, version: str | None = None, skills_dir: Path | None = None) -> tuple[Path, str, bytes]:
    import io as io_mod
    skill = await Skill.filter(name=name).prefetch_related("author").first()
    if not skill:
        raise ValueError("skill 不存在")
    if not version:
        latest = await SkillVersion.filter(skill=skill).order_by("-created_at").first()
        version = latest.version
    if skills_dir is None:
        skills_dir = Path.cwd() / "skills"

    src_dir = skills_dir / skill.author.username / name / version
    if not src_dir.exists():
        raise ValueError("版本文件不存在")

    buf = io_mod.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(str(src_dir), arcname=name)

    skill.download_count += 1
    await skill.save()

    from skillhub_selfhost.skills.models import DownloadLog
    await DownloadLog.create(skill=skill, version=version)

    filename = f"{name}-v{version}.tar.gz"
    return src_dir, filename, buf.getvalue()

async def delete_skill(name: str, author: User):
    skill = await Skill.filter(name=name).prefetch_related("author").first()
    if not skill:
        raise ValueError("skill 不存在")
    if skill.author_id != author.id:
        raise ValueError("无权限删除此 skill")

    config = Config()
    skill_dir = config.skills_dir / author.username / name
    import shutil
    if skill_dir.exists():
        shutil.rmtree(skill_dir)
    await skill.delete()

async def delete_skill_version(name: str, version: str, author: User):
    skill = await Skill.filter(name=name).prefetch_related("author").first()
    if not skill:
        raise ValueError("skill 不存在")
    if skill.author_id != author.id:
        raise ValueError("无权限删除此版本")

    ver = await SkillVersion.filter(skill=skill, version=version).first()
    if not ver:
        raise ValueError("版本不存在")

    config = Config()
    version_dir = config.skills_dir / author.username / name / version
    import shutil
    if version_dir.exists():
        shutil.rmtree(version_dir)
    await ver.delete()

    remaining = await SkillVersion.filter(skill=skill).count()
    if remaining == 0:
        skill_dir = config.skills_dir / author.username / name
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
        await skill.delete()

async def transfer_skill(name: str, target_username: str, actor: User):
    skill = await Skill.filter(name=name).prefetch_related("author").first()
    if not skill:
        raise ValueError("skill 不存在")
    if skill.author_id != actor.id and not actor.is_admin:
        raise ValueError("无权限转移此 skill")

    target = await User.filter(username=target_username, status="active").first()
    if not target:
        raise ValueError(f"用户 {target_username} 不存在或未激活")

    config = Config()
    old_dir = config.skills_dir / skill.author.username / name
    new_dir = config.skills_dir / target_username
    new_dir.mkdir(parents=True, exist_ok=True)
    import shutil
    if old_dir.exists():
        shutil.move(str(old_dir), str(new_dir / name))

    skill.author_id = target.id
    await skill.save()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_skills_service.py -v
```
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add skillhub_selfhost/skills/service.py tests/test_skills_service.py
git commit -m "feat: add skill list, search, download, delete, transfer services"
```

---

### Task 13: Skill Router

**Files:**
- Create: `skillhub_selfhost/skills/router.py`
- Create: `tests/test_skills_router.py`

- [ ] **Step 1: 编写路由测试**

```python
# tests/test_skills_router.py
import io
import tarfile
import pytest
from httpx import ASGITransport, AsyncClient
from skillhub_selfhost.main import create_app
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.auth.service import register_user, login
from skillhub_selfhost.config import Config

def make_tar(skill_name: str) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo(name=f"{skill_name}/SKILL.md")
        info.size = 10
        tar.addfile(info, io.BytesIO(b"# Test"))
    return buf.getvalue()

@pytest.fixture
def app():
    return create_app()

@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest.fixture
async def auth_client(client):
    config = Config()
    await register_user("testuser", "pass123", status="active")
    tokens = await login("testuser", "pass123", config.secret_key)
    client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    yield client
    client.headers.pop("Authorization", None)

@pytest.mark.asyncio
async def test_upload_skill(auth_client):
    tar = make_tar("router-skill")
    files = {"file": ("skill.tar.gz", tar, "application/gzip")}
    data = {
        "display_name": "Router Skill",
        "description": "test",
        "tags": '["test"]',
        "version": "1.0.0",
    }
    resp = await auth_client.post("/api/skills/", files=files, data=data)
    assert resp.status_code == 201

@pytest.mark.asyncio
async def test_get_skill_list(client, auth_client):
    tar = make_tar("list-r-skill")
    files = {"file": ("skill.tar.gz", tar, "application/gzip")}
    data = {"display_name": "List", "description": "d", "tags": '["x"]', "version": "1.0.0"}
    await auth_client.post("/api/skills/", files=files, data=data)
    resp = await client.get("/api/skills/")
    assert resp.status_code == 200
    j = resp.json()
    assert j["total"] >= 1
    assert "items" in j

@pytest.mark.asyncio
async def test_download_increments_count(client, auth_client):
    tar = make_tar("count-skill")
    files = {"file": ("skill.tar.gz", tar, "application/gzip")}
    data = {"display_name": "C", "description": "d", "tags": '[]', "version": "1.0.0"}
    await auth_client.post("/api/skills/", files=files, data=data)
    resp = await client.get("/api/skills/count-skill/download")
    assert resp.status_code == 200
    # Check download count incremented
    detail = await client.get("/api/skills/count-skill/")
    assert detail.json()["download_count"] == 1
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_skills_router.py -v
```
Expected: FAIL

- [ ] **Step 3: 实现 Skill Router**

```python
# skillhub_selfhost/skills/router.py
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import StreamingResponse
from skillhub_selfhost.skills.service import (
    upload_skill, list_skills, search_skills, get_skill_detail,
    get_skill_readme, download_skill, delete_skill, delete_skill_version, transfer_skill
)
from skillhub_selfhost.skills.schemas import TransferRequest, PaginatedResponse
from skillhub_selfhost.auth.dependencies import get_current_user, require_user, require_admin
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.config import Config
import io

router = APIRouter(prefix="/api/skills", tags=["skills"])

@router.post("/", status_code=201)
async def upload(
    file: UploadFile = File(...),
    display_name: str = Form(...),
    description: str = Form(...),
    tags: str = Form("[]"),
    version: str = Form(""),
    release_notes: str | None = Form(None),
    user: User = Depends(require_user),
):
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已被禁用")
    config = Config()
    content = await file.read()
    try:
        await upload_skill(
            file_content=content,
            display_name=display_name,
            description=description,
            tags=json.loads(tags),
            version=version,
            author=user,
            skills_dir=config.skills_dir,
            release_notes=release_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400 if "格式" in str(e) or "必须" in str(e) else 409, detail=str(e))

@router.get("/")
async def list_skills_route(
    q: str | None = Query(None),
    tag: list[str] | None = Query(None),
    author: str | None = Query(None),
    sort: str = Query("downloads"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: User | None = Depends(get_current_user),
):
    author_username = None
    if author == "me" and user:
        author_username = user.username
    elif author:
        author_username = author

    if q or tag or author_username:
        items, total = await search_skills(q=q, tags=tag, author_username=author_username, page=page, size=size, sort=sort)
    else:
        items, total = await list_skills(page=page, size=size, sort=sort)
    return {"items": items, "total": total, "page": page, "size": size}

@router.get("/{name}")
async def skill_detail(name: str):
    detail = await get_skill_detail(name)
    if detail is None:
        raise HTTPException(status_code=404, detail="skill 不存在")
    return detail

@router.get("/{name}/readme")
async def readme(name: str, version: str | None = Query(None)):
    config = Config()
    try:
        content = await get_skill_readme(name, version, config.skills_dir)
        return StreamingResponse(io.BytesIO(content.encode("utf-8")), media_type="text/plain")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{name}/download")
async def download(name: str, version: str | None = Query(None)):
    config = Config()
    try:
        _, filename, content = await download_skill(name, version, config.skills_dir)
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/gzip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{name}")
async def delete(name: str, user: User = Depends(require_user)):
    try:
        await delete_skill(name, user)
    except ValueError as e:
        raise HTTPException(status_code=403 if "权限" in str(e) else 404, detail=str(e))

@router.delete("/{name}/versions/{version}")
async def delete_version(name: str, version: str, user: User = Depends(require_user)):
    try:
        await delete_skill_version(name, version, user)
    except ValueError as e:
        raise HTTPException(status_code=403 if "权限" in str(e) else 404, detail=str(e))

@router.patch("/{name}/transfer")
async def transfer(name: str, body: TransferRequest, user: User = Depends(require_user)):
    try:
        await transfer_skill(name, body.target_user, user)
    except ValueError as e:
        status_code = 403 if "权限" in str(e) else 404 if "不存在" in str(e) else 400
        raise HTTPException(status_code=status_code, detail=str(e))
```

- [ ] **Step 4: 更新 main.py 注册路由**

```python
# skillhub_selfhost/main.py 中 create_app 函数添加:
from skillhub_selfhost.skills.router import router as skills_router
app.include_router(skills_router)
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_skills_router.py -v
```
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add skillhub_selfhost/skills/router.py skillhub_selfhost/main.py tests/test_skills_router.py
git commit -m "feat: add skill API routes"
```

---

### Task 14: Admin Router

**Files:**
- Create: `skillhub_selfhost/admin/__init__.py`
- Create: `skillhub_selfhost/admin/schemas.py`
- Create: `skillhub_selfhost/admin/router.py`
- Create: `tests/test_admin_router.py`

- [ ] **Step 1: 创建 Admin schemas**

```python
# skillhub_selfhost/admin/schemas.py
from pydantic import BaseModel
from datetime import datetime

class CreateUserRequest(BaseModel):
    username: str
    password: str

class UserItem(BaseModel):
    id: str
    username: str
    status: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: 编写测试**

```python
# tests/test_admin_router.py
import pytest
from httpx import ASGITransport, AsyncClient
from skillhub_selfhost.main import create_app
from skillhub_selfhost.auth.service import register_user, login
from skillhub_selfhost.config import Config

@pytest.fixture
def app():
    return create_app()

@pytest.fixture
async def admin_client(app):
    config = Config()
    await register_user("admin", "admin123", is_admin=True, status="active")
    tokens = await login("admin", "admin123", config.secret_key)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers["Authorization"] = f"Bearer {tokens['access_token']}"
        yield c

@pytest.fixture
async def normal_client(app):
    config = Config()
    await register_user("normal", "pass123", status="active")
    tokens = await login("normal", "pass123", config.secret_key)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers["Authorization"] = f"Bearer {tokens['access_token']}"
        yield c

@pytest.mark.asyncio
async def test_list_users_admin(admin_client):
    resp = await admin_client.get("/api/admin/users/")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

@pytest.mark.asyncio
async def test_list_users_normal(normal_client):
    resp = await normal_client.get("/api/admin/users/")
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_approve_user(admin_client):
    user = await register_user("approveme", "pass1", status="pending")
    resp = await admin_client.patch(f"/api/admin/users/{user.id}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

@pytest.mark.asyncio
async def test_disable_user(admin_client):
    user = await register_user("disableme", "pass1", status="active")
    resp = await admin_client.patch(f"/api/admin/users/{user.id}/disable")
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"

@pytest.mark.asyncio
async def test_cannot_disable_admin(admin_client):
    admins = await admin_client.get("/api/admin/users/?is_admin=true")
    admin_id = admins.json()["items"][0]["id"]
    resp = await admin_client.patch(f"/api/admin/users/{admin_id}/disable")
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_create_user(admin_client):
    resp = await admin_client.post("/api/admin/users/", json={"username": "created", "password": "pass1"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "active"
```

- [ ] **Step 3: 运行测试验证失败**

```bash
pytest tests/test_admin_router.py -v
```
Expected: FAIL

- [ ] **Step 4: 实现 Admin Router**

```python
# skillhub_selfhost/admin/router.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from skillhub_selfhost.auth.dependencies import require_admin
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.auth.service import register_user
from skillhub_selfhost.admin.schemas import CreateUserRequest, UserItem

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/users/")
async def list_users(
    status_filter: str | None = Query(None, alias="status"),
    is_admin: bool | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_admin),
):
    qs = User.all()
    if status_filter:
        qs = qs.filter(status=status_filter)
    if is_admin is not None:
        qs = qs.filter(is_admin=is_admin)
    total = await qs.count()
    users = await qs.offset((page - 1) * size).limit(size).all()
    items = [{"id": str(u.id), "username": u.username, "status": u.status, "is_admin": u.is_admin, "created_at": u.created_at} for u in users]
    return {"items": items, "total": total, "page": page, "size": size}

@router.post("/users/", status_code=201)
async def create_user(body: CreateUserRequest, _: User = Depends(require_admin)):
    try:
        user = await register_user(body.username, body.password, status="active")
        return {"id": str(user.id), "username": user.username, "status": user.status, "is_admin": user.is_admin, "created_at": user.created_at}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.patch("/users/{user_id}/approve")
async def approve_user(user_id: str, _: User = Depends(require_admin)):
    user = await User.filter(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.status = "active"
    await user.save()
    return {"id": str(user.id), "username": user.username, "status": user.status, "is_admin": user.is_admin, "created_at": user.created_at}

@router.patch("/users/{user_id}/disable")
async def disable_user(user_id: str, _: User = Depends(require_admin)):
    user = await User.filter(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.is_admin:
        raise HTTPException(status_code=403, detail="不能禁用管理员账号")
    user.status = "disabled"
    await user.save()
    return {"id": str(user.id), "username": user.username, "status": user.status, "is_admin": user.is_admin, "created_at": user.created_at}

@router.patch("/users/{user_id}/enable")
async def enable_user(user_id: str, _: User = Depends(require_admin)):
    user = await User.filter(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.status = "active"
    await user.save()
    return {"id": str(user.id), "username": user.username, "status": user.status, "is_admin": user.is_admin, "created_at": user.created_at}
```

- [ ] **Step 5: 更新 main.py 注册路由**

```python
# skillhub_selfhost/main.py 中 create_app 函数添加:
from skillhub_selfhost.admin.router import router as admin_router
app.include_router(admin_router)
```

- [ ] **Step 6: 运行测试验证通过**

```bash
pytest tests/test_admin_router.py -v
```
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add skillhub_selfhost/admin/ skillhub_selfhost/main.py tests/test_admin_router.py
git commit -m "feat: add admin API routes for user management"
```

---

### Task 15: 后端集成测试

**Files:**
- Modify: `tests/conftest.py`（确保完整）
- Run: 全部测试

- [ ] **Step 1: 确保 conftest.py 完整**

```python
# tests/conftest.py
import pytest
from tortoise.contrib.test import initializer, finalizer

@pytest.fixture(autouse=True)
def setup_db():
    initializer(
        ["skillhub_selfhost.auth.models", "skillhub_selfhost.skills.models"],
        db_url="sqlite://:memory:",
    )
    yield
    finalizer()
```

- [ ] **Step 2: 运行全部测试**

```bash
pytest -v
```
Expected: ALL 25+ tests PASS

- [ ] **Step 3: 端到端手动验证**

```bash
skillhub-selfhost admin-init  # 创建 admin
skillhub-selfhost server start  # 启动服务
# curl http://localhost:8000/api/auth/register -X POST -H "Content-Type: application/json" -d '{"username":"test","password":"123"}'
# curl http://localhost:8000/api/health
```

- [ ] **Step 4: Commit**

```bash
git commit -m "test: full backend integration tests passing"
```

---

### Task 16: 前端脚手架

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "skillhub-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^7.0.0",
    "react-markdown": "^9.0.0",
    "lucide-react": "^0.400.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.5.0",
    "@radix-ui/react-slot": "^1.1.0",
    "@radix-ui/react-dialog": "^1.1.0",
    "@radix-ui/react-label": "^2.1.0",
    "@radix-ui/react-select": "^2.1.0",
    "@radix-ui/react-tabs": "^1.1.0",
    "sonner": "^1.7.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 2: 创建 Vite 配置**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: '../skillhub_selfhost/dist',
    emptyOutDir: true,
  },
})
```

- [ ] **Step 3: 创建 Tailwind/PostCSS 配置**

```typescript
// frontend/tailwind.config.ts
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: { extend: {} },
  plugins: [],
} satisfies Config
```

```javascript
// frontend/postcss.config.js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 4: 创建 tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "paths": {
      "@/*": ["./src/*"]
    },
    "baseUrl": "."
  },
  "include": ["src"]
}
```

- [ ] **Step 5: 创建入口文件**

```html
<!-- frontend/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>skillhub</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

```css
/* frontend/src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

```tsx
// frontend/src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
```

```tsx
// frontend/src/App.tsx
import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import Layout from './components/Layout'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import SkillDetail from './pages/SkillDetail'
import Upload from './pages/Upload'
import MySkills from './pages/MySkills'
import Admin from './pages/Admin'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/skills/:name" element={<SkillDetail />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/my" element={<MySkills />} />
          <Route path="/admin" element={<Admin />} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}
```

- [ ] **Step 6: npm install**

```bash
cd frontend; npm install
```

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold frontend with React, Vite, Tailwind CSS, react-router-dom"
```

---

### Task 17: shadcn/ui 工具函数

**Files:**
- Create: `frontend/src/lib/utils.ts`

- [ ] **Step 1: 创建 cn 工具函数**

```typescript
// frontend/src/lib/utils.ts
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/
git commit -m "feat: add shadcn/ui cn utility"
```

---

### Task 18: AuthContext + API Client

**Files:**
- Create: `frontend/src/contexts/AuthContext.tsx`
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: 实现 AuthContext**

```typescript
// frontend/src/contexts/AuthContext.tsx
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'

interface User {
  id: string
  username: string
  status: string
  is_admin: boolean
  created_at: string
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  login: (accessToken: string, refreshToken: string, user: User) => void
  logout: () => void
  refreshAuth: () => Promise<boolean>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(() => localStorage.getItem('access_token'))
  const [refreshToken, setRefreshToken] = useState<string | null>(() => localStorage.getItem('refresh_token'))

  const login = useCallback((access: string, refresh: string, u: User) => {
    setAccessToken(access)
    setRefreshToken(refresh)
    setUser(u)
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }, [])

  const logout = useCallback(() => {
    setAccessToken(null)
    setRefreshToken(null)
    setUser(null)
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }, [])

  const refreshAuth = useCallback(async (): Promise<boolean> => {
    if (!refreshToken) return false
    try {
      const resp = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (!resp.ok) {
        logout()
        return false
      }
      const data = await resp.json()
      setAccessToken(data.access_token)
      setRefreshToken(data.refresh_token)
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      return true
    } catch {
      logout()
      return false
    }
  }, [refreshToken, logout])

  useEffect(() => {
    if (accessToken && !user) {
      fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
        .then(r => r.ok ? r.json() : null)
        .then(u => {
          if (u) setUser(u)
          else logout()
        })
    }
  }, [accessToken])

  return (
    <AuthContext.Provider value={{ user, accessToken, refreshToken, login, logout, refreshAuth }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
```

- [ ] **Step 2: 实现 API client**

```typescript
// frontend/src/api/client.ts
let getAccessToken: (() => string | null) | null = null
let getRefreshToken: (() => string | null) | null = null
let onRefresh: (() => Promise<boolean>) | null = null
let onLogout: (() => void) | null = null

export function initApiClient(
  accessTokenFn: () => string | null,
  refreshTokenFn: () => string | null,
  refreshFn: () => Promise<boolean>,
  logoutFn: () => void,
) {
  getAccessToken = accessTokenFn
  getRefreshToken = refreshTokenFn
  onRefresh = refreshFn
  onLogout = logoutFn
}

export async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  }
  if (getAccessToken) {
    const token = getAccessToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  let resp = await fetch(url, { ...options, headers })

  if (resp.status === 401 && onRefresh) {
    const refreshed = await onRefresh()
    if (refreshed) {
      const newToken = getAccessToken?.()
      if (newToken) headers['Authorization'] = `Bearer ${newToken}`
      resp = await fetch(url, { ...options, headers })
    } else {
      onLogout?.()
    }
  }

  return resp
}
```

- [ ] **Step 3: 在 App.tsx 中初始化 client**

修改 `frontend/src/App.tsx`，在 `App` 函数开头添加：

```typescript
import { useEffect } from 'react'
import { initApiClient } from './api/client'

export default function App() {
  const { accessToken, refreshToken, refreshAuth, logout } = useAuth()
  
  useEffect(() => {
    initApiClient(
      () => accessToken,
      () => refreshToken,
      refreshAuth,
      logout,
    )
  }, [accessToken, refreshToken, refreshAuth, logout])

  return (
    <AuthProvider>
      ...
    </AuthProvider>
  )
}
```

Wait, the initApiClient call needs to be inside AuthProvider since `useAuth` only works there. Let me restructure. Actually, let me have App use a wrapper component.

- [ ] **Step 4: 修正 App.tsx 结构**

```tsx
// frontend/src/App.tsx
import { Routes, Route } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { initApiClient } from './api/client'
import Layout from './components/Layout'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import SkillDetail from './pages/SkillDetail'
import Upload from './pages/Upload'
import MySkills from './pages/MySkills'
import Admin from './pages/Admin'

function AppRoutes() {
  const { accessToken, refreshToken, logout, refreshAuth } = useAuth()

  useEffect(() => {
    initApiClient(
      () => accessToken,
      () => refreshToken,
      refreshAuth,
      logout,
    )
  }, [accessToken, refreshToken, refreshAuth, logout])

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/skills/:name" element={<SkillDetail />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/my" element={<MySkills />} />
        <Route path="/admin" element={<Admin />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
```

- [ ] **Step 5: 修正 main.tsx**（移除 BrowserRouter，App 内部自己处理路由没有问题，但需要 BrowserRouter）

```tsx
// frontend/src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/contexts/ frontend/src/api/ frontend/src/App.tsx frontend/src/main.tsx
git commit -m "feat: add AuthContext and API client with 401 auto-refresh"
```

---

### Task 19: Layout + shadcn/ui Components

**Files:**
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/ui/` (button, input, card, badge, tabs, dialog, sonner)

使用 `npx shadcn@latest add` 命令添加组件：

- [ ] **Step 1: 初始化 shadcn/ui**

```bash
cd frontend
npx shadcn@latest init -d --force
```

- [ ] **Step 2: 添加所需组件**

```bash
cd frontend
npx shadcn@latest add button -y
npx shadcn@latest add input -y
npx shadcn@latest add card -y
npx shadcn@latest add badge -y
npx shadcn@latest add tabs -y
npx shadcn@latest add dialog -y
npx shadcn@latest add sonner -y
npx shadcn@latest add skeleton -y
npx shadcn@latest add label -y
npx shadcn@latest add select -y
```

- [ ] **Step 3: 实现 Layout 组件**

```tsx
// frontend/src/components/Layout.tsx
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { useAuth } from '../contexts/AuthContext'
import { Button } from './ui/button'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="font-bold text-lg">skillhub</Link>
          <div className="flex items-center gap-3">
            {user ? (
              <>
                <span className="text-sm text-gray-600">{user.username}</span>
                {user.is_admin && <Link to="/admin" className="text-sm text-blue-600">管理</Link>}
                <Link to="/my" className="text-sm text-gray-600">我的</Link>
                <Button variant="ghost" size="sm" onClick={() => { logout(); navigate('/') }}>退出</Button>
              </>
            ) : (
              <Link to="/login"><Button variant="ghost" size="sm">登录</Button></Link>
            )}
          </div>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-6">
        <Outlet />
      </main>
      <Toaster position="top-right" />
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/
git commit -m "feat: add Layout component and shadcn/ui components"
```

---

### Task 20: 登录/注册页

**Files:**
- Create: `frontend/src/pages/Login.tsx`
- Create: `frontend/src/pages/Register.tsx`

- [ ] **Step 1: Login 页面**

```tsx
// frontend/src/pages/Login.tsx
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useAuth } from '../contexts/AuthContext'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.detail)
      const meRes = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${data.access_token}` },
      })
      const user = await meRes.json()
      login(data.access_token, data.refresh_token, user)
      toast.success('登录成功')
      navigate('/')
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex justify-center mt-20">
      <Card className="w-96">
        <CardHeader><CardTitle className="text-center">登录 skillhub</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="username">用户名</Label>
              <Input id="username" value={username} onChange={e => setUsername(e.target.value)} required />
            </div>
            <div>
              <Label htmlFor="password">密码</Label>
              <Input id="password" type="password" value={password} onChange={e => setPassword(e.target.value)} required />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? '登录中...' : '登录'}
            </Button>
          </form>
          <p className="text-sm text-center mt-4">
            还没有账号？<Link to="/register" className="text-blue-600">立即注册</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 2: Register 页面**

```tsx
// frontend/src/pages/Register.tsx
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

export default function Register() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (password !== confirm) {
      toast.error('两次密码不一致')
      return
    }
    setLoading(true)
    try {
      const resp = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (!resp.ok) {
        const data = await resp.json()
        throw new Error(data.detail)
      }
      toast.success('注册已提交，等待管理员审批')
      navigate('/')
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex justify-center mt-20">
      <Card className="w-96">
        <CardHeader><CardTitle className="text-center">注册 skillhub</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="username">用户名</Label>
              <Input id="username" value={username} onChange={e => setUsername(e.target.value)} required />
            </div>
            <div>
              <Label htmlFor="password">密码</Label>
              <Input id="password" type="password" value={password} onChange={e => setPassword(e.target.value)} required />
            </div>
            <div>
              <Label htmlFor="confirm">确认密码</Label>
              <Input id="confirm" type="password" value={confirm} onChange={e => setConfirm(e.target.value)} required />
            </div>
            <p className="text-xs text-gray-500">提交后需等待管理员审批</p>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? '注册中...' : '注册'}
            </Button>
          </form>
          <p className="text-sm text-center mt-4">
            已有账号？<Link to="/login" className="text-blue-600">立即登录</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 3: npm run dev 验证页面渲染**

```bash
cd frontend; npm run dev
# 访问 http://localhost:5173/login, http://localhost:5173/register
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Login.tsx frontend/src/pages/Register.tsx
git commit -m "feat: add login and register pages"
```

---

### Task 21: 首页

**Files:**
- Create: `frontend/src/pages/Home.tsx`

- [ ] **Step 1: 实现首页**

```tsx
// frontend/src/pages/Home.tsx
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api/client'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Skeleton } from '../components/ui/skeleton'
import { Search, ChevronLeft, ChevronRight } from 'lucide-react'

interface SkillItem {
  name: string
  display_name: string
  description: string
  author: { username: string; status: string }
  latest_version: string
  tags: string[]
  download_count: number
}

export default function Home() {
  const [skills, setSkills] = useState<SkillItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const [activeTags, setActiveTags] = useState<string[]>([])
  const [sort, setSort] = useState('downloads')
  const [loading, setLoading] = useState(true)
  const [allTags, setAllTags] = useState<string[]>([])

  const PAGE_SIZE = 20

  useEffect(() => {
    loadSkills()
  }, [page, activeTags, sort])

  useEffect(() => {
    setPage(1)
    loadSkills()
  }, [activeTags])

  async function loadSkills() {
    setLoading(true)
    const params = new URLSearchParams()
    params.set('page', String(page))
    params.set('size', String(PAGE_SIZE))
    params.set('sort', sort)
    if (q) params.set('q', q)
    activeTags.forEach(t => params.append('tag', t))

    const resp = await apiFetch(`/api/skills/?${params}`)
    const data = await resp.json()
    setSkills(data.items)
    setTotal(data.total)

    if (allTags.length === 0) {
      const tags = new Set<string>()
      data.items.forEach((s: SkillItem) => s.tags.forEach(t => tags.add(t)))
      setAllTags(Array.from(tags).sort())
    }
    setLoading(false)
  }

  function toggleTag(tag: string) {
    setActiveTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag])
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
    loadSkills()
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div>
      <form onSubmit={handleSearch} className="flex gap-2 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            className="pl-10"
            placeholder="搜索 skill 名称或描述"
            value={q}
            onChange={e => setQ(e.target.value)}
          />
        </div>
      </form>

      <div className="flex gap-2 mb-4">
        {(['downloads', 'weekly', 'newest'] as const).map(s => (
          <Button key={s} variant={sort === s ? 'default' : 'outline'} size="sm" onClick={() => { setSort(s); setPage(1) }}>
            {{downloads: '总下载', weekly: '本周热门', newest: '最新上传'}[s]}
          </Button>
        ))}
      </div>

      {allTags.length > 0 && (
        <div className="flex gap-1 mb-4 flex-wrap">
          <Badge variant={activeTags.length === 0 ? 'default' : 'outline'} className="cursor-pointer" onClick={() => setActiveTags([])}>
            All
          </Badge>
          {allTags.map(tag => (
            <Badge key={tag} variant={activeTags.includes(tag) ? 'default' : 'outline'} className="cursor-pointer" onClick={() => toggleTag(tag)}>
              {tag}
            </Badge>
          ))}
        </div>
      )}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}
        </div>
      ) : skills.length === 0 ? (
        <div className="text-center py-20 text-gray-400">还没有 skill，快来上传第一个吧</div>
      ) : (
        <div className="space-y-2">
          <div className="grid grid-cols-12 gap-4 text-xs text-gray-500 px-3 py-2 border-b">
            <span className="col-span-1">#</span>
            <span className="col-span-4">Skill</span>
            <span className="col-span-2">作者</span>
            <span className="col-span-2">版本</span>
            <span className="col-span-2">标签</span>
            <span className="col-span-1 text-right">下载</span>
          </div>
          {skills.map((skill, i) => (
            <Link
              key={skill.name}
              to={`/skills/${skill.name}`}
              className="grid grid-cols-12 gap-4 px-3 py-2 rounded hover:bg-gray-100 items-center"
            >
              <span className="col-span-1 text-sm text-gray-500">{(page - 1) * PAGE_SIZE + i + 1}</span>
              <div className="col-span-4">
                <div className="font-medium">{skill.display_name}</div>
                <div className="text-xs text-gray-500 truncate">{skill.description}</div>
              </div>
              <span className="col-span-2 text-sm text-gray-600">
                {skill.author.username}
                {skill.author.status === 'disabled' && <Badge variant="destructive" className="ml-1 text-[10px]">已封禁</Badge>}
              </span>
              <span className="col-span-2 text-sm text-gray-500">{skill.latest_version}</span>
              <span className="col-span-2 flex gap-1 flex-wrap">
                {skill.tags.slice(0, 3).map(t => <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>)}
              </span>
              <span className="col-span-1 text-sm text-right text-gray-500">{skill.download_count.toLocaleString()}</span>
            </Link>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-2 mt-4">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm">{page} / {totalPages}</span>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Home.tsx
git commit -m "feat: add home page with skill list, search, tag filter, and sorting"
```

---

### Task 22: Skill 详情页

**Files:**
- Create: `frontend/src/pages/SkillDetail.tsx`

- [ ] **Step 1: 实现详情页**

```tsx
// frontend/src/pages/SkillDetail.tsx
import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { toast } from 'sonner'
import { apiFetch } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'
import { Card, CardContent } from '../components/ui/card'
import { ArrowLeft, Copy, Download, Trash2 } from 'lucide-react'

interface Version {
  version: string
  release_notes: string | null
  file_size: number
  created_at: string
}

interface SkillDetail {
  name: string
  display_name: string
  description: string
  author: { username: string; status: string }
  tags: string[]
  download_count: number
  versions: Version[]
}

export default function SkillDetail() {
  const { name } = useParams<{ name: string }>()
  const { user } = useAuth()
  const [skill, setSkill] = useState<SkillDetail | null>(null)
  const [readme, setReadme] = useState('')
  const [selectedVersion, setSelectedVersion] = useState('')
  const [loading, setLoading] = useState(true)
  const isAuthor = user?.username === skill?.author.username

  useEffect(() => { loadSkill() }, [name])

  async function loadSkill(version?: string) {
    setLoading(true)
    const params = version ? `?version=${version}` : ''
    const resp = await apiFetch(`/api/skills/${name}/${params}`)
    if (!resp.ok) return
    const data = await resp.json()
    setSkill(data)
    const v = version || data.versions[0]?.version
    setSelectedVersion(v)

    const rmResp = await apiFetch(`/api/skills/${name}/readme?version=${v}`)
    if (rmResp.ok) setReadme(await rmResp.text())

    setLoading(false)
  }

  function handleVersionClick(version: string) {
    setSelectedVersion(version)
    loadSkill(version)
  }

  async function handleDeleteVersion(version: string) {
    if (!confirm(`确定删除版本 ${version}？`)) return
    const resp = await apiFetch(`/api/skills/${name}/versions/${version}`, { method: 'DELETE' })
    if (resp.ok) {
      toast.success('版本已删除')
      loadSkill()
    } else {
      const data = await resp.json()
      toast.error(data.detail)
    }
  }

  function formatSize(bytes: number) {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1048576).toFixed(1)} MB`
  }

  const downloadUrl = `${window.location.origin}/api/skills/${name}/download${selectedVersion ? `?version=${selectedVersion}` : ''}`

  if (loading) return <div className="space-y-4"><Skeleton className="h-8 w-64" /><Skeleton className="h-96 w-full" /></div>
  if (!skill) return <div className="text-center py-20 text-gray-400">skill 不存在</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <Link to="/" className="flex items-center text-sm text-gray-500 hover:text-gray-700">
          <ArrowLeft className="h-4 w-4 mr-1" />返回
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">{skill.display_name} @ {selectedVersion}</span>
          <a href={downloadUrl}>
            <Button size="sm"><Download className="h-4 w-4 mr-1" />下载 tar.gz</Button>
          </a>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <Card>
            <CardContent className="p-6 prose prose-sm max-w-none">
              <ReactMarkdown>{readme || '# 暂无 README'}</ReactMarkdown>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardContent className="p-4 space-y-3">
              <div>
                <div className="text-sm text-gray-500 mb-1">安装命令</div>
                <div className="bg-gray-100 rounded p-2 text-xs font-mono break-all">
                  curl -o {name}-v{selectedVersion}.tar.gz {downloadUrl}
                </div>
                <Button variant="ghost" size="sm" className="mt-1" onClick={() => { navigator.clipboard.writeText(`curl -o ${name}-v${selectedVersion}.tar.gz ${downloadUrl}`); toast.success('已复制') }}>
                  <Copy className="h-3 w-3 mr-1" />复制
                </Button>
              </div>
              <div>
                <div className="text-sm text-gray-500">基本信息</div>
                <div className="text-sm mt-1">作者: {skill.author.username}</div>
                <div className="text-sm">下载: {skill.download_count.toLocaleString()} 次</div>
                <div className="flex gap-1 mt-1 flex-wrap">
                  {skill.tags.map(t => <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>)}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-sm text-gray-500 mb-2">历史版本</div>
              <div className="space-y-1">
                {skill.versions.map((v) => (
                  <div key={v.version} className={`flex items-center justify-between p-2 rounded text-sm cursor-pointer ${selectedVersion === v.version ? 'bg-blue-50' : 'hover:bg-gray-50'}`} onClick={() => handleVersionClick(v.version)}>
                    <div>
                      <span className={selectedVersion === v.version ? 'font-medium text-blue-600' : ''}>{v.version}</span>
                      {skill.versions[0]?.version === v.version && <Badge variant="outline" className="ml-1 text-[10px]">最新</Badge>}
                      <div className="text-xs text-gray-400">{formatSize(v.file_size)}</div>
                    </div>
                    <div className="flex gap-1">
                      <a href={`/api/skills/${name}/download?version=${v.version}`} onClick={e => e.stopPropagation()}>
                        <Button variant="ghost" size="icon" className="h-7 w-7"><Download className="h-3 w-3" /></Button>
                      </a>
                      {isAuthor && (
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={(e) => { e.stopPropagation(); handleDeleteVersion(v.version) }}>
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <a href={downloadUrl}>
            <Button className="w-full"><Download className="h-4 w-4 mr-1" />下载 tar.gz</Button>
          </a>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/SkillDetail.tsx
git commit -m "feat: add skill detail page with markdown rendering and version management"
```

---

### Task 23: 上传页

**Files:**
- Create: `frontend/src/pages/Upload.tsx`

- [ ] **Step 1: 实现上传页**

```tsx
// frontend/src/pages/Upload.tsx
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useAuth } from '../contexts/AuthContext'
import { apiFetch } from '../api/client'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Badge } from '../components/ui/badge'
import { Card, CardContent } from '../components/ui/card'
import { ArrowLeft, Upload as UploadIcon, X } from 'lucide-react'

export default function Upload() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [skillName, setSkillName] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [description, setDescription] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')
  const [version, setVersion] = useState('')
  const [releaseNotes, setReleaseNotes] = useState('')
  const [uploading, setUploading] = useState(false)

  if (!user) { navigate('/login'); return null }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()
    if (!file) { toast.error('请选择文件'); return }
    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('display_name', displayName)
    formData.append('description', description)
    formData.append('tags', JSON.stringify(tags))
    formData.append('version', version)
    if (releaseNotes) formData.append('release_notes', releaseNotes)

    try {
      const resp = await apiFetch('/api/skills/', { method: 'POST', body: formData })
      if (!resp.ok) {
        const data = await resp.json()
        throw new Error(data.detail)
      }
      toast.success('上传成功')
      navigate('/my')
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setUploading(false)
    }
  }

  function addTag() {
    const t = tagInput.trim()
    if (t && !tags.includes(t)) {
      setTags([...tags, t])
      setTagInput('')
    }
  }

  return (
    <div>
      <Link to="/my" className="flex items-center text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft className="h-4 w-4 mr-1" />返回我的技能
      </Link>
      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-bold mb-4">上传新 Skill</h2>
          <form onSubmit={handleUpload} className="space-y-4">
            <div className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:bg-gray-50"
              onDragOver={e => e.preventDefault()}
              onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) { setFile(f); setSkillName(f.name.replace('.tar.gz', '').replace('.tgz', '')) } }}
              onClick={() => document.getElementById('file-upload')?.click()}
            >
              <input id="file-upload" type="file" accept=".tar.gz,.tgz" className="hidden"
                onChange={e => {
                  const f = e.target.files?.[0]
                  if (f) { setFile(f); setSkillName(f.name.replace('.tar.gz', '').replace('.tgz', '')) }
                }}
              />
              <UploadIcon className="h-8 w-8 mx-auto text-gray-400 mb-2" />
              <p className="text-sm text-gray-500">{file ? file.name : '拖拽 tar.gz 到此处或点击选择文件'}</p>
            </div>

            <div><Label>skill 名称</Label><Input value={skillName} readOnly className="bg-gray-50" /><p className="text-xs text-gray-400">从目录名自动提取</p></div>
            <div><Label>展示名称</Label><Input value={displayName} onChange={e => setDisplayName(e.target.value)} required /></div>
            <div><Label>描述</Label><Input value={description} onChange={e => setDescription(e.target.value)} required /></div>
            <div>
              <Label>标签</Label>
              <div className="flex gap-1 flex-wrap mb-1">
                {tags.map(t => <Badge key={t} variant="secondary" className="cursor-pointer" onClick={() => setTags(tags.filter(x => x !== t))}>{t} <X className="h-3 w-3 ml-1" /></Badge>)}
              </div>
              <div className="flex gap-1">
                <Input value={tagInput} onChange={e => setTagInput(e.target.value)} placeholder="添加标签" onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag() } }} />
                <Button type="button" variant="outline" size="sm" onClick={addTag}>添加</Button>
              </div>
            </div>
            <div><Label>版本（留空自动追加小版本）</Label><Input value={version} onChange={e => setVersion(e.target.value)} placeholder="如 1.0.0" /></div>
            <div><Label>更新说明（可选）</Label><Input value={releaseNotes} onChange={e => setReleaseNotes(e.target.value)} /></div>

            <Button type="submit" disabled={uploading} className="w-full">
              {uploading ? '上传中...' : '上传'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Upload.tsx
git commit -m "feat: add skill upload page with drag-and-drop"
```

---

### Task 24: 我的技能页

**Files:**
- Create: `frontend/src/pages/MySkills.tsx`

- [ ] **Step 1: 实现我的技能页**

```tsx
// frontend/src/pages/MySkills.tsx
import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useAuth } from '../contexts/AuthContext'
import { apiFetch } from '../api/client'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Card, CardContent } from '../components/ui/card'
import { Skeleton } from '../components/ui/skeleton'
import { ArrowLeft, Plus, Trash2, ArrowRightLeft } from 'lucide-react'

interface MySkill {
  name: string
  display_name: string
  description: string
  latest_version: string
  tags: string[]
  download_count: number
  versions: { version: string }[]
}

export default function MySkills() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [skills, setSkills] = useState<MySkill[]>([])
  const [loading, setLoading] = useState(true)

  if (!user) { navigate('/login'); return null }

  useEffect(() => { loadSkills() }, [])

  async function loadSkills() {
    setLoading(true)
    const resp = await apiFetch(`/api/skills/?author=me`)
    const data = await resp.json()
    setSkills(data.items)
    setLoading(false)
  }

  async function handleDelete(name: string) {
    if (!confirm(`确定删除 ${name}？此操作不可撤销。`)) return
    const resp = await apiFetch(`/api/skills/${name}`, { method: 'DELETE' })
    if (resp.ok) {
      toast.success('已删除')
      loadSkills()
    } else {
      const data = await resp.json()
      toast.error(data.detail)
    }
  }

  async function handleTransfer(name: string) {
    const target = prompt('输入目标用户名')
    if (!target) return
    const resp = await apiFetch(`/api/skills/${name}/transfer`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_user: target }),
    })
    if (resp.ok) {
      toast.success('转移成功')
      loadSkills()
    } else {
      const data = await resp.json()
      toast.error(data.detail)
    }
  }

  if (loading) return <div className="space-y-4">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-32 w-full" />)}</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <Link to="/" className="flex items-center text-sm text-gray-500 hover:text-gray-700">
          <ArrowLeft className="h-4 w-4 mr-1" />返回首页
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600">{user.username}</span>
          <Link to="/upload"><Button size="sm"><Plus className="h-4 w-4 mr-1" />上传新 Skill</Button></Link>
        </div>
      </div>

      <h2 className="text-lg font-bold mb-4">我的 Skills ({skills.length})</h2>

      {skills.length === 0 ? (
        <div className="text-center py-20 text-gray-400">还没有 skill，快来上传第一个吧</div>
      ) : (
        <div className="space-y-3">
          {skills.map(skill => (
            <Card key={skill.name}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <Link to={`/skills/${skill.name}`} className="font-medium hover:text-blue-600">{skill.display_name}</Link>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500" onClick={() => handleDelete(skill.name)} title="删除">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleTransfer(skill.name)} title="转移">
                      <ArrowRightLeft className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="text-sm text-gray-500">
                  {skill.latest_version && <span>{skill.latest_version} (latest) · </span>}
                  {skill.tags.length > 0 && <span>{skill.tags.join(', ')} · </span>}
                  总下载 {skill.download_count.toLocaleString()}
                </div>
                <div className="mt-2 flex gap-1 flex-wrap">
                  {skill.tags.map(t => <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>)}
                </div>
                <Link to={`/upload?name=${skill.name}`} className="mt-2 inline-block">
                  <Button variant="outline" size="sm"><Plus className="h-3 w-3 mr-1" />追加新版本</Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/MySkills.tsx
git commit -m "feat: add my skills page with delete and transfer"
```

---

### Task 25: 管理员页

**Files:**
- Create: `frontend/src/pages/Admin.tsx`

- [ ] **Step 1: 实现管理员页**

```tsx
// frontend/src/pages/Admin.tsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useAuth } from '../contexts/AuthContext'
import { apiFetch } from '../api/client'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Badge } from '../components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog'
import { Skeleton } from '../components/ui/skeleton'
import { Plus } from 'lucide-react'

interface UserItem {
  id: string
  username: string
  status: string
  is_admin: boolean
  created_at: string
}

export default function Admin() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [users, setUsers] = useState<UserItem[]>([])
  const [loading, setLoading] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)
  const [newUsername, setNewUsername] = useState('')
  const [newPassword, setNewPassword] = useState('')

  if (!user?.is_admin) { navigate('/'); return null }

  useEffect(() => { loadUsers() }, [])

  async function loadUsers(status?: string) {
    setLoading(true)
    const params = status ? `?status=${status}` : ''
    const resp = await apiFetch(`/api/admin/users/${params}`)
    const data = await resp.json()
    setUsers(data.items)
    setLoading(false)
  }

  async function approveUser(id: string) {
    const resp = await apiFetch(`/api/admin/users/${id}/approve`, { method: 'PATCH' })
    if (resp.ok) { toast.success('已通过'); loadUsers() }
    else { const d = await resp.json(); toast.error(d.detail) }
  }

  async function disableUser(id: string) {
    if (!confirm('确定禁用该用户？')) return
    const resp = await apiFetch(`/api/admin/users/${id}/disable`, { method: 'PATCH' })
    if (resp.ok) { toast.success('已禁用'); loadUsers() }
    else { const d = await resp.json(); toast.error(d.detail) }
  }

  async function enableUser(id: string) {
    const resp = await apiFetch(`/api/admin/users/${id}/enable`, { method: 'PATCH' })
    if (resp.ok) { toast.success('已启用'); loadUsers() }
    else { const d = await resp.json(); toast.error(d.detail) }
  }

  async function createUser(e: React.FormEvent) {
    e.preventDefault()
    const resp = await apiFetch('/api/admin/users/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: newUsername, password: newPassword }),
    })
    if (resp.ok) {
      toast.success('用户已创建')
      setCreateOpen(false)
      setNewUsername('')
      setNewPassword('')
      loadUsers()
    } else {
      const d = await resp.json()
      toast.error(d.detail)
    }
  }

  const statusIcon = (s: string) => {
    if (s === 'active') return <span className="text-green-500">✅ 活跃</span>
    if (s === 'pending') return <span className="text-yellow-500">🕐 待审批</span>
    return <span className="text-red-500">🚫 已禁用</span>
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold">用户管理</h2>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button size="sm"><Plus className="h-4 w-4 mr-1" />创建用户</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>创建新用户</DialogTitle></DialogHeader>
            <form onSubmit={createUser} className="space-y-3">
              <div><Label>用户名</Label><Input value={newUsername} onChange={e => setNewUsername(e.target.value)} required /></div>
              <div><Label>密码</Label><Input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} required /></div>
              <Button type="submit">创建</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Tabs defaultValue="all" onValueChange={v => loadUsers(v === 'all' ? undefined : v)}>
        <TabsList>
          <TabsTrigger value="all">所有用户</TabsTrigger>
          <TabsTrigger value="pending">待审批</TabsTrigger>
        </TabsList>
        <TabsContent value="all" className="mt-4">
          {loading ? <Skeleton className="h-64 w-full" /> : users.length === 0 ? (
            <div className="text-center py-10 text-gray-400">暂无用户</div>
          ) : (
            <div className="space-y-2">
              {users.map(u => (
                <Card key={u.id}>
                  <CardContent className="p-3 flex items-center justify-between">
                    <div>
                      <span className="font-medium">{u.username}</span>
                      {u.is_admin && <Badge variant="default" className="ml-2">管理员</Badge>}
                      <span className="ml-2 text-sm">{statusIcon(u.status)}</span>
                      <span className="ml-2 text-xs text-gray-400">{new Date(u.created_at).toLocaleDateString()}</span>
                    </div>
                    <div className="flex gap-1">
                      {u.status === 'pending' && (
                        <>
                          <Button variant="outline" size="sm" onClick={() => approveUser(u.id)}>通过</Button>
                          <Button variant="outline" size="sm" onClick={() => disableUser(u.id)}>驳回</Button>
                        </>
                      )}
                      {u.status === 'active' && !u.is_admin && (
                        <Button variant="outline" size="sm" onClick={() => disableUser(u.id)}>禁用</Button>
                      )}
                      {u.status === 'disabled' && (
                        <Button variant="outline" size="sm" onClick={() => enableUser(u.id)}>启用</Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
        <TabsContent value="pending">
          {loading ? <Skeleton className="h-64 w-full" /> : users.length === 0 ? (
            <div className="text-center py-10 text-gray-400">暂无待审批用户</div>
          ) : (
            <div className="space-y-2 mt-4">
              {users.map(u => (
                <Card key={u.id}>
                  <CardContent className="p-3 flex items-center justify-between">
                    <div><span className="font-medium">{u.username}</span><span className="ml-2 text-xs text-gray-400">{new Date(u.created_at).toLocaleDateString()}</span></div>
                    <div className="flex gap-1">
                      <Button variant="outline" size="sm" onClick={() => approveUser(u.id)}>通过</Button>
                      <Button variant="outline" size="sm" onClick={() => disableUser(u.id)}>驳回</Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Admin.tsx
git commit -m "feat: add admin page for user approval and management"
```

---

### Task 26: 前端构建与集成

**Files:**
- Modify: `skillhub_selfhost/dist/`（构建产物）

- [ ] **Step 1: 构建前端**

```bash
cd frontend; npm run build
```
Expected: 输出到 `skillhub_selfhost/dist/`

- [ ] **Step 2: 更新 main.py 的 SPA fallback**

```python
# skillhub_selfhost/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

def create_app() -> FastAPI:
    app = FastAPI(title="skillhub")

    from skillhub_selfhost.auth.router import router as auth_router
    from skillhub_selfhost.skills.router import router as skills_router
    from skillhub_selfhost.admin.router import router as admin_router

    app.include_router(auth_router)
    app.include_router(skills_router)
    app.include_router(admin_router)

    dist_path = Path(__file__).parent / "dist"
    if dist_path.exists() and (dist_path / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="frontend")

    return app
```

- [ ] **Step 3: 验证完整启动**

```bash
skillhub-selfhost server start --port 8000
```
浏览器访问 `http://localhost:8000`，确认首页/登录/注册/管理员等功能正常

- [ ] **Step 4: Commit**

```bash
git add skillhub_selfhost/main.py skillhub_selfhost/dist/
git commit -m "feat: integrate frontend build into package"
```

---

### Task 27: 最终验证与清理

- [ ] **Step 1: 运行全部后端测试**

```bash
pytest -v
```
Expected: ALL PASS

- [ ] **Step 2: 确认 wheel 打包正确**

```bash
pip install build
python -m build
# 验证 dist/*.whl 包含 skillhub_selfhost/dist/
```

- [ ] **Step 3: 清理并最终提交**

```bash
git status
git add -A
git commit -m "chore: final integration and cleanup"
```

---

## 自审

- [x] **Spec 覆盖检查** — 每个 spec 需求都有对应 task：User 模型 (T6)、Skill 模型 (T10)、Auth API (T7-T9)、Skill API (T11-T13)、Admin API (T14)、CLI (T5)、前端所有页面 (T16-T25)、日志 (T4)、配置 (T2)、数据库 (T3)
- [x] **无占位符** — 所有 step 都包含完整代码
- [x] **类型一致性** — 前后端使用统一的 interface/schema，字段名一致