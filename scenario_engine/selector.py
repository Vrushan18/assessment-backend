import json
from pathlib import Path
from typing import List

from mapping_engine.schemas import MappedContext
from scenario_engine.schemas import Scenario


SCENARIOS_FILE = Path(__file__).resolve().parent.parent / "scenarios.json"


def load_scenarios() -> List[Scenario]:
    with open(SCENARIOS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return [Scenario(**item) for item in data]


def select_scenario(mapped_context: MappedContext) -> Scenario:
    scenarios = load_scenarios()

    if not scenarios:
        raise ValueError("No scenarios available")

    # Extract domain from pathway_id, e.g. Engineering_L2
    pathway_parts = mapped_context.pathway_id.split("_")
    candidate_domain = pathway_parts[0] if pathway_parts else ""

    # Get the target difficulty from Member 2's distribution
    difficulty_distribution = mapped_context.difficulty_distribution

    if difficulty_distribution:
        candidate_difficulty = max(
            difficulty_distribution,
            key=difficulty_distribution.get
        )
    else:
        candidate_difficulty = ""

    # Criteria with non-zero weights
    candidate_criteria = {
        criterion
        for criterion, weight in mapped_context.c_weights.items()
        if weight > 0
    }

    best_scenario = None
    best_score = -1

    for scenario in scenarios:
        domain_match = int(
            scenario.domain.lower() == candidate_domain.lower()
        )

        difficulty_match = int(
            scenario.difficulty.lower() == candidate_difficulty.lower()
        )

        criteria_overlap_count = len(
            candidate_criteria.intersection(scenario.criteria)
        )

        score = (
            (domain_match * 3)
            + (difficulty_match * 2)
            + (criteria_overlap_count * 1)
        )

        if score > best_score:
            best_score = score
            best_scenario = scenario

    if best_scenario is None:
        raise ValueError("Unable to select a scenario")

    return best_scenario