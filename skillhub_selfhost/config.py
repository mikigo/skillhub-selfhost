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

    def __post_init__(self):
        if not self.db_url:
            self.db_url = self._load_db_url()
        if not self.secret_key:
            self.secret_key = self._load_or_generate_secret()
        if self.skills_dir is None:
            self.skills_dir = self.base_dir / "skills"

    def _load_db_url(self) -> str:
        config_file = self.base_dir / "config.json"
        if config_file.exists():
            try:
                data = json.loads(config_file.read_text())
                if data.get("db_url"):
                    return data["db_url"]
            except Exception:
                pass
        return f"sqlite://{self.base_dir / 'metadata.db'}"

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