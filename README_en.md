# SkillHub

A self-hosted marketplace for AI agent skills. Enable your team to search, upload, version, and share reusable capabilities for any AI agent that supports the skills protocol.

---

## Overview

AI agents benefit from domain-specific knowledge and toolchain integrations packaged as reusable modules ("skills"). SkillHub provides a private, self-hosted repository for managing these skills within your organization &mdash; analogous to a container registry or package index, but purpose-built for AI agent workflows.

---

## Features

| Category | Details |
|----------|---------|
| Browse & Search | Full-text search, tag filtering, multi-dimension sorting (total downloads / 24h trending / newest) |
| Upload | Drag-and-drop folder upload with automatic ZIP packaging and SKILL.md frontmatter extraction |
| Version Management | Multiple versions per skill, in-place switching, author-controlled version deletion |
| User System | Registration with admin approval, BCrypt password hashing, JWT with refresh token rotation |
| Access Control | Admin / user role separation, skill ownership enforcement, skill transfer between users |
| Internationalization | Chinese and English locales, configurable default language, runtime switching via UI dropdown |
| Theme Support | Light and dark modes with system preference detection |
| Branding | Customizable logo, favicon, and site title via configuration file |
| Markdown Rendering | Full GFM support including tables, fenced code blocks, and frontmatter display |
| Admin Panel | User approval, disable/enable accounts, user creation, status-based filtering |

### Screenshots

<p align="center">
  <img src="website/public/dark.png" alt="SkillHub Dark Theme" width="32%">
  <img src="website/public/white.png" alt="SkillHub Light Theme" width="32%">
  <img src="website/public/login.png" alt="SkillHub Login" width="32%">
</p>

---

## Quick Start

### Installation

```bash
pip install skillhub-selfhost
```

Requires Python &ge; 3.8.

### Create Administrator

```bash
skillhub-selfhost admin-init
```

### Start Server

```bash
skillhub-selfhost server-start
```

Open `http://localhost:8000` in a browser.

Customize host and port:

```bash
skillhub-selfhost server-start --host 0.0.0.0 --port 8080
```

---

## Configuration

Place a `config.json` file in the working directory. All fields are optional; defaults apply when omitted.

### Complete Example

```json
{
  "db_url": "postgres://skillhub:password@localhost:5432/skillhub",
  "default_lang": "zh",
  "logo_text": "MySkillHub",
  "logo": "logo.png",
  "favicon": "favicon.ico"
}
```

### Configuration Reference

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `db_url` | string | `sqlite://{cwd}/metadata.db` | Database connection string (see Database Configuration below) |
| `default_lang` | string | `en` | Default UI language (`en` or `zh`) |
| `logo_text` | string | `SkillHub` | Text displayed in the navigation bar |
| `logo` | string | — | Image file name placed alongside config.json; appears to the left of logo_text |
| `favicon` | string | — | Browser tab icon file name placed alongside config.json; falls back to built-in default if omitted |

### Database Configuration

SkillHub uses [Tortoise ORM](https://tortoise.github.io/) and supports SQLite and PostgreSQL.

#### SQLite (Default)

No additional setup required. Suitable for individual use and small teams.

```json
{ "db_url": "sqlite://metadata.db" }
```

| Format | Description |
|--------|-------------|
| `sqlite://metadata.db` | Relative to working directory |
| `sqlite:///absolute/path/metadata.db` | Absolute path (three slashes) |
| `sqlite://:memory:` | In-memory (data lost on restart, testing only) |

#### PostgreSQL (Production)

Install the asyncpg driver:

```bash
pip install asyncpg
```

Connection string format: `postgres://user:password@host:port/database`

```json
{ "db_url": "postgres://skillhub:password@localhost:5432/skillhub" }
```

With connection pool parameters:

```json
{ "db_url": "postgres://skillhub:password@10.0.0.5:5432/skillhub?minsize=5&maxsize=20" }
```

Notes:
- Create the database before starting (`CREATE DATABASE skillhub;`). Tables are auto-created on launch.
- Grant schema read/write permissions to the configured user.
- Production deployments should use a dedicated database user.

#### Comparison

| Dimension | SQLite | PostgreSQL |
|-----------|--------|------------|
| Setup | Zero-configuration | Requires running PostgreSQL service |
| Concurrency | Single writer, limited reads | High-throughput concurrent access |
| Reliability | Single-file, simple backup | WAL-based crash recovery |
| Use case | Individual / small team (&lt; 10) | Team collaboration / production |
| Migration | None | Configuration-only switch; manual data migration |

### Configuration Precedence

1. **Environment variables** (highest)
2. **`config.json`**
3. **Built-in defaults** (lowest)

Environment variables override corresponding `config.json` fields. Branding fields (`logo_text`, `logo`, `favicon`) are `config.json`-only.

### Environment Variables

| Variable | Maps to | Default | Description |
|----------|---------|---------|-------------|
| `SKILLHUB_HOST` | — | `0.0.0.0` | Listen address |
| `SKILLHUB_PORT` | — | `8000` | Listen port |
| `SKILLHUB_DB_URL` | `db_url` | `sqlite://{cwd}/metadata.db` | Database connection string |
| `SKILLHUB_SECRET_KEY` | — | Auto-generated | JWT signing key; must be fixed in production |
| `SKILLHUB_SKILLS_DIR` | — | `{cwd}/skills` | Skill file storage directory |
| `SKILLHUB_LOG_LEVEL` | — | `INFO` | Log level (`DEBUG` / `INFO` / `WARNING` / `ERROR`) |

---

## Production Deployment

```bash
# 1. Prepare config.json with PostgreSQL
cat > config.json << EOF
{
  "db_url": "postgres://skillhub:password@localhost:5432/skillhub",
  "default_lang": "en",
  "logo_text": "MySkillHub",
  "logo": "logo.png",
  "favicon": "favicon.ico"
}
EOF

# 2. Generate a persistent JWT secret
export SKILLHUB_SECRET_KEY=$(openssl rand -hex 32)

# 3. Start the server
skillhub-selfhost server-start --port 8000
```

Key points:
- `SKILLHUB_SECRET_KEY` must be persistent and confidential; changing it invalidates all active sessions.
- Mount `SKILLHUB_SKILLS_DIR` on persistent storage (Docker volume, NFS, or cloud block storage).
- The frontend is embedded in the Python package. No separate web server is required.
- For HTTPS, place a reverse proxy (Nginx, Caddy) in front of the application to terminate TLS.

---

## Architecture

| Layer | Technology |
|-------|------------|
| API Framework | FastAPI (Python) |
| ORM | Tortoise ORM + SQLite / PostgreSQL |
| Authentication | BCrypt + PyJWT |
| CLI | Typer |
| Frontend Framework | React 18 + TypeScript |
| Build Tool | Vite |
| UI Components | shadcn/ui (New York) + Tailwind CSS 3 |
| Icons | Lucide React |
| Markdown | react-markdown + remark-gfm |
| Internationalization | Custom React context with localStorage persistence |
| Theming | next-themes |

---

## Development

```bash
# Backend (hot-reload)
uvicorn skillhub_selfhost.main:create_app --factory --reload

# Frontend
cd frontend
npm install
npm run dev          # Development server with HMR
npm run build        # Production build → skillhub_selfhost/dist/
```

---

## Links

- [Project Website](https://mikigo.github.io/skillhub-selfhost/)
- [GitHub Repository](https://github.com/mikigo/skillhub-selfhost)

---

## License

Apache-2.0