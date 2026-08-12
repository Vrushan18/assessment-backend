from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field
from enum import Enum


class SkillTier(str, Enum):
    WEAK = "Weak"
    DEVELOPING = "Developing"
    PROFICIENT = "Proficient"
    EXPERT = "Expert"


class CriterionScore(BaseModel):
    question_id: str
    criterion: str = Field(pattern=r"^C[1-6]$")
    score: float = Field(ge=0.0, le=10.0)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    rubric_reference: str

class ScoredResult(BaseModel):
    candidate_id: str
    package_id: str

    question_scores: List[CriterionScore]

    aggregate_scores: Dict[str, float]

    overall_score: float = Field(ge=0.0, le=10.0)

    skill_tier: SkillTier

    confidence_overall: float = Field(ge=0.0, le=1.0)

    c5_veto_triggered: bool

    explanation: str

    graded_at: datetime