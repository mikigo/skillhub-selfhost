# skillhub-selfhost 设计文档

> 日期: 2026-09-28
> 状态: 已确认

## 1. 项目定位

面向小团队内网部署的 AI 技能市场平台。开发者上传、版本化管理、分发 agent skills（文件目录包形式），其他成员浏览、搜索、下载安装。

核心原则：轻量（pip install 一键部署）、自部署（内网可用，零 CDN）、易安装（无需 docker/kubernetes）。

## 2. 技术栈

| 层 | 选择 | 说明 |
|---|---|---|
| 后端框架 | FastAPI | 异步、类型安全、生态好 |
| ORM | Tortoise ORM | 原生异步、类 Django API |
| 默认数据库 | SQLite | 零配置，用户可自定义 PostgreSQL/MySQL |
| 前端 | React + Vite | SPA，build 后由 FastAPI serve |
| 前端路由 | react-router-dom v7 | SPA 路由 |
| UI 库 | shadcn/ui + Tailwind CSS | 全部本地打包，零 CDN |
| 图标 | lucide-react | 打包进 bundle |
| 认证 | JWT (access + refresh token) | 用户名密码登录，无状态，不存 DB |
| 密码哈希 | bcrypt | 标准选择 |
| CLI | typer | 类型提示的 CLI 框架 |
| 打包 | pyproject.toml + setuptools | wheel 分发 |
| 前端状态管理 | React Context + useReducer | 内网小团队够用，无额外依赖 |
| Markdown 渲染 | react-markdown | 详情页渲染 SKILL.md |

## 3. 部署与启动

### 安装

```bash
pip install skillhub-selfhost
```

### 初始化管理员

```bash
skillhub-selfhost admin-init
# 交互式提示：管理员用户名 → 管理员密码 → 创建
```

若 `metadata.db` 不存在则自动创建，写入一个 `is_admin=True` + `status=active` 的管理员用户。

### 启动服务

```bash
skillhub-selfhost server start                  # 默认 :8000
skillhub-selfhost server start --port 8080      # 自定义端口
skillhub-selfhost server start --host 0.0.0.0   # 局域网可访问
```

`server start` **自动初始化**：检查 `metadata.db`、`skills/`、`logs/` 目录，不存在则自动创建；之后执行 `generate_schemas()` 确保表结构存在，最后启动 uvicorn。

启动时 `os.getcwd()` 作为 `BASE_DIR`，该目录下：

```
{BASE_DIR}/
├── metadata.db           # SQLite（默认），用户可配置为 PostgreSQL/MySQL
├── .secret               # JWT 签名密钥（自动生成，首次启动持久化）
├── logs/
│   ├── skillhub-2026-09-28.log
│   └── skillhub-2026-09-27.log
├── skills/               # 所有 skill 文件存储
│   ├── alice/
│   │   └── my-linter/
│   │       ├── v1.0.0/
│   │       │   ├── SKILL.md
│   │       │   └── scripts/...
│   │       └── v1.1.0/
│   │           └── ...
│   └── bob/
│       └── some-skill/
│           └── v1.0.0/
│               └── ...
```

前端 `dist/` 来自 wheel 包内的 `skillhub_selfhost/dist/`，启动时 FastAPI 通过 `importlib.resources` 定位并 mount serve，不依赖 `BASE_DIR`。

## 4. 数据库与连接配置

默认使用 `{BASE_DIR}/metadata.db` 作为 SQLite 数据库。用户可通过环境变量自定义：

| 环境变量 | 说明 | 默认值 |
|---|---|---|
| `SKILLHUB_DB_URL` | 数据库连接串 | `sqlite://metadata.db` |
| `SKILLHUB_SECRET_KEY` | JWT 签名密钥（留空自动生成并持久化） | 随机生成 + 持久化到 `{BASE_DIR}/.secret` |
| `SKILLHUB_HOST` | 监听地址 | `0.0.0.0` |
| `SKILLHUB_PORT` | 监听端口 | `8000` |
| `SKILLHUB_SKILLS_DIR` | skill 存储根目录 | `{BASE_DIR}/skills` |

环境变量优先级低于 CLI 参数。

## 5. 数据模型

### User

