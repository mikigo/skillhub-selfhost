# SkillHub

一个自托管的 AI Agent 技能市场。帮助团队搜索、上传、版本管理和共享可复用的 AI 能力模块。

---

## 概述

AI Agent 通过可复用的模块（"技能"）获取领域知识和工具链集成能力。SkillHub 为组织内管理这些技能提供了自托管的私有仓库，类似于容器镜像仓库或包管理索引，但专为 AI Agent 的工作流设计。

---

## 功能

| 分类 | 说明 |
|----------|---------|
| 浏览与搜索 | 全文搜索、标签筛选、多维度排序（总下载数 / 24 小时热门 / 最新上传） |
| 上传 | 拖拽文件夹自动打包 ZIP，自动提取 SKILL.md frontmatter，支持版本号与更新说明 |
| 版本管理 | 多版本并存、自由切换、作者可删除旧版本 |
| 用户系统 | 注册需管理员审批、BCrypt 密码加密、JWT 令牌 + 刷新令牌 |
| 权限控制 | 管理员与普通用户角色分离、技能所有权保护、技能转让 |
| 国际化 | 中英文切换、支持通过配置文件设置默认语言、运行时可切换 |
| 主题切换 | 亮色与暗色模式、跟随系统偏好自动选择 |
| 品牌定制 | 自定义 Logo、Favicon、站点标题，通过配置文件设置 |
| Markdown 渲染 | 完整支持 GFM，包括表格、围栏代码块和 frontmatter 展示 |
| 管理面板 | 用户审批、禁用/启用、创建用户、按状态筛选 |

### 截图展示

<p align="center">
  <img src="website/public/dark.png" alt="暗色主题" width="32%">
  <img src="website/public/white.png" alt="亮色主题" width="32%">
  <img src="website/public/login.png" alt="登录页" width="32%">
</p>

---

## 快速开始

### 安装

```bash
pip install skillhub-selfhost
```

要求 Python &ge; 3.8。

### 创建管理员

```bash
skillhub-selfhost admin-init
```

### 启动服务

```bash
skillhub-selfhost server-start
```

在浏览器中访问 `http://localhost:8000`。

自定义监听地址与端口：

```bash
skillhub-selfhost server-start --host 0.0.0.0 --port 8080
```

---

## 配置

在工作目录下创建 `config.json` 文件。所有字段均为可选，未配置时使用默认值。

### 完整示例

```json
{
  "db_url": "postgres://skillhub:password@localhost:5432/skillhub",
  "default_lang": "zh",
  "logo_text": "MySkillHub",
  "logo": "logo.png",
  "favicon": "favicon.ico"
}
```

### 配置项说明

| 字段 | 类型 | 默认值 | 说明 |
|-------|------|---------|-------------|
| `db_url` | string | `sqlite://{工作目录}/metadata.db` | 数据库连接串（详见数据库配置） |
| `default_lang` | string | `en` | 默认界面语言（`en` 或 `zh`） |
| `logo_text` | string | `SkillHub` | 导航栏显示的文字 |
| `logo` | string | — | 放置于 config.json 同目录下的图片文件名，显示在 logo_text 左侧 |
| `favicon` | string | — | 浏览器标签页图标文件名，放置于 config.json 同目录下；未配置时使用内置默认图标 |

### 数据库配置

