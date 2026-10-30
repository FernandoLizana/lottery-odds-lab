"""Carga del histórico completo del Kino (era de 15 y de 14 números)."""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import Config  # noqa: E402

POOL = Config.POOL_SIZE
HISTORICO_PATH = BASE_DIR / "historico.csv"
MODERN_CSV = BASE_DIR / "data" / "kino_draws.csv"


def _parse_historico_date(raw: str) -> date:
    raw = raw.strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return datetime.strptime(raw, "%d-%m-%Y").date()


def load_historico_all_eras(path: Path) -> dict[date, list[int]]:
    """Lee historico.csv aceptando 14 o 15 números (era antigua y moderna)."""
    rows: dict[date, list[int]] = {}
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = [p.strip() for p in line.split(",") if p.strip() != ""]
        if len(parts) < 15:
            continue
        numbers = [int(x) for x in parts[1:]]
        if len(numbers) not in (14, 15):
            continue
        if len(set(numbers)) != len(numbers):
            continue
        if min(numbers) < 1 or max(numbers) > POOL:
            continue
        rows[_parse_historico_date(parts[0])] = sorted(numbers)
    return rows


def load_modern_csv(path: Path) -> dict[date, list[int]]:
    import csv as csv_module

    rows: dict[date, list[int]] = {}
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", newline="") as handle:
        for record in csv_module.DictReader(handle):
            draw_date = date.fromisoformat(record["draw_date"].strip())
            numbers = [int(record[f"n{i}"]) for i in range(1, 15)]
            if len(set(numbers)) != 14:
                continue
            rows[draw_date] = sorted(numbers)
    return rows


def load_longest_history() -> tuple[list[date], np.ndarray, np.ndarray]:
    """Une 1990→hoy. Si una fecha está en ambos, gana el CSV moderno."""
    merged = load_historico_all_eras(HISTORICO_PATH)
    merged.update(load_modern_csv(MODERN_CSV))
    dates = sorted(merged)
    hits = np.zeros((len(dates), POOL), dtype=np.float64)
    sizes = np.empty(len(dates), dtype=np.int16)
    for i, draw_date in enumerate(dates):
        numbers = merged[draw_date]
        sizes[i] = len(numbers)
        for number in numbers:
            hits[i, number - 1] = 1.0
    return dates, hits, sizes

