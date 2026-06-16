import os
from pydantic import BaseModel


def _detect_source_dir() -> str:
    """Auto-detect the Agent OS source directory."""
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    ).replace("\\", "/")


class Settings(BaseModel):
    app_name: str = "Agent OS"
    debug: bool = True
    ollama_url: str = "http://localhost:11434"

    # ── Filesystem Isolation ──────────────────────────────────────────
    project_root: str = "D:/Projects"
    agent_os_source_dir: str = _detect_source_dir()

    # ── Port Reservation ──────────────────────────────────────────────
    reserved_ports: list[int] = [8000, 5173, 3000]
    port_range_frontend: tuple[int, int] = (3101, 3199)
    port_range_backend: tuple[int, int] = (8101, 8199)

    # ── Persistence ───────────────────────────────────────────────────
    data_dir: str = os.path.join(
        _detect_source_dir(), ".agentos-data"
    ).replace("\\", "/")

    # ── Runtime ───────────────────────────────────────────────────────
    orphan_cleanup_interval_seconds: int = 60
    max_concurrent_jobs: int = 5

    # ── Forbidden Paths ───────────────────────────────────────────────
    forbidden_paths: list[str] = [
        "C:/",
        "C:/Windows",
        "C:/Windows/System32",
        "C:/Program Files",
        "C:/Program Files (x86)",
        "C:/Users",
    ]


settings = Settings()
