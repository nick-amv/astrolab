"""Scoring unit tests — pure, no DB."""

from __future__ import annotations

from app.assessment.scoring import AnswerItem, compute_scores


def test_riasec_mean_per_axis() -> None:
    answers = [
        AnswerItem("A", "I", 1.0),
        AnswerItem("A", "I", 0.5),
        AnswerItem("A", "R", 0.0),
    ]
    s = compute_scores(answers)
    assert s["riasec"]["I"] == 0.75
    assert s["riasec"]["R"] == 0.0
    # untouched axes default to 0
    assert s["riasec"]["A"] == 0.0
    assert set(s["riasec"]) == {"R", "I", "A", "S", "E", "C"}


def test_klimov_from_tags_only() -> None:
    answers = [
        AnswerItem("A", "S", 1.0, klimov="human"),
        AnswerItem("A", "S", 0.0, klimov="human"),
        AnswerItem("A", "R", 1.0, klimov="tech"),
        AnswerItem("A", "R", 1.0),  # no tag → ignored by klimov
    ]
    s = compute_scores(answers)
    assert s["klimov"]["human"] == 0.5
    assert s["klimov"]["tech"] == 1.0
    assert s["klimov"]["nature"] == 0.0


def test_values_mean_per_axis() -> None:
    answers = [
        AnswerItem("C", "autonomy", 1.0),
        AnswerItem("C", "autonomy", 1.0),
        AnswerItem("C", "stability", 0.0),
    ]
    s = compute_scores(answers)
    assert s["values"]["autonomy"] == 1.0
    assert s["values"]["stability"] == 0.0
    assert set(s["values"]) == {
        "achievement",
        "autonomy",
        "recognition",
        "relationships",
        "stability",
        "conditions",
    }


def test_values_forced_choice_pairs() -> None:
    # v2: dimension "a|b", value 1.0 = a wins, 0.0 = b wins. Win-rate per axis.
    answers = [
        AnswerItem("C", "autonomy|stability", 1.0),   # autonomy wins
        AnswerItem("C", "autonomy|achievement", 1.0),  # autonomy wins
        AnswerItem("C", "recognition|autonomy", 0.0),  # autonomy wins (b side)
        AnswerItem("C", "stability|achievement", 1.0),  # stability wins
    ]
    s = compute_scores(answers)
    # autonomy appeared in 3 pairs, won all 3
    assert s["values"]["autonomy"] == 1.0
    # stability: appeared twice (lost to autonomy, beat achievement) -> 0.5
    assert s["values"]["stability"] == 0.5
    # achievement: appeared twice, lost both -> 0.0
    assert s["values"]["achievement"] == 0.0
    # recognition: appeared once, lost -> 0.0; untouched axes -> 0.0
    assert s["values"]["recognition"] == 0.0
    assert set(s["values"]) == {
        "achievement",
        "autonomy",
        "recognition",
        "relationships",
        "stability",
        "conditions",
    }


def test_subjects_passthrough() -> None:
    answers = [
        AnswerItem("B", "math", 1.0),
        AnswerItem("B", "cs", 0.25),
    ]
    s = compute_scores(answers)
    assert s["subjects"] == {"math": 1.0, "cs": 0.25}


def test_empty_is_all_zero() -> None:
    s = compute_scores([])
    assert all(v == 0.0 for v in s["riasec"].values())
    assert s["subjects"] == {}
