from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from services.combination_service import combo_to_mask, features_for_combo, mask_to_combo, overlap_count
from services.csv_service import parse_csv_bytes
from services.scoring_service import normalize_weights, score_combo
from services.draw_calendar import TZ_CHILE, next_draw_datetime
from services.statistical_seed_service import build_statistical_seed


class FakeDraw:
    def __init__(self, draw_date, numbers, draw_number):
        self.draw_date = draw_date
        self._numbers = numbers
        self.draw_number = draw_number

    def numbers(self):
        return self._numbers


def test_parse_kino_header_csv():
    raw = b"Fecha,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14\n01-01-2023,01,02,03,04,05,06,09,11,13,18,19,22,24,25\n"
    rows = parse_csv_bytes(raw)
    assert len(rows) == 1
    assert rows[0]["numbers"] == [1, 2, 3, 4, 5, 6, 9, 11, 13, 18, 19, 22, 24, 25]


def test_reject_duplicates():
    raw = b"Fecha,N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14\n01-01-2023,01,01,03,04,05,06,09,11,13,18,19,22,24,25\n"
    try:
        parse_csv_bytes(raw)
        assert False, "should fail"
    except Exception as exc:
        assert "Ningún sorteo válido" in str(exc) or "duplicad" in str(exc).lower()


def test_mask_roundtrip():
    nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
    mask = combo_to_mask(nums)
    assert mask_to_combo(mask) == nums
    assert overlap_count(mask, mask) == 14