```python
class User(Model):
    id = UUIDField(pk=True)
    username = CharField(max_length=64, unique=True, index=True)
    password_hash = CharField(max_length=256)
    status = CharField(max_length=16, default="pending")  # pending | active | disabled
    is_admin = BooleanField(default=False)
    created_at = DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"
```

**状态流转：**

```
注册 → pending → 管理员审批 → active
                          ↓
                       disabled（管理员封禁/驳回）
```

- 管理员通过 `admin-init` 创建时为 `active`
- 管理员通过 Web 界面创建用户时也为 `active`
- 被封禁用户的 skill 继续可浏览/下载，但列表页打标记"作者已被封禁"，不能上传新版本

### Skill

```python
class Skill(Model):
    id = UUIDField(pk=True)
    name = CharField(max_length=128, unique=True, index=True)  # 全局唯一
    display_name = CharField(max_length=256)
    description = TextField()
    tags = JSONField(default=[])
    author: ForeignKeyRelation[User]
    download_count = IntField(default=0)
    created_at = DatetimeField(auto_now_add=True)
    updated_at = DatetimeField(auto_now=True)

    class Meta:
        table = "skills"
```

### SkillVersion

```python
class SkillVersion(Model):
    id = UUIDField(pk=True)
    skill: ForeignKeyRelation[Skill]
    version = CharField(max_length=32)           # semver, 如 "1.0.0"
    release_notes = TextField(null=True)
    file_size = IntField()                       # 字节
    created_at = DatetimeField(auto_now_add=True)

    class Meta:
        table = "skill_versions"
        unique_together = ("skill_id", "version")
```

### DownloadLog

```python
class DownloadLog(Model):
    id = UUIDField(pk=True)
    skill: ForeignKeyRelation[Skill]
    version = CharField(max_length=32)
    downloaded_at = DatetimeField(auto_now_add=True)

    class Meta:
        table = "download_logs"
```

用于支撑首页"本周热门"排序（按最近 7 天下载量降序）。

## 6. 存储模型

```
{SKILLS_DIR}/{username}/{skill_name}/{version}/
```

- `skill_name` 字符集：`[a-zA-Z0-9][a-zA-Z0-9_.-]*`，最长 128 字符，不允许以 `-`、`.`、`_` 开头
- `username` 同理，注册时校验
- `version` 严格 semver `MAJOR.MINOR.PATCH`，正则 `^\d+\.\d+\.\d+$`
- 上传时前端打包整个 skill 目录为 `tar.gz`，后端解压后**立即删除**原始 tar.gz，不额外存储
- `file_size` 记录的是 tar.gz 包文件大小（`len(file_content)`）
- 删除整个 skill 时移除对应目录 + DB 记录
- 删除单个版本时移除对应版本目录 + 版本记录，若该 skill 无剩余版本则连带删除 skill 记录及目录
- 转移时重命名 `skills/{from_user}/{skill_name}` → `skills/{to_user}/{skill_name}`，更新 DB 外键

## 7. API 设计

### 通用约定

**错误响应格式**（FastAPI 默认）：

```json
{"detail": "skill 名称已被占用"}
```

**分页响应格式：**

```json
{
    "items": [...],
    "total": 100,
    "page": 1,
    "size": 20
}
```

可选参数 `?page=1&size=20`，默认 `page=1`、`size=20`，最大 `size=100`。

### 认证 API

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| POST | `/api/auth/register` | 匿名 | 注册，status=pending |
| POST | `/api/auth/login` | 匿名 | 登录，返回 `{access_token, refresh_token}` |
| POST | `/api/auth/refresh` | 匿名 | 刷新，返回新的 `{access_token, refresh_token}` |
| GET | `/api/auth/me` | Bearer | 当前用户信息 |

**请求/响应格式：**

```
POST /api/auth/register
Body:   {"username": "alice", "password": "secret123"}
Response: (204 No Content)

POST /api/auth/login
Body:   {"username": "alice", "password": "secret123"}
Response: {"access_token": "eyJ...", "refresh_token": "eyJ..."}

POST /api/auth/refresh
Body:   {"refresh_token": "eyJ..."}
Response: {"access_token": "eyJ...", "refresh_token": "eyJ..."}

GET /api/auth/me
Response: {"id": "uuid", "username": "alice", "status": "active", "is_admin": false, "created_at": "2026-09-28T10:00:00Z"}
```

