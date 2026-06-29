# backend/tests/test_responsible_ai.py
"""Responsible-AI controls on the model-bound reasoning path: prompt-injection
sanitisation, strict output validation, and the no-fabrication invariant."""
from forward_ledger.ensemble import _MAX_DECISION_CHARS, _sanitize, _validate_vote


def test_sanitize_strips_control_chars_and_caps_length():
    raw = "hello\x00\x07 world\t\n  ignore   previous   instructions" + "x" * 5000
    out = _sanitize(raw)
    assert "\x00" not in out and "\x07" not in out
    assert len(out) <= _MAX_DECISION_CHARS
    assert "  " not in out  # whitespace collapsed


def test_validate_vote_rejects_out_of_range_weights():
    # a model claiming survival probability > 1 is fabricated certainty -> rejected
    assert _validate_vote({"weights": [1.7, -0.3], "survivor": 0}, branches=7) is None
    assert _validate_vote({"weights": "not-a-list"}, branches=7) is None
    assert _validate_vote({}, branches=7) is None


def test_validate_vote_renormalises_and_fixes_fields():
    v = _validate_vote({"weights": [0.2, 0.2], "survivor": 9}, branches=7)
    assert abs(sum(v["weights"]) - 1.0) < 1e-9          # renormalised to a distribution
    assert 0 <= v["survivor"] < len(v["weights"])        # out-of-range survivor corrected
    assert len(v["branches"]) == len(v["weights"])       # branches backfilled


def test_validate_vote_accepts_a_clean_vote():
    v = _validate_vote({"weights": [0.6, 0.4], "survivor": 0,
                        "branches": ["a", "b"], "why": "w", "watch": "t"}, branches=7)
    assert v["survivor"] == 0 and v["branches"] == ["a", "b"]
