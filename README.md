# SkillHub

一个自托管的 AI Skill 集市。给你的 AI agent 装上插件系统 &mdash; 搜索、上传、分享，团队内部一站搞定。

> *"Skills are reusable capabilities for AI agents."* &mdash; 同行的广告词我们直接抄过来了。

---

## 为什么需要 SkillHub？

AI agent 越来越能打，但也越来越能吃上下文。每次对话都得手把手教会它怎么做某件事？太累了。Skill 解决的就是这件事 &mdash; 把领域知识、工具链、最佳实践打包成一个可复用的模块，agent 一行命令就能装上。

SkillHub 是给你自己的团队 / 公司搭建的私有 skill 仓库。像 npm 之于包管理，像 Docker Hub 之于镜像 &mdash; 只不过你的 target audience 是一群 YAML-slinging, markdown-writing 的 AI agents。

---

## 功能

| 模块 | 说明 |
|------|------|
| 🔍 浏览与搜索 | 按名称搜索、标签筛选、多维度排序（总下载 / 本周热门 / 最新上传） |
| 📦 上传 | 拖拽文件夹自动打包 ZIP，从 `SKILL.md` 提取 frontmatter，支持版本号与更新说明 |
| 🔄 版本管理 | 多版本并存，随时切换，作者可删除旧版本 |
| 👤 用户系统 | 注册需管理员审批，BCrypt 密码加密，JWT 认证 + refresh token |
| 🔐 权限控制 | 普通用户 / 管理员分离，skill 归属权保护，支持 skill 转让 |
| 🎨 界面 | React + shadcn/ui + Tailwind，暗色模式支持，响应式布局 |
| 📝 Markdown | `SKILL.md` 完整渲染，GFM 表格、代码高亮、frontmatter 展示 |
| 🛠 管理面板 | 用户审批、禁用/启用、管理员创建用户 |

---

## 快速开始

### 安装

```bash
pip install skillhub-selfhost
```

> 需要 Python &ge; 3.8。

### 创建管理员

```bash
skillhub-selfhost admin-init
```

交互式输入用户名和密码。

### 启动服务

```bash
skillhub-selfhost server-start
```

打开浏览器访问 `http://localhost:8000`。

如需自定义监听地址或端口：

```bash
skillhub-selfhost server-start --host 0.0.0.0 --port 8080
```

详细的数据库、品牌等配置见下方 **配置详解**。

---

## 开发

```bash
# 后端
pip install -e ".[dev]"
uvicorn skillhub_selfhost.main:create_app --factory --reload

# 前端
cd frontend
npm install
npm run dev          # 开发模式（热更新）
npm run build        # 生产构建 → ../skillhub_selfhost/dist/
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI (Python) |
| ORM | Tortoise ORM + SQLite / PostgreSQL |
| 认证 | BCrypt + PyJWT |
| CLI | Typer |
| 前端框架 | React 18 + TypeScript |
| 构建 | Vite |
| UI | shadcn/ui (New York) + Tailwind CSS 3 |
| Markdown | react-markdown + remark-gfm |

---

## 配置详解

在启动目录下创建 `config.json` 文件。所有字段均为可选，未配置时使用默认值。

### 完整配置示例

```json
{
  "db_url": "sqlite://metadata.db",
  "logo_text": "MySkillHub",
  "logo": "logo.png",
  "favicon": "favicon.ico"
}
```

### 配置项说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `db_url` | string | `sqlite://{启动目录}/metadata.db` | 数据库连接串，见下方数据库配置 |
| `logo_text` | string | `SkillHub` | 导航栏左上角显示的文字 |
| `logo` | string | 无 | 显示在 logo_text 左边的图片文件名，图片放在 config.json 同目录下 |
| `favicon` | string | 无 | 浏览器标签页图标文件名，图片放在 config.json 同目录下。不配置则不显示 favicon |

### 数据库配置