**Token 策略：**
- `access_token` 15 分钟，`refresh_token` 7 天
- 均为无状态 JWT，不存 DB
- `/api/auth/refresh` 传入 `refresh_token`，校验通过后签发全新的 access + refresh pair，旧 token 自然过期淘汰
- 无主动吊销机制；需要全量失效时改 `SKILLHUB_SECRET_KEY` 重启服务

**登录校验：**
- `status=pending` 用户登录 → 返回 403 `{"detail": "账号尚未通过审批，请联系管理员"}`
- `status=disabled` 用户登录 → 返回 403 `{"detail": "账号已被禁用"}`
- 用户名或密码错误 → 返回 401 `{"detail": "用户名或密码错误"}`

### 技能 API（匿名）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/skills/` | 列表，支持 `?q=搜索&tag=python&sort=downloads|weekly|newest&page=1&size=20` |
| GET | `/api/skills/{name}/` | 详情，含版本列表（`?version=1.0.0` 指定默认展示版本，缺省最新版） |
| GET | `/api/skills/{name}/readme` | 返回 SKILL.md 原始内容（默认最新版） |
| GET | `/api/skills/{name}/readme?version=1.0.0` | 返回指定版本 SKILL.md 内容 |
| GET | `/api/skills/{name}/download` | 下载最新版 tar.gz（Response header: `Content-Disposition: attachment; filename="xxx-v1.2.0.tar.gz"`） |
| GET | `/api/skills/{name}/download?version=1.0.0` | 下载指定版本 |

排序参数说明：

| sort | 含义 | 数据来源 |
|---|---|---|
| `downloads`（默认） | 总下载量降序 | `skill.download_count` |
| `weekly` | 最近 7 天下载量降序 | `download_logs` 表聚合 |
| `newest` | 创建时间降序 | `skill.created_at` |

**响应格式：**

```
GET /api/skills/
Response:
{
    "items": [
        {
            "name": "my-linter",
            "display_name": "My Linter",
            "description": "一个Python代码检查工具",
            "author": {"username": "alice", "status": "active"},
            "latest_version": "1.2.0",
            "tags": ["python", "linter"],
            "download_count": 12340,
            "created_at": "2026-09-20T10:00:00Z",
            "updated_at": "2026-09-28T10:00:00Z"
        }
    ],
    "total": 100,
    "page": 1,
    "size": 20
}
```

`author.status` 用于前端判断是否显示"作者已被封禁"标记。

- 多标签过滤为 **AND** 语义：`?tag=python&tag=linter` 只返回同时拥有二者的 skill
- 单标签过滤为 OR 语义（等同于单个 `?tag=python`）
- `?author=me` 特殊值 → 后端解析为当前已登录用户

```
GET /api/skills/{name}/
Response:
{
    "name": "my-linter",
    "display_name": "My Linter",
    "description": "一个Python代码检查工具",
    "author": {"username": "alice", "status": "active"},
    "tags": ["python", "linter"],
    "download_count": 12340,
    "created_at": "2026-09-20T10:00:00Z",
    "updated_at": "2026-09-28T10:00:00Z",
    "versions": [
        {"version": "1.2.0", "release_notes": "修复bug", "file_size": 24576, "created_at": "2026-09-28T10:00:00Z"},
        {"version": "1.1.0", "release_notes": null, "file_size": 22000, "created_at": "2026-09-25T10:00:00Z"}
    ]
}
```

`?version=x.y.z` 参数标识前端当前选中展示的版本（联动 SKILL.md 渲染）。

```
GET /api/skills/{name}/readme
Response: (text/plain) SKILL.md 原始内容
```

### 技能 API（需登录）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/skills/` | 上传 skill（multipart: tar.gz + metadata JSON） |
| DELETE | `/api/skills/{name}/` | 删除整个 skill（仅作者，需二次确认） |
| DELETE | `/api/skills/{name}/versions/{version}` | 删除单个版本（仅作者），若为最后一个版本则删除 skill |
| PATCH | `/api/skills/{name}/transfer` | 转移所有权 `{"target_user": "bob"}`（作者或管理员） |