SkillHub 使用 [Tortoise ORM](https://tortoise.github.io/)，支持 SQLite 和 PostgreSQL。

#### SQLite（默认）

无需额外配置，适用于个人或小团队。

```json
{ "db_url": "sqlite://metadata.db" }
```

| 格式 | 说明 |
|--------|-------------|
| `sqlite://metadata.db` | 相对于工作目录 |
| `sqlite:///absolute/path/metadata.db` | 绝对路径（三个斜杠） |
| `sqlite://:memory:` | 内存数据库（重启后数据丢失，仅测试用途） |

#### PostgreSQL（生产环境推荐）

安装 asyncpg 驱动：

```bash
pip install asyncpg
```

连接串格式：`postgres://用户名:密码@主机:端口/数据库名`

```json
{ "db_url": "postgres://skillhub:password@localhost:5432/skillhub" }
```

含连接池参数：

```json
{ "db_url": "postgres://skillhub:password@10.0.0.5:5432/skillhub?minsize=5&maxsize=20" }
```

注意事项：
- 需提前创建数据库（`CREATE DATABASE skillhub;`），表结构由应用启动时自动生成。
- 确保配置的用户拥有 schema 读写权限。
- 生产环境建议使用专用数据库用户。

#### 对比

| 维度 | SQLite | PostgreSQL |
|-----------|--------|------------|
| 安装复杂度 | 零配置 | 需安装并运行 PostgreSQL 服务 |
| 并发能力 | 单写者，读并发有限 | 高并发读写 |
| 数据可靠性 | 单文件，备份简单 | WAL 日志，支持崩溃恢复 |
| 适用场景 | 个人 / 小团队（&lt; 10 人） | 团队协作 / 生产环境 |
| 迁移成本 | 无 | 仅切换配置；数据需手动迁移 |

### 配置优先级

1. **环境变量**（最高优先级）
2. **`config.json`**
3. **内置默认值**（最低优先级）

环境变量会覆盖 `config.json` 中的同名字段。品牌定制字段（`logo_text`、`logo`、`favicon`）仅支持 `config.json` 方式。

### 环境变量

| 变量 | 对应配置 | 默认值 | 说明 |
|----------|---------|---------|-------------|
| `SKILLHUB_HOST` | — | `0.0.0.0` | 监听地址 |
| `SKILLHUB_PORT` | — | `8000` | 监听端口 |
| `SKILLHUB_DB_URL` | `db_url` | `sqlite://{工作目录}/metadata.db` | 数据库连接串 |
| `SKILLHUB_SECRET_KEY` | — | 自动生成 | JWT 签名密钥，生产环境必须固定 |
| `SKILLHUB_SKILLS_DIR` | — | `{工作目录}/skills` | 技能文件存储目录 |
| `SKILLHUB_LOG_LEVEL` | — | `INFO` | 日志级别（`DEBUG` / `INFO` / `WARNING` / `ERROR`） |

---

## 生产环境部署

```bash
# 1. 准备 config.json（使用 PostgreSQL）
cat > config.json << EOF
{
  "db_url": "postgres://skillhub:password@localhost:5432/skillhub",
  "default_lang": "zh",
  "logo_text": "MySkillHub",
  "logo": "logo.png",
  "favicon": "favicon.ico"
}
EOF

# 2. 生成持久化的 JWT 密钥
export SKILLHUB_SECRET_KEY=$(openssl rand -hex 32)

# 3. 启动服务
skillhub-selfhost server-start --port 8000
```

注意事项：
- `SKILLHUB_SECRET_KEY` 必须持久化且保密；密钥变更会导致所有活跃会话失效。
- 将 `SKILLHUB_SKILLS_DIR` 挂载到持久化存储（Docker 卷、NFS 或云存储）。
- 前端已内嵌于 Python 包中，无需额外 Web 服务器。
- 如需 HTTPS，在应用前部署反向代理（Nginx、Caddy）以终止 TLS。

---

## 技术架构

| 层级 | 技术 |
|-------|------------|
| API 框架 | FastAPI (Python) |
| ORM | Tortoise ORM + SQLite / PostgreSQL |
| 认证 | BCrypt + PyJWT |
| CLI | Typer |
| 前端框架 | React 18 + TypeScript |
| 构建工具 | Vite |
| UI 组件 | shadcn/ui (New York) + Tailwind CSS 3 |
| 图标 | Lucide React |
| Markdown | react-markdown + remark-gfm |
| 国际化 | 自定义 React Context + localStorage 持久化 |
| 主题 | next-themes |

---

## 开发

```bash
# 后端（热重载）
uvicorn skillhub_selfhost.main:create_app --factory --reload

# 前端
cd frontend
npm install
npm run dev          # 开发服务器，支持热更新
npm run build        # 生产构建 → skillhub_selfhost/dist/
```

---

## 链接

- [项目网站](https://mikigo.github.io/skillhub-selfhost/)
- [GitHub 仓库](https://github.com/mikigo/skillhub-selfhost)

---

## 许可证

Apache-2.0