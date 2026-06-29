# backend/tests/test_dp_federation.py
"""Differential privacy on the Clean Rooms federated aggregates."""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "infra", "clean_rooms"))

import federation as F  # noqa: E402


def test_dp_mean_is_bounded_and_close_with_large_n():
    rng = random.Random(7)
    # 5000 records, 3000 survived; ε=1 → noise scale (1/5000) is tiny
    v = F.dp_mean(3000, 5000, epsilon=1.0, sensitivity=1.0, rng=rng)
    assert 0.0 <= v <= 1.0
    assert abs(v - 0.6) < 0.05


def test_dp_mean_actually_randomises():
    a = F.dp_mean(50, 100, 1.0, 1.0, random.Random(1))
    b = F.dp_mean(50, 100, 1.0, 1.0, random.Random(2))
    assert a != b  # different randomness → different noisy releases


def test_min_cell_suppression_still_enforced():
    # one bucket below min_cell must not be released at all
    t = F.TenantContribution("acme", {7: (3, 2)})  # n=3 < min_cell 5
    out = F.joint_calibration([t], min_cell=5, rng=random.Random(0))
    assert out["joint_reliability"] == []


def test_dp_budget_is_reported():
    t1 = F.TenantContribution("acme", {7: (12, 9), 8: (8, 7)})
    t2 = F.TenantContribution("globex", {7: (9, 7), 8: (11, 10)})
    out = F.joint_calibration([t1, t2], epsilon=0.5, rng=random.Random(3))
    cells = out["dp"]["released_cells"]
    assert out["dp"]["mechanism"] == "laplace"
    assert abs(out["dp"]["epsilon_total"] - 0.5 * cells) < 1e-9
    for row in out["joint_reliability"]:
        assert 0.0 <= row["actual_survival"] <= 1.0
