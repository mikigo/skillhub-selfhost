# SkillHub-SelfHost

一个自托管的 AI Agent 技能市场。帮助团队搜索、上传、版本管理和共享可复用的 AI 能力模块。

---

## 概述

AI Agent 通过可复用的模块（"技能"）获取领域知识和工具链集成能力。SkillHub 为组织内管理这些技能提供了自托管的私有仓库，类似于容器镜像仓库或包管理索引，但专为 AI Agent 的工作流设计。

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

## 功能

| 分类 | 说明 |
|----------|---------|
| 浏览与搜索 | 全文搜索、标签筛选、多维度排序（总下载数 / 24 小时热门 / 最新上传） |
| 上传 | 拖拽文件夹自动打包 ZIP，展示名称与标签自动取自 SKILL.md frontmatter，支持版本号与更新说明 |
| 从 GitLab 导入 | 只保存仓库指针（地址 + 分支 + 路径），描述自动取自 SKILL.md，内容实时拉取 |
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
  <img src="website/public/home.png" alt="主页" width="32%">
  <img src="website/public/upload.png" alt="上传" width="32%">
  <img src="website/public/myskill.png" alt="我的技能" width="32%">
</p>
<p align="center">
  <img src="website/public/dark.png" alt="暗色主题" width="32%">
  <img src="website/public/white.png" alt="亮色主题" width="32%">
</p>

---

## 技能的名字与地址

**技能名只在作者内唯一**：两个用户可以各有一个叫 `foo` 的 skill，但同一个人不能有两个 `foo`（再次上传同名会变成追加版本）。所以定位一个 skill 必须同时给出作者名，页面与 API 的地址都带上作者：

| | 地址 |
|---|---|
| 详情页 | `/skills/<用户名>/<技能名>` |
| 详情 / README / 下载 / 删除 / 转让 API | `/api/skills/<用户名>/<技能名>/...` |

安装命令因此形如：

```bash
curl -sSL -o /tmp/skill.zip https://your-skillhub/api/skills/alice/foo/download && unzip -o /tmp/skill.zip -d ~/.agents/skills/
```

首页列表在展示名后面用灰字标出作者；如果这个 skill 是通过「原作者」字段记着转手来源的，会显示成 `alice[原作者]`。

用户名的字符集是有限制的：**字母、数字以及 `-` `_` `.`，且必须以字母或数字开头**。这条规则只在注册（含管理员建号）时校验，见下方已知限制。

### 已知限制

- 老链接 `/skills/<技能名>` **直接失效**，没有重定向 —— 请用带作者名的新地址
- 用户名校验只对新账号生效：**存量账号**如果用户名含上面字库之外的字符（尤其是 `/`），它的详情页链接拼不出来，需要改名或重新建号
- 首页上同名的 skill 会并排出现两条，只能靠后面那串 `用户名[原作者]` 区分

---

## 从 GitLab 导入技能

上传页有「本地 ZIP」和「GitLab」两个 tab。GitLab 方式只需填 3 项：

| 字段 | 说明 |
|----------|---------|
| GitLab 地址 | 项目主页地址，如 `https://gitlab.com/group/proj`。`.git` 后缀、尾部 `/`，以及浏览器里复制的 `/-/tree/main/xxx` 形式的地址都能识别 |
| 分支 | 如 `main` |
| 技能路径 | 仓库内的相对路径，如 `skills/foo`；留空表示技能就在仓库根目录 |

提交后后端会读取该路径下的 `SKILL.md`，用 frontmatter 自动填充各字段（表单里没有可编辑的输入框）：

- **技能名** = 路径最后一段（路径留空时取项目名），与作者共同构成唯一标识
- **显示名** = frontmatter 的 `name`，缺失时回退为技能名
- **描述** = frontmatter 的 `description`
- **标签** = frontmatter 的 `tags`

这类技能**没有版本概念**：详情页每次打开都实时读取仓库中最新的 `SKILL.md`，不做任何缓存；下载同样由后端实时从 GitLab 拉取归档、重新打包成 `<技能名>/...` 后返回（所以安装命令里的 `curl` 只会访问你的 SkillHub，不需要能连到 GitLab）。因此 GitLab 上的改动无需回到 SkillHub 重新上传，刷新详情页即可看到。

### 已知限制

- 仅支持公开仓库（或内网免认证），**不支持私有仓库，也不支持配置访问 token**
- 不支持自签名 TLS 证书的 GitLab
- 假定 GitLab 安装在域名根路径（即 `https://host/api/v4`）；装在子路径（如 `https://host/gitlab/...`）时会表现为 404
- 同一作者名下，技能名取自路径最后一段，因此 `agents/foo` 与 `tools/foo` 会撞名（不同作者可以各有一个 `foo`）
- 已登记的技能会被重新指向：同一作者用相同技能名再次提交，会覆盖原有的分支/路径配置

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
| 出站请求 | Python 标准库 urllib（拉取 GitLab 内容，无额外依赖） |
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