**转移逻辑：**
- 作者或管理员可转移
- 目标用户名需存在且 `status=active`
- 用户不存在 → 400 `{"detail": "用户 bob 不存在"}`
- 转移成功后移动文件目录 + 更新 DB `author_id`

### 管理员 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/admin/users/` | 用户列表 `?status=pending&page=1&size=20` |
| POST | `/api/admin/users/` | 管理员直接创建用户 `{"username": "...", "password": "..."}` |
| PATCH | `/api/admin/users/{id}/approve` | 审批通过，status → active |
| PATCH | `/api/admin/users/{id}/disable` | 禁用用户，status → disabled（不可禁管理员） |
| PATCH | `/api/admin/users/{id}/enable` | 启用已禁用用户，status → active |

管理员创建的初始密码由管理员设定，创建即 `status=active`。

**响应格式：**

```
GET /api/admin/users/
Response:
{
    "items": [
        {"id": "uuid", "username": "alice", "status": "active", "is_admin": false, "created_at": "2026-09-20T10:00:00Z"}
    ],
    "total": 5,
    "page": 1,
    "size": 20
}

POST /api/admin/users/
Body:   {"username": "newuser", "password": "pass123"}
Response: {"id": "uuid", "username": "newuser", "status": "active", "is_admin": false, "created_at": "..."}
```

### 我的技能

已登录用户通过 `GET /api/skills/?author=me` 获取自己的所有技能。

## 8. 上传逻辑

1. 前端打包 skill 目录为 `tar.gz`
2. 请求 `POST /api/skills/`，multipart body 包含：
   - `file`: tar.gz
   - `display_name`: str
   - `description`: str
   - `tags`: JSON array
   - `version`: str（semver，留空则自动 bump patch，如 1.2.0 → 1.2.1）
   - `release_notes`: str（可选）
3. 后端校验：
   - 用户已登录且 `status=active`
   - `skill_name` 从 tar.gz 根目录名提取，校验字符集 `[a-zA-Z0-9][a-zA-Z0-9_.-]*`、最长 128 字符
   - skill 名全局唯一 → 新 skill 直接创建
   - skill 名已存在 → 仅作者可追加版本（其他用户提示重名）
   - `version` 严格 semver `^\d+\.\d+\.\d+$`，在该 skill 下无重复
   - 版本号留空 → 新 skill 默认 `1.0.0`，已有 skill 自动 bump patch（`1.2.0` → `1.2.1`）
   - tar.gz 结构合法（至少包含 `SKILL.md`，根目录名提取为 `skill_name`）
4. 校验通过：写入 DB 记录 + 解压到 `skills/{user}/{name}/{version}/`，`file_size` 记录 tar.gz 原始大小
5. 解压完成后删除 tar.gz 原始文件
6. 校验失败：返回 4xx + `{"detail": "..."}`
   - 重名（非作者）→ 409 `{"detail": "skill 名称已被占用"}`
   - 版本重复 → 409 `{"detail": "版本 xxx 已存在"}`
   - 缺少 SKILL.md → 400 `{"detail": "tar.gz 内必须包含 SKILL.md"}`
   - 命名不合法 → 400 `{"detail": "skill 名称不合法，需以字母或数字开头，仅含字母、数字、连字符、下划线、点号"}`
   - 版本格式错误 → 400 `{"detail": "版本号格式不正确，请使用 x.y.z 格式"}`

## 9. 前端设计

### 状态管理

- React Context + useReducer
- AuthContext：存储当前用户信息、token、登录/登出方法
- Token 存 localStorage，页面刷新后从 localStorage 恢复

### 页面路由

| 路由 | 页面 | 鉴权 |
|---|---|---|
| `/` | 首页：排行榜 / 搜索 / 标签过滤 | 匿名 |
| `/skills/{name}` | 详情页 | 匿名 |
| `/login` | 登录页 | 匿名 |
| `/register` | 注册页 | 匿名 |
| `/my` | 我的技能：列表 + 管理 | 需登录 |
| `/upload` | 上传页（拖拽 tar.gz） | 需登录 |
| `/admin` | 后台管理：用户审批/创建 | 管理员 |

### 首页 `/`

