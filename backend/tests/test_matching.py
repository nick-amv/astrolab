"""Matching engine unit tests — pure, no DB."""

from __future__ import annotations

from app.matching.engine import (
    OccupationVec,
    Profile,
    cosine,
    match,
    score_occupation,
    subject_fit,
)

CONFIG = {
    "default": {"riasec": 0.5, "subjects": 0.25, "values": 0.25},
    "by_age_band": {"14-16": {"riasec": 0.45, "subjects": 0.35, "values": 0.20}},
    "core_tau": 0.55,
}


def test_cosine_identical_is_one() -> None:
    v = {"R": 1.0, "I": 0.5}
    assert abs(cosine(v, v, ("R", "I", "A")) - 1.0) < 1e-9


def test_cosine_empty_is_zero() -> None:
    assert cosine({}, {"R": 1.0}, ("R",)) == 0.0


def test_subject_fit_weighted_mean() -> None:
    user = {"math": 1.0, "phys": 0.5, "art": 0.0}
    occ = {"math": 2.0, "phys": 1.0}  # weights
    # (1.0*2 + 0.5*1) / 3 = 0.8333
    assert abs(subject_fit(user, occ) - (2.5 / 3)) < 1e-9


def test_subject_fit_no_key_subjects_is_neutral() -> None:
    assert subject_fit({"math": 1.0}, {}) == 0.0


def test_age_band_weights_used() -> None:
    profile_teen = Profile(riasec={"R": 1.0}, subjects={"math": 1.0}, age_band="14-16")
    occ = OccupationVec(id="1", slug="a", riasec={"R": 1.0}, subjects={"math": 1.0})
    # 14-16 weights subjects higher (0.35) than default (0.25).
    s_teen = score_occupation(profile_teen, occ, CONFIG)
    profile_adult = Profile(riasec={"R": 1.0}, subjects={"math": 1.0}, age_band="24+")
    s_adult = score_occupation(profile_adult, occ, CONFIG)  # falls back to default
    assert s_teen != s_adult


def test_soft_penalty_pushes_down_not_out() -> None:
    profile = Profile(riasec={"I": 1.0}, age_band="17-19", constraints={"max_edu_years": 4})
    long = OccupationVec(id="1", slug="med", riasec={"I": 1.0}, edu_years=8)
    short = OccupationVec(id="2", slug="lab", riasec={"I": 1.0}, edu_years=4)
    s_long = score_occupation(profile, long, CONFIG)
    s_short = score_occupation(profile, short, CONFIG)
    assert s_long < s_short  # penalised
    assert s_long > 0  # but not eliminated


def test_match_is_deterministic_and_bucketed() -> None:
    profile = Profile(
        riasec={"I": 1.0, "A": 0.2},
        values={"achievement": 1.0},
        subjects={"math": 1.0},
        age_band="17-19",
    )
    occs = [
        OccupationVec("1", "data-scientist", {"I": 1.0}, {"achievement": 1.0}, {"math": 1.0},
                      field_tag="tech"),
        OccupationVec("2", "mathematician", {"I": 0.95}, {"achievement": 0.9}, {"math": 1.0},
                      field_tag="science"),
        OccupationVec("3", "clerk", {"C": 1.0}, {"stability": 1.0}, {}, field_tag="admin"),
    ]
    r1 = match(profile, occs, CONFIG)
    r2 = match(profile, occs, CONFIG)
    assert [x.occupation.id for x in r1] == [x.occupation.id for x in r2]  # deterministic
    # strong I-match ranks first and is core
    assert r1[0].occupation.slug == "data-scientist"
    assert r1[0].bucket == "core"
    # the weak match (clerk) is not core
    clerk = next(x for x in r1 if x.occupation.slug == "clerk")
    assert clerk.bucket != "core"


def test_stable_tiebreak_by_slug() -> None:
    profile = Profile(riasec={"R": 1.0}, age_band="17-19")
    # identical scores → ordered by slug asc
    occs = [
        OccupationVec("1", "zeta", {"R": 1.0}),
        OccupationVec("2", "alpha", {"R": 1.0}),
    ]
    r = match(profile, occs, CONFIG)
    assert [x.occupation.slug for x in r] == ["alpha", "zeta"]
