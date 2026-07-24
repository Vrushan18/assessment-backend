# File: context_processor/schemas.py

from enum import Enum
from typing import List
from pydantic import BaseModel, ConfigDict, Field


class DomainEnum(str, Enum):
    ENGINEERING = "Engineering"
    SCIENCE = "Science"
    COMMERCE = "Commerce"
    ARTS = "Arts"


class LevelEnum(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


class CandidateContextObject(BaseModel):
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "candidate_id": "CAND-1001",
                "domain": "Engineering",
                "level": "L2",
                "eligibility_confirmed": True,
                "criteria_focus": ["C1", "C2"]
            }
        }
    )

    candidate_id: str = Field(
        ..., 
        description="Unique identifier for the candidate"
    )
    domain: DomainEnum = Field(
        ..., 
        description="Target academic or professional domain"
    )
    level: LevelEnum = Field(
        ..., 
        description="Assessment proficiency level (L1-L4)"
    )
    eligibility_confirmed: bool = Field(
        ..., 
        description="Must be True to pass validation"
    )
    criteria_focus: List[str] = Field(
        default_factory=list, 
        description="Focus criteria codes, e.g., ['C1', 'C2']"
    )