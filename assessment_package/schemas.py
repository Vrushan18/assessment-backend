from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

from context_processor.schemas import CandidateContextObject


class QuestionTypeEnum(str, Enum):
    mcq        = "MCQ"
    scenario   = "ScenarioBased"
    case_study = "CaseStudy"
    simulation = "Simulation"


class CriterionEnum(str, Enum):
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"
    C5 = "C5"
    C6 = "C6"


class DifficultyEnum(str, Enum):
    easy   = "Easy"
    medium = "Medium"
    hard   = "Hard"


class Question(BaseModel):
    question_id:          str
    question_text:        str
    question_type:        QuestionTypeEnum
    competency_criterion: CriterionEnum
    bloom_level:          str
    difficulty:           DifficultyEnum
    domain:               str
    durability_flag:      bool
    governance_flag:      bool
    options:              Optional[List[str]] = None
    correct_answer_index: Optional[int] = None


class AssessmentPackage(BaseModel):
    package_id:         str
    candidate_context:  CandidateContextObject
    questions:          List[Question] = Field(..., min_length=10, max_length=30)
    scenario_id:        str
    created_at:         datetime
    total_c1_count:     int
    total_c2_count:     int
    total_c3_count:     int
    total_c4_count:     int
    total_c5_count:     int
    total_c6_count:     int