from pydantic import BaseModel
from typing import List


class Scenario(BaseModel):
    scenario_id: str
    title: str
    description: str
    domain: str
    difficulty: str
    criteria: List[str]