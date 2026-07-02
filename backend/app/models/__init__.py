"""Import every model so Base.metadata is fully populated for Alembic autogen
and for the metadata-coverage test."""

from app.models.assessment import (
    Answer,
    AssessmentSession,
    Profile,
    QuestionBank,
    QuestionI18n,
    ScoringConfig,
    TraitScore,
)
from app.models.base import Base
from app.models.catalog import (
    DataSource,
    EduDomain,
    EduRequirement,
    Milestone,
    Occupation,
    OccupationCountry,
    OccupationEdu,
    OccupationI18n,
    OccupationSkill,
    OccupationSubject,
    Skill,
    SkillI18n,
)
from app.models.commerce import Event, Payment, Subscription
from app.models.identity import AuthToken, ConsentRecord, DeletionLog, User
from app.models.results import AiInterview, LlmCall, Match, Report

__all__ = [
    "Base",
    # identity
    "User",
    "AuthToken",
    "ConsentRecord",
    "DeletionLog",
    # assessment
    "Profile",
    "AssessmentSession",
    "QuestionBank",
    "QuestionI18n",
    "Answer",
    "TraitScore",
    "ScoringConfig",
    # catalog
    "DataSource",
    "Occupation",
    "OccupationI18n",
    "OccupationCountry",
    "OccupationSubject",
    "Skill",
    "SkillI18n",
    "OccupationSkill",
    "EduDomain",
    "EduRequirement",
    "OccupationEdu",
    "Milestone",
    # results
    "Match",
    "AiInterview",
    "LlmCall",
    "Report",
    # commerce
    "Payment",
    "Subscription",
    "Event",
]
