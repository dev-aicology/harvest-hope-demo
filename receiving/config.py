"""Explicit, fail-closed configuration for the local draft."""
from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlparse


def validate_local_url(value: str) -> str:
    parsed = urlparse(value)
    if (parsed.scheme not in {"http", "https"}
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username or parsed.password or parsed.query or parsed.fragment
        or parsed.path not in {"", "/"}):
        raise ValueError("The Ollama URL must be a loopback origin without credentials or a path.")
    _ = parsed.port  # Validate the port before any request.
    return value.rstrip("/")


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path("var")
    host: str = "127.0.0.1"
    port: int = 8000
    mode: str = "demo"
    integration: str = "mock"
    ai_provider: str = "disabled"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = ""
    photo_retention_days: int = 7
    max_photo_bytes: int = 4 * 1024 * 1024

    def __post_init__(self):
        if self.mode != "demo" or self.integration != "mock":
            raise ValueError("Only demo mode and mock integration are implemented.")
        if self.host not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("This draft may only bind to a loopback address.")
        if not 1024 <= self.port <= 65535:
            raise ValueError("Choose an unprivileged port between 1024 and 65535.")
        if self.ai_provider not in {"disabled", "ollama"}:
            raise ValueError("HH_AI_PROVIDER must be disabled or ollama.")
        validate_local_url(self.ollama_url)
        if self.ai_provider == "ollama" and not self.ollama_model.strip():
            raise ValueError("Choose an installed local model using HH_OLLAMA_MODEL.")
        if self.ai_provider == "ollama" and "cloud" in self.ollama_model.lower():
            raise ValueError("Choose a local model tag; cloud model tags are disabled.")
        if not 1 <= self.photo_retention_days <= 30:
            raise ValueError("Photo retention must be between 1 and 30 days.")
        if not 1024 <= self.max_photo_bytes <= 4 * 1024 * 1024:
            raise ValueError("Photo size limit must be between 1 KiB and 4 MiB.")

    @classmethod
    def from_env(cls):
        return cls(
            data_dir=Path(os.environ.get("HH_DATA_DIR", "var")),
            host=os.environ.get("HH_HOST", "127.0.0.1"),
            port=int(os.environ.get("HH_PORT", "8000")),
            mode=os.environ.get("HH_MODE", "demo"),
            integration=os.environ.get("HH_INTEGRATION", "mock"),
            ai_provider=os.environ.get("HH_AI_PROVIDER", "disabled"),
            ollama_url=os.environ.get("HH_OLLAMA_URL", "http://127.0.0.1:11434"),
            ollama_model=os.environ.get("HH_OLLAMA_MODEL", ""),
            photo_retention_days=int(os.environ.get("HH_PHOTO_RETENTION_DAYS", "7")),
            max_photo_bytes=int(os.environ.get("HH_MAX_PHOTO_BYTES", str(4 * 1024 * 1024))),
        )
