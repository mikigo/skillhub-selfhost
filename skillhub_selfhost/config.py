# skillhub_selfhost/config.py
import os
import json
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class Config:
    base_dir: Path = field(default_factory=lambda: Path.cwd())
    host: str = "0.0.0.0"
    port: int = 8000
    db_url: str = ""
    secret_key: str = ""
    skills_dir: Optional[Path] = None
    log_level: str = "INFO"
    logo_text: str = "SkillHub"
    logo: str = ""
    favicon: str = ""
    default_lang: str = "en"

    def __post_init__(self):
        self._load_config_json()
        if not self.db_url:
            self.db_url = f"sqlite://{self.base_dir / 'metadata.db'}"
        if not self.secret_key:
            self.secret_key = self._load_or_generate_secret()
        if self.skills_dir is None:
            self.skills_dir = self.base_dir / "skills"

    def _load_config_json(self):
        config_file = self.base_dir / "config.json"
        if not config_file.exists():
            return
        try:
            data = json.loads(config_file.read_text())
            if data.get("db_url"):
                self.db_url = data["db_url"]
            if data.get("logo_text"):
                self.logo_text = data["logo_text"]
            if data.get("logo"):
                self.logo = data["logo"]
            if data.get("favicon"):
                self.favicon = data["favicon"]
            if data.get("default_lang"):
                self.default_lang = data["default_lang"]
        except Exception:
            pass

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