```
┌─────────────────────────────────────────────────────────────┐
│  🔍 [________搜索 skill 名称或描述________]    [登录|我的]   │
│─────────────────────────────────────────────────────────────│
│  总下载 · 本周热门 · 最新上传                                │
│─────────────────────────────────────────────────────────────│
│  # │ Skill          │ 作者   │ 版本   │ 标签   │ 下载     │
│─────────────────────────────────────────────────────────────│
│  1 │ my-linter      │ alice  │ v1.2.0 │ python │ 12,340  │
│    │ 一个Python代码  │        │        │ linter │         │
│  2 │ git-hooks      │ bob    │ v0.3.1 │ git    │ 5,423   │
│    │ 自动化 git 钩子 │        │        │        │         │
│─────────────────────────────────────────────────────────────│
│  tags: All · python · linter · testing · git · ...          │
├─────────────────────────────────────────────────────────────│
│                    < 1 2 3 ... 10 >                         │
└─────────────────────────────────────────────────────────────┘
```

- 默认按**总下载**降序排列
- 三个排序 tab 切换
- 标签行悬浮点击过滤
- 被封禁作者的行显示"🚫 作者已被封禁"标记

### 登录页 `/login`

```
┌──────────────────────────────────────────┐
│                                          │
│           🔑 登录 skillhub              │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │ 用户名                    [___] │    │
│  │ 密码                      [___] │    │
│  │                                  │    │
│  │ [      登  录       ]           │    │
│  └──────────────────────────────────┘    │
│                                          │
│  还没有账号？[立即注册]                   │
└──────────────────────────────────────────┘
```

### 注册页 `/register`

```
┌──────────────────────────────────────────┐
│                                          │
│           📝 注册 skillhub              │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │ 用户名                    [___] │    │
│  │ 密码                      [___] │    │
│  │ 确认密码                  [___] │    │
│  │                                  │    │
│  │ 提交后需等待管理员审批            │    │
│  │ [      注  册       ]           │    │
│  └──────────────────────────────────┘    │
│                                          │
│  已有账号？[立即登录]                     │
└──────────────────────────────────────────┘
```

- 注册成功 → 提示"已提交，等待管理员审批" → 回到首页（匿名状态）

### 详情页 `/skills/{name}`

```
┌─────────────────────────────────────────────────────────────┐
│  ← 返回        my-linter @ 1.2.0     [ 下载 tar.gz ]        │
│─────────────────────────────────────────────────────────────│
│  SKILL.md 渲染内容                       │  安装命令         │
│                                          │  curl -O http://  │
│  # My Linter                             │  host:8000/api/   │
│  一个 Python 代码检查工具...              │  skills/my-linter│
│                                          │  /download?version│
│  代码块、列表等 Markdown 正常渲染         │  =1.2.0          │
│  ...                                     │                   │
│                                          │  [ 📋 复制 ]      │
│                                          │                   │
│                                          │  基本信息         │
│                                          │  作者: alice      │
│                                          │  大小: 24 KB      │
│                                          │  下载: 1,234 次   │
│                                          │  标签: python...  │
│                                          │                   │
│                                          │  历史版本         │
│                                          │  ○ 1.2.0 (最新)  │
│                                          │  ○ 1.1.0    [下] │
│                                          │  ○ 1.0.0    [下] │
│                                          │      [ 删 ]       │
│                                          │                   │
│                                          │  [ 下载 tar.gz ]  │
└─────────────────────────────────────────────────────────────┘
```

- 默认展示最新版 SKILL.md，版本切换联动左右两侧
- 右侧 curl 命令含一键复制
- 作者登录后可在历史版本列表中看到单版本删除按钮（删最后一个版本 = 删整个 skill）
- 未登录：下载正常可用

### 上传页 `/upload`

```
┌─────────────────────────────────────────────────────────────┐
│  ← 返回我的技能                                              │
│─────────────────────────────────────────────────────────────│
│  上传新 Skill                                               │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                     │    │
│  │              📦  拖拽 tar.gz 到此处                   │    │
│  │                或 点击选择文件                        │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  skill 名称     my-linter          （从目录名自动提取）       │
│  展示名称       My Linter                                     │
│  描述           [___________________________]                │
│  标签           [python ×] [linter ×] [+ 添加]               │
│  版本           [________] （留空自动追加小版本）   │
│  更新说明       [___________________________]                │
│                                                             │
│  [        上  传        ]                                   │
└─────────────────────────────────────────────────────────────┘
```