def test_features_and_score():
    import numpy as np

    matrix = np.array(
        [
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
            [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        ],
        dtype=np.int16,
    )
    from services.scoring_service import _build_context

    ctx = _build_context(matrix)
    weights = normalize_weights(None)
    scored = score_combo([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14], ctx, weights)
    assert 0 <= scored["score"] <= 2
    feats = features_for_combo(scored["numbers"])
    assert feats["total_sum"] == sum(range(1, 15))


def test_statistical_seed_is_reproducible_and_history_sensitive():
    draws = [
        FakeDraw(
            date(2026, 7, 1) + timedelta(days=i),
            list(range(1 + (i % 2), 15 + (i % 2))),
            3200 + i,
        )
        for i in range(4)
    ]
    run_date = date(2026, 7, 19)

    first = build_statistical_seed(draws, experiment_date=run_date)
    second = build_statistical_seed(list(reversed(draws)), experiment_date=run_date)

    assert first["sha256"] == second["sha256"]
    assert first["numeric_seed"] == second["numeric_seed"]
    assert len(first["sha256"]) == 64
    assert 0 <= first["numeric_seed"] < 2**63

    changed = build_statistical_seed(
        draws + [
            FakeDraw(
                date(2026, 7, 20),
                list(range(3, 17)),
                3204,
            )
        ],
        experiment_date=run_date,
    )
    assert changed["sha256"] != first["sha256"]


def test_next_draw_datetime_calendar_cases():
    # Sábado mañana -> domingo 22:30
    sat_morning = datetime(2026, 7, 18, 10, 0, tzinfo=TZ_CHILE)  # sábado
    nxt = next_draw_datetime(sat_morning)
    assert nxt == datetime(2026, 7, 19, 22, 30, tzinfo=TZ_CHILE)
    assert nxt.weekday() == 6

    # Domingo mañana -> domingo 22:30
    sun_morning = datetime(2026, 7, 19, 9, 15, tzinfo=TZ_CHILE)
    nxt = next_draw_datetime(sun_morning)
    assert nxt == datetime(2026, 7, 19, 22, 30, tzinfo=TZ_CHILE)

    # Domingo 22:31 -> miércoles 22:30
    sun_late = datetime(2026, 7, 19, 22, 31, tzinfo=TZ_CHILE)
    nxt = next_draw_datetime(sun_late)
    assert nxt == datetime(2026, 7, 22, 22, 30, tzinfo=TZ_CHILE)
    assert nxt.weekday() == 2

    # Miércoles 22:29 -> miércoles 22:30
    wed_early = datetime(2026, 7, 22, 22, 29, tzinfo=TZ_CHILE)
    nxt = next_draw_datetime(wed_early)
    assert nxt == datetime(2026, 7, 22, 22, 30, tzinfo=TZ_CHILE)


def test_color_arc_payload_and_route():
    from app import create_app
    from services.color_service import build_color_arc_payload

    draws = [
        FakeDraw(date(2026, 7, 15), list(range(1, 15)), 1),
        FakeDraw(date(2026, 7, 17), list(range(12, 26)), 2),
    ]
    payload = build_color_arc_payload(draws)
    assert payload["draw_count"] == 2
    assert len(payload["numbers"]) == 25
    assert payload["numbers"][0]["number"] == 1
    assert payload["last"]["date"] == "2026-07-17"
    assert payload["points"][0]["hex"] != payload["points"][1]["hex"]
    assert sum(p["dominant_count"] for p in payload["pigments"]) == 2

    app = create_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/colores" in rules
    assert "/colores/predecir" in rules
    template = (
        Path(__file__).resolve().parents[1] / "templates" / "colors.html"
    ).read_text(encoding="utf-8")
    assert "colorArcSvg" in template
    assert "Predecir próximo sorteo" in template
    assert "color_predict" in template
    assert "conic-gradient" in (
        Path(__file__).resolve().parents[1] / "static" / "css" / "app.css"
    ).read_text(encoding="utf-8")
    navbar = (
        Path(__file__).resolve().parents[1] / "templates" / "base.html"
    ).read_text(encoding="utf-8")
    assert "url_for('colors')" in navbar


def test_combo_color_is_deterministic_and_uses_all_five_pigments():
    from services.color_service import PIGMENT_NAMES, combo_color, number_hue_deg

    a = combo_color([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
    b = combo_color([14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1])
    assert a["hex"] == b["hex"]
    assert a["dominant_pigment"] == "rojo"
    assert a["pigment_counts"]["rojo"] == 5
    assert number_hue_deg(1) == 0.0
    assert abs(number_hue_deg(26) - 0.0) < 1e-9
    # Un bloque alto se va al violeta y a un tono distinto.
    high = combo_color([12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25])
    assert high["hex"] != a["hex"]
    assert high["hue_deg"] > a["hue_deg"]
    assert combo_color(list(range(12, 26)))["pigment_counts"]["violeta"] == 5
    assert set(a["pigment_counts"]) == set(PIGMENT_NAMES)


def test_color_prediction_prefers_target_hue():
    from services.color_service import combo_color, run_color_experiment

    draws = [
        FakeDraw(date(2026, 7, 15), list(range(1, 15)), 1),
        FakeDraw(date(2026, 7, 17), list(range(2, 16)), 2),
    ]
    metrics, results = run_color_experiment(
        draws, mode="pick", target_hue=0.0, sample_size=400, seed=3, top_k=5
    )
    assert metrics["mode"] == "color"
    assert metrics["target"]["hue_deg"] == 0.0
    assert len(results) == 5
    top = metrics["prediction"]
    assert len(top["numbers"]) == 14
    # Cerca del rojo (0°) — más cerca que una cartilla alta/violeta.
    far = combo_color(list(range(12, 26)))
    assert top["hue_distance_deg"] < min(far["hue_deg"], 360 - far["hue_deg"]) - 10


def test_results_copy_ui_contract():
    template = (
        Path(__file__).resolve().parents[1] / "templates" / "results.html"
    ).read_text(encoding="utf-8")
    assert "Copiar 14 números" in template
    assert "navigator.clipboard.writeText" in template
    assert "selected.kind == 'color' and rows" in template
    for word in ("astrolog", "lunar", "tarot"):
        assert word not in template.lower()

    dashboard = (
        Path(__file__).resolve().parents[1] / "templates" / "dashboard.html"
    ).read_text(encoding="utf-8")
    assert "url_for('colors')" in dashboard
    assert "Arco de colores" in dashboard
    for word in ("astrolog", "lunar", "tarot"):
        assert word not in dashboard.lower()
