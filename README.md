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

### 自定义配置

```bash
skillhub-selfhost server-start --host 0.0.0.0 --port 8080
```

环境变量（可选）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SKILLHUB_HOST` | `0.0.0.0` | 监听地址 |
| `SKILLHUB_PORT` | `8000` | 监听端口 |
| `SKILLHUB_DB_URL` | `sqlite://./metadata.db` | 数据库连接（也支持 PostgreSQL） |
| `SKILLHUB_SECRET_KEY` | 自动生成 | JWT 签名密钥 |
| `SKILLHUB_SKILLS_DIR` | `./skills` | skill 文件存储目录 |
| `SKILLHUB_LOG_LEVEL` | `INFO` | 日志级别 |

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

## 部署到生产

1. 设置 `SKILLHUB_DB_URL` 指向 PostgreSQL 实例
2. 设置 `SKILLHUB_SECRET_KEY` 为固定值（防止重启后密钥变化导致 token 失效）
3. 挂载 `SKILLHUB_SKILLS_DIR` 到持久化存储
4. 前端已内嵌到 Python 包中，单进程部署即开即用

```bash
SKILLHUB_DB_URL=postgres://user:pass@host:5432/skillhub \
SKILLHUB_SECRET_KEY=your-random-secret \
skillhub-selfhost server-start --port 8000
```

---

## License

Apache-2.0