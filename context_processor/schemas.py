from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from enum import Enum


class DomainEnum(str, Enum):
    engineering = "Engineering"
    science     = "Science"
    commerce    = "Commerce"
    arts        = "Arts"


class LevelEnum(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


class BloomEnum(str, Enum):
    remember   = "Remember"
    understand = "Understand"
    apply      = "Apply"
    analyse    = "Analyse"
    evaluate   = "Evaluate"
    create     = "Create"


class CandidateContextObject(BaseModel):
    candidate_id:          str
    domain:                DomainEnum
    certification_level:   LevelEnum
    bloom_target:          BloomEnum
    background:            str = Field(..., max_length=500)
    eligibility_confirmed: bool
    timestamp:             datetime
    source_assessment_id:  str


class ValidationResult(BaseModel):
    is_valid:  bool
    errors:    List[str]
    warnings:  List[str]