- 版本号留空 → 自动 bump patch（如 1.2.0 → 1.2.1）
- 新 skill（名称未占用）→ 不填则默认 `1.0.0`
- 上传成功 → 跳转 `/my`
- 重名（非作者）→ `skill 名称已被占用，请联系管理员`
- 版本重复 → `该版本已存在`
- 缺少 SKILL.md → `tar.gz 内必须包含 SKILL.md`

### 我的 `/my`

```
┌─────────────────────────────────────────────────────────────────┐
│  [← 返回首页]                           [alice] [上传新 Skill]  │
│─────────────────────────────────────────────────────────────────│
│  我的 Skills (3)                                                │
│─────────────────────────────────────────────────────────────────│
│  ┌─ my-linter ───────────────────[删除] [转移]────────────────┐ │
│  │ v1.2.0 (latest) · python, linter · 总下载 12,340          │ │
│  │ v1.1.0                                                     │ │
│  │ v1.0.0                                                     │ │
│  │ [  追加新版本  ]                                           │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌─ test-gen ────────────────────[删除] [转移]────────────────┐ │
│  │ v2.0.0 (latest) · testing · 总下载 4,210                   │ │
│  │ [  追加新版本  ]                                           │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

- 删除整个 skill → 二次确认弹窗"确定删除 my-linter？此操作不可撤销。"，确认后删除所有版本 + 文件
- 转移 → 弹窗输入目标用户名，校验存在且 active，确认后转移
- 追加新版本 → 跳转上传页，skill 名自动填入

### 管理员 `/admin`

- 两个 tab：待审批 / 所有用户
- 顶部 [+ 创建用户] 按钮

**待审批：**

```
┌─────────────────────────────────────────────────────────────────┐
│  ┌─ bob ──────────────────────── 2026-09-28 10:23 ───────────┐ │
│  │                                         [通过] [驳回]      │ │
│  └────────────────────────────────────────────────────────────┘ │
```

**所有用户：**

```
  carol  ✅ 活跃    2026-09-27  [禁用]
  bob    🕐 待审批  2026-09-28  [通过] [驳回]
  alice  ✅ 活跃    2026-09-20  [禁用]
  dave   🚫 已禁用  2026-09-18  [启用]
  admin  👑 管理员  2026-09-18  -
```

**创建用户弹窗：**

```
  创建新用户
  ┌────────────────────┐
  │ 用户名      [___] │
  │ 密码        [___] │
  │                     │
  │ [  创  建  ]       │
  └────────────────────┘
```

- 管理员创建的用户自动 `status=active`，无需审批
- 驳回 → `status=disabled`
- 管理员自己不可被禁用
- 管理员不可删除用户（v1 不实现）

### API 客户端与 Token 管理

- 前端封装 `fetch` client，自动在请求头中附加 `Authorization: Bearer <access_token>`
- `access_token` 和 `refresh_token` 均存 localStorage
- **401 自动重试流程：**

```
请求返回 401
  → 尝试 POST /api/auth/refresh（body: {"refresh_token": "..."}）
    → 刷新成功：更新 localStorage 中的双 token，重试原请求
    → 刷新失败（refresh 也 401）：清空 localStorage token，跳转 /login
```

- 路由守卫：需登录的页面（`/my`、`/upload`）在 load 时检查 localStorage 是否有 token，无则重定向 `/login`；管理员页面额外检查 `user.is_admin`

### 全局 UI 规则

- 顶部导航栏：左侧 Logo/首页链接，右侧未登录显示[登录]，已登录显示[用户名][我的][退出]
- 匿名用户：写操作按钮置灰 + tooltip"请先登录"，点击跳转 `/login`
- 封禁用户登录后：仅可浏览，上传/删除/转移全部置灰
- Loading 状态：列表/详情使用 Skeleton 占位
- 空状态：列表为空时显示友好提示"还没有 skill，快来上传第一个吧"
- Toast 通知：操作成功/失败用 shadcn/ui Sonner toast，右上角弹出

### 技术约束

- shadcn/ui 组件全部本地引用，无 CDN
- Tailwind CSS 由 Vite 编译
- lucide-react 图标打包
- 字体使用系统字体栈：`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- 前端 `dist/` 打包在 wheel 内，FastAPI 通过包内路径 `importlib.resources` 定位并 mount serve
- SPA fallback：所有非 `/api/` 路由返回 `index.html`

