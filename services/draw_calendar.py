"""Calendario de sorteos y desempate geométrico neutral."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np

from config import Config

DRAW_HOUR = Config.DRAW_HOUR
DRAW_MINUTE = Config.DRAW_MINUTE
DRAW_WEEKDAYS = tuple(Config.DRAW_WEEKDAYS)
TZ_CHILE = ZoneInfo(Config.DRAW_TIMEZONE)

WEEKDAY_NAMES_ES = {
    0: "lunes",
    1: "martes",
    2: "miércoles",
    3: "jueves",
    4: "viernes",
    5: "sábado",
    6: "domingo",
}

GEOMETRIC_TIEBREAK_WEIGHT = 0.02


def next_draw_datetime(now: datetime | None = None) -> datetime:
    """Próximo sorteo real: miércoles/viernes/domingo a las 22:30 America/Santiago."""
    if now is None:
        now = datetime.now(TZ_CHILE)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=TZ_CHILE)
    else:
        now = now.astimezone(TZ_CHILE)

    for offset in range(0, 8):
        day = (now + timedelta(days=offset)).date()
        if day.weekday() not in DRAW_WEEKDAYS:
            continue
        candidate = datetime(
            day.year,
            day.month,
            day.day,
            DRAW_HOUR,
            DRAW_MINUTE,
            tzinfo=TZ_CHILE,
        )
        if candidate > now:
            return candidate
    raise RuntimeError("No se pudo determinar el próximo sorteo")


def format_draw_label(dt: datetime) -> str:
    local = dt.astimezone(TZ_CHILE) if dt.tzinfo else dt.replace(tzinfo=TZ_CHILE)
    name = WEEKDAY_NAMES_ES[local.weekday()].capitalize()
    return (
        f"{name} {local.strftime('%Y-%m-%d')} "
        f"{local.strftime('%H:%M')} {Config.DRAW_TIMEZONE}"
    )


def _geometric_tiebreak(feats: dict) -> float:
    """Desempate geométrico neutral (paridad/suma/consecutivos); no usa historial."""
    parity = 1.0 - abs(feats["even_count"] - feats["odd_count"]) / Config.DRAW_SIZE
    # Suma ideal aproximada de 14 números ~ 182
    sum_score = float(np.exp(-0.5 * ((feats["total_sum"] - 182) / 25.0) ** 2))
    consec = 1.0 - abs(feats["consecutive"] - 2) / Config.DRAW_SIZE
    return float(max(0.0, (parity + sum_score + consec) / 3.0))
