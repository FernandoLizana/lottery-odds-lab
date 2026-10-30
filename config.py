from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _env_float(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    return int(raw)


class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.environ.get("SECRET_KEY", "kino-local-dev-key-change-me")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'data' / 'kino.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    POOL_SIZE = 25
    DRAW_SIZE = 14
    COMBINATION_COUNT = 4_457_400
    DEFAULT_CHUNK_SIZE = 50_000
    DEFAULT_SAMPLE_SIZE = 20_000
    LOG_DIR = BASE_DIR / "logs"
    JOB_POLL_MS = 800

    DEFAULT_WEIGHTS = {
        "frequency": 1.0,
        "gap": 0.8,
        "parity": 0.6,
        "sum_balance": 0.7,
        "bands": 0.7,
        "consecutive": 0.5,
        "pairs": 0.9,
        "triples": 0.6,
    }

    # Horario del sorteo. Sobrescribible con .env.
    DRAW_TIMEZONE = os.environ.get("DRAW_TIMEZONE", "America/Santiago")
    DRAW_HOUR = _env_int("DRAW_HOUR", 22)
    DRAW_MINUTE = _env_int("DRAW_MINUTE", 30)
    # Miércoles, viernes y domingo (date.weekday(): lun=0 … dom=6)
    DRAW_WEEKDAYS = (2, 4, 6)
