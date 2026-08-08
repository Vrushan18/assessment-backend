from typing import Dict, List
from pydantic import BaseModel


class MappedContext(BaseModel):
    pathway_id: str

    c_weights: Dict[str, float]

    question_count_target: int

    difficulty_distribution: Dict[str, int]

    bloom_distribution: Dict[str, int]

    scenario_tags: List[str]