## 10. 安全性

- 密码 bcrypt 哈希存储
- JWT 无状态，access_token 15 分钟，refresh_token 7 天
- 上传文件名校验，防止路径穿越（`../` 等）
- `skills_dir` 限制在 `BASE_DIR` 内，不允许配置为系统关键路径
- CORS 默认 `*`（内网场景），可通过环境变量 `SKILLHUB_CORS_ORIGINS` 配置
- 管理员 API 单独鉴权中间件，检查 `is_admin=True`
- tar.gz 解压大小限制（单个文件 50MB，总计 100MB）

## 11. 日志

- 使用 Python `logging` + `TimedRotatingFileHandler`
- 按天翻滚：`logs/skillhub-YYYY-MM-DD.log`
- 保留最近 30 天日志，自动清理
- 日志级别默认 INFO，可通过 `SKILLHUB_LOG_LEVEL` 环境变量调整
- uvicorn 的 access log 同时输出到文件和控制台

## 12. CLI 设计

```bash
skillhub-selfhost admin-init     # 交互式创建管理员（若 db 不存在则先创建）
skillhub-selfhost server start   # 自动初始化 + 启动 HTTP 服务
```

`server start` 启动流程：

1. 确定 `BASE_DIR = os.getcwd()`
2. 检查并创建 `{BASE_DIR}/metadata.db`（Tortoise ORM `generate_schemas()`）
3. 检查并创建 `{BASE_DIR}/skills/`
4. 检查并创建 `{BASE_DIR}/logs/`
5. 若 `{BASE_DIR}/.secret` 不存在，生成随机密钥写入
6. 从包内 `dist/` 路径挂载前端静态文件到根路径（SPA fallback）
7. 配置日志
8. `uvicorn.run()`

使用 `typer` 实现 CLI。

## 13. 打包结构

```
skillhub-selfhost/
├── skillhub_selfhost/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app 创建 + 生命周期
│   ├── cli.py                   # typer CLI
│   ├── config.py                # 配置读取（环境变量 + 参数）
│   ├── db.py                    # Tortoise ORM 初始化
│   ├── logging_config.py        # 日志配置
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── models.py            # User 模型
│   │   ├── router.py            # 认证 API
│   │   ├── service.py           # 登录/注册逻辑
│   │   └── dependencies.py      # get_current_user / get_admin 依赖
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── models.py            # Skill + SkillVersion + DownloadLog 模型
│   │   ├── router.py            # 技能 API
│   │   └── service.py           # 上传/下载/转移/删除逻辑
│   ├── admin/
│   │   ├── __init__.py
│   │   └── router.py            # 管理员 API
│   └── dist/                    # 前端构建产物（CI 自动生成）
│       ├── index.html
│       └── assets/
├── frontend/                    # React 源码（开发用，不入 wheel）
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx              # 路由
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx  # 认证状态
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── SkillDetail.tsx
│   │   │   ├── Upload.tsx
│   │   │   ├── MySkills.tsx
│   │   │   └── Admin.tsx
│   │   ├── components/
│   │   │   ├── Layout.tsx       # 全局导航栏
│   │   │   └── ...
│   │   └── api/
│   │       └── client.ts        # fetch 封装
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── package.json
├── pyproject.toml
└── README.md
```

`pyproject.toml` 中声明：

```toml
[project.scripts]
skillhub-selfhost = "skillhub_selfhost.cli:app"

[tool.setuptools.package-data]
skillhub_selfhost = ["dist/**"]
```

## 14. 待定项

| 项 | 说明 |
|---|---|
| 用户头像 | 前端根据用户名首字母生成纯色头像 |
| 密码复杂度 | 不做校验，由管理员自行约束 |
| 邮件通知 | 内网部署无邮件服务，审批结果通过 Web 界面查看 |
| 登录失败锁定 | 不做，内网场景恶意爆破概率低 |
| 修改密码 | v1 不做 |
| 删除用户 | v1 不做（仅支持禁用） |
| 客户端 CLI (`skillhub-cli`) | v1 不做，curl 一行够用 |