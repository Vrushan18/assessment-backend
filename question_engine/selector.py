import itertools
import json
from pathlib import Path
from typing import List, Optional

from assessment_package.schemas import Question
from mapping_engine.schemas import MappedContext
from scenario_engine.schemas import Scenario

QUESTION_BANK_PATH = Path(__file__).resolve().parent / "question_bank.json"


def load_questions() -> List[Question]:
    """Load and validate questions from the question bank."""
    if not QUESTION_BANK_PATH.exists():
        raise FileNotFoundError(f"Question bank not found: {QUESTION_BANK_PATH}")

    with open(QUESTION_BANK_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Question bank must contain a JSON array")

    return [Question(**item) for item in data]


def _is_l2_or_higher(pathway_id: str) -> bool:
    pathway = pathway_id.upper()
    return any(level in pathway for level in ("_L2", "_L3", "_L4"))


def _domain_matches(question: Question, scenario: Scenario) -> bool:
    return question.domain.lower() == scenario.domain.lower()


def _criterion_matches(question: Question, scenario: Scenario) -> bool:
    return question.competency_criterion.value in scenario.criteria


def _target_counts(distribution: dict, total: int) -> dict:
    """Convert proportional weights/distributions into integer targets."""
    if not distribution:
        return {}

    positive = {k: float(v) for k, v in distribution.items() if float(v) > 0}
    if not positive:
        return {}

    raw = {k: positive[k] / sum(positive.values()) * total for k in positive}
    targets = {k: int(raw[k]) for k in raw}
    remainder = total - sum(targets.values())

    for key, _ in sorted(
        raw.items(), key=lambda item: item[1] - int(item[1]), reverse=True
    )[:remainder]:
        targets[key] += 1

    return targets


def _exact_distribution_possible(
    candidates: List[Question],
    target_count: int,
    criterion_targets: dict,
    difficulty_targets: dict,
    bloom_targets: dict,
) -> Optional[List[Question]]:
    """Find an exact quota-matching subset when one exists.

    Domain banks are intentionally small (currently 25 per domain), so
    exhaustive combinations are practical and make quota compliance explicit.
    """
    if len(candidates) < target_count:
        return None

    for combo in itertools.combinations(candidates, target_count):
        criterion_counts = {}
        difficulty_counts = {}
        bloom_counts = {}

        for q in combo:
            c = q.competency_criterion.value
            d = q.difficulty.value
            b = q.bloom_level
            criterion_counts[c] = criterion_counts.get(c, 0) + 1
            difficulty_counts[d] = difficulty_counts.get(d, 0) + 1
            bloom_counts[b] = bloom_counts.get(b, 0) + 1

        if criterion_targets and criterion_counts != criterion_targets:
            continue
        if difficulty_targets and difficulty_counts != difficulty_targets:
            continue
        if bloom_targets and bloom_counts != bloom_targets:
            continue

        return list(combo)

    return None


def _ranked_fallback(
    candidates: List[Question],
    target_count: int,
    criterion_targets: dict,
    difficulty_targets: dict,
    bloom_targets: dict,
) -> List[Question]:
    """Fallback selection that minimizes quota deviations."""
    selected = []
    remaining = list(candidates)
    counts = {"criterion": {}, "difficulty": {}, "bloom": {}}

    for _ in range(min(target_count, len(remaining))):
        best = None
        best_score = None

        for question in remaining:
            c = question.competency_criterion.value
            d = question.difficulty.value
            b = question.bloom_level

            score = (
                1000 if counts["criterion"].get(c, 0) < criterion_targets.get(c, 0) else 0,
                100 if counts["difficulty"].get(d, 0) < difficulty_targets.get(d, 0) else 0,
                10 if counts["bloom"].get(b, 0) < bloom_targets.get(b, 0) else 0,
                1 if question.durability_flag else 0,
                1 if question.governance_flag else 0,
            )

            if best_score is None or score > best_score:
                best_score = score
                best = question

        selected.append(best)
        remaining.remove(best)

        c = best.competency_criterion.value
        d = best.difficulty.value
        b = best.bloom_level
        counts["criterion"][c] = counts["criterion"].get(c, 0) + 1
        counts["difficulty"][d] = counts["difficulty"].get(d, 0) + 1
        counts["bloom"][b] = counts["bloom"].get(b, 0) + 1

    return selected


def select_questions(
    mapped_context: MappedContext,
    scenario: Scenario,
    question_bank: Optional[List[Question]] = None,
) -> List[Question]:
    """
    Select questions using the documented order:
    domain -> criterion balance -> Bloom -> difficulty -> durability -> governance.

    For L2+, governance-aware and durable questions are required.
    Criterion, difficulty, and Bloom targets are matched exactly when feasible.
    """
    if question_bank is None:
        question_bank = load_questions()

    target_count = mapped_context.question_count_target
    if target_count <= 0:
        raise ValueError("Question count target must be greater than zero")

    candidates = [
        q for q in question_bank
        if _domain_matches(q, scenario)
    ]

    if _is_l2_or_higher(mapped_context.pathway_id):
        candidates = [q for q in candidates if q.governance_flag]

    # Durability is an eligibility requirement, not merely a score bonus.
    candidates = [q for q in candidates if q.durability_flag]

    if len(candidates) < target_count:
        raise ValueError(
            f"Unable to select {target_count} questions. "
            f"Only {len(candidates)} suitable questions available."
        )

    criterion_targets = _target_counts(
        mapped_context.c_weights, target_count
    )
    difficulty_targets = {
        k: int(v)
        for k, v in mapped_context.difficulty_distribution.items()
        if int(v) > 0
    }
    bloom_targets = {
        k: int(v)
        for k, v in mapped_context.bloom_distribution.items()
        if int(v) > 0
    }

    selected = _exact_distribution_possible(
        candidates,
        target_count,
        criterion_targets,
        difficulty_targets,
        bloom_targets,
    )

    if selected is None:
        selected = _ranked_fallback(
            candidates,
            target_count,
            criterion_targets,
            difficulty_targets,
            bloom_targets,
        )

    if len(selected) < target_count:
        raise ValueError(
            f"Unable to select {target_count} questions. "
            f"Only {len(selected)} suitable questions available."
        )

    return selected[:target_count]