from collections import defaultdict
from typing import Dict, List

from evaluation_engine.schemas import CriterionScore


CRITERIA = ("C1", "C2", "C3", "C4", "C5", "C6")


def compute_aggregate(
    question_scores: List[CriterionScore],
    c_weights: Dict[str, float],
) -> Dict[str, float]:
    """
    Calculate weighted C1-C6 criterion scores.

    Each criterion is first averaged across its question scores.
    The average is then multiplied by the mapped criterion weight.

    Returns weighted contributions for C1-C6.
    """

    if not question_scores:
        raise ValueError("Cannot aggregate an empty score list.")

    grouped = defaultdict(list)

    for result in question_scores:
        if result.criterion not in CRITERIA:
            raise ValueError(
                f"Invalid criterion: {result.criterion}"
            )

        grouped[result.criterion].append(result.score)

    weighted_scores = {}

    for criterion in CRITERIA:
        scores = grouped.get(criterion, [])

        if not scores:
            weighted_scores[criterion] = 0.0
            continue

        average_score = sum(scores) / len(scores)

        weight = float(c_weights.get(criterion, 0.0))

        weighted_scores[criterion] = average_score * weight

    return weighted_scores