SkillHub 使用 [Tortoise ORM](https://tortoise.github.io/)，支持 SQLite 和 PostgreSQL（通过 asyncpg 驱动）。`db_url` 按标准数据库连接串格式书写。

#### SQLite（默认）

最简单的方案，无需额外安装任何东西，适合个人或小团队使用。

```json
{
  "db_url": "sqlite://metadata.db"
}
```

连接串格式：`sqlite://{文件路径}`。

| 写法 | 说明 |
|------|------|
| `sqlite://metadata.db` | 文件放在启动目录下 |
| `sqlite:///absolute/path/metadata.db` | 绝对路径（注意三个斜杠） |
| `sqlite://:memory:` | 内存数据库（重启后数据丢失，仅限测试） |

#### PostgreSQL（推荐生产环境）

需要安装 PostgreSQL 客户端库和 asyncpg 驱动：

```bash
pip install asyncpg
```

连接串格式：`postgres://用户名:密码@主机:端口/数据库名`

```json
{
  "db_url": "postgres://skillhub:your_password@localhost:5432/skillhub"
}
```

更多连接参数示例：

```json
{
  "db_url": "postgres://skillhub:your_password@10.0.0.5:5432/skillhub?minsize=5&maxsize=20"
}
```

注意：
- 数据库需提前创建（`CREATE DATABASE skillhub;`），表结构由应用自动生成
- schema 读写权限需赋予配置的用户
- 建议生产环境使用单独的只读/读写用户

#### 对比

| 维度 | SQLite | PostgreSQL |
|------|--------|------------|
| 安装复杂度 | 零配置 | 需安装并运行 PostgreSQL 服务 |
| 并发能力 | 单写者，读并发有限 | 高并发读写 |
| 数据可靠性 | 单文件，易备份 | WAL 日志，崩溃恢复 |
| 适用场景 | 个人 / 小团队（< 10 人） | 团队协作 / 生产环境 |
| 迁移成本 | 无 | 无（配置项切换即可，数据需手动迁移） |

### 配置优先级

配置来源按优先级从高到低：

1. **环境变量**（`SKILLHUB_DB_URL` 等）
2. **`config.json` 文件**
3. **默认值**

环境变量会覆盖 `config.json` 中的同名配置。只有 `logo_text`、`logo`、`favicon` 仅支持 `config.json` 方式（不需要通过环境变量暴露）。

### 环境变量（可选）

| 变量 | 相当于 config.json | 默认值 | 说明 |
|------|-----|--------|------|
| `SKILLHUB_HOST` | &mdash; | `0.0.0.0` | 监听地址 |
| `SKILLHUB_PORT` | &mdash; | `8000` | 监听端口 |
| `SKILLHUB_DB_URL` | `db_url` | `sqlite://{cwd}/metadata.db` | 数据库连接串 |
| `SKILLHUB_SECRET_KEY` | &mdash; | 自动生成 | JWT 签名密钥，生产环境必须固定 |
| `SKILLHUB_SKILLS_DIR` | &mdash; | `{cwd}/skills` | skill 文件存储目录 |
| `SKILLHUB_LOG_LEVEL` | &mdash; | `INFO` | 日志级别（DEBUG / INFO / WARNING / ERROR） |

---

## 部署到生产

```bash
# 1. 准备 config.json
cat > config.json << EOF
{
  "db_url": "postgres://skillhub:your_password@localhost:5432/skillhub",
  "logo_text": "MySkillHub",
  "logo": "logo.png",
  "favicon": "favicon.ico"
}
EOF

# 2. 固定 JWT 密钥（防止重启后用户登录失效）
SKILLHUB_SECRET_KEY=$(openssl rand -hex 32)

# 3. 启动
SKILLHUB_SECRET_KEY=$SKILLHUB_SECRET_KEY \
skillhub-selfhost server-start --port 8000
```

4 点注意事项：
- `SKILLHUB_SECRET_KEY` 必须固定且保密，建议使用 `openssl rand -hex 32` 生成
- `SKILLHUB_SKILLS_DIR` 挂载到持久化存储（Docker volume / NFS）
- 前端已内嵌到 Python 包中，单进程即开即用，无需 Nginx 反向代理即可直接对外服务
- 如需 HTTPS，在前端加一层 Nginx 或 Caddy 做 TLS 终止

---

## License

Apache-2.0