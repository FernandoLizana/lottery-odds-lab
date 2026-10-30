from __future__ import annotations

import json
import random

from lab.combinations import sample_uniform
from lab.profiles import get_profile
from lab.simulate import auto_ticket, run_monte_carlo


def test_auto_ticket_is_not_first_simulated_draw():
    p = get_profile("kino_moderno")
    for seed in (1, 7, 42, 2024):
        first_draw = sample_uniform(p, random.Random(seed))
        assert sorted(auto_ticket(p, seed)) != sorted(first_draw)
        assert auto_ticket(p, seed) == auto_ticket(p, seed)


def test_resume_keeps_mean_hits_per_ticket():
    p = get_profile("kino_moderno")
    tickets = [auto_ticket(p, 5), auto_ticket(p, 6)]
    full = run_monte_carlo(p, 3_000, 9, tickets)

    calls = {"n": 0}

    def pause_once():
        calls["n"] += 1
        return calls["n"] == 2  # pausa tras el primer lote

    paused = run_monte_carlo(p, 3_000, 9, tickets, should_pause=pause_once)
    assert paused["status"] == "paused"
    # Igual que job_runner: el checkpoint pasa por JSON.
    cp = json.loads(json.dumps(paused["checkpoint"], default=str))
    resumed = run_monte_carlo(
        p, 3_000, 9, tickets,
        start_done=cp["done"],
        start_hits=cp["hits"],
        start_rng_state=cp["rng_state"],
        start_ticket_hits=cp["ticket_hits"],
    )
    assert resumed["n_completed"] == 3_000
    assert resumed["mean_hits_per_ticket"] == full["mean_hits_per_ticket"]
    assert [h["count"] for h in resumed["hits"]] == [h["count"] for h in full["hits"]]
