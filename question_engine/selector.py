import itertools
import json
from pathlib import Path
from typing import List, Optional

from assessment_package.schemas import Question
from mapping_engine.schemas import MappedContext
from scenario_engine.schemas import Scenario


QUESTION_BANK_PATH = Path(__file__).resolve().parent / "question_bank.json"

VALID_BLOOM_LEVELS = {
    "Remember",
    "Understand",
    "Apply",
    "Analyse",
    "Evaluate",
    "Create",
}

VALID_DIFFICULTIES = {
    "Easy",
    "Medium",
    "Hard",
}

VALID_CRITERIA = {
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C6",
}


def load_questions() -> List[Question]:
    """Load and validate questions from the question bank."""
    if not QUESTION_BANK_PATH.exists():
        raise FileNotFoundError(
            f"Question bank not found: {QUESTION_BANK_PATH}"
        )

    with open(QUESTION_BANK_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Question bank must contain a JSON array")

    questions = [Question(**item) for item in data]

    # Basic metadata integrity validation.
    ids = [q.question_id for q in questions]

    if len(ids) != len(set(ids)):
        raise ValueError("Question bank contains duplicate question IDs")

    for q in questions:
        if q.bloom_level not in VALID_BLOOM_LEVELS:
            raise ValueError(
                f"Invalid Bloom level for {q.question_id}: "
                f"{q.bloom_level}"
            )

        if q.difficulty.value not in VALID_DIFFICULTIES:
            raise ValueError(
                f"Invalid difficulty for {q.question_id}: "
                f"{q.difficulty.value}"
            )

        if q.competency_criterion.value not in VALID_CRITERIA:
            raise ValueError(
                f"Invalid competency criterion for {q.question_id}: "
                f"{q.competency_criterion.value}"
            )

        if not isinstance(q.durability_flag, bool):
            raise ValueError(
                f"Invalid durability_flag for {q.question_id}"
            )

        if not isinstance(q.governance_flag, bool):
            raise ValueError(
                f"Invalid governance_flag for {q.question_id}"
            )

    return questions


def _is_l2_or_higher(pathway_id: str) -> bool:
    pathway = pathway_id.upper()
    return any(
        level in pathway
        for level in ("_L2", "_L3", "_L4")
    )


def _domain_matches(
    question: Question,
    scenario: Scenario,
) -> bool:
    return (
        question.domain.lower()
        == scenario.domain.lower()
    )


def _criterion_matches(
    question: Question,
    scenario: Scenario,
) -> bool:
    return (
        question.competency_criterion.value
        in scenario.criteria
    )


def _target_counts(
    distribution: dict,
    total: int,
) -> dict:
    """
    Convert proportional competency weights into exact
    integer targets using largest-remainder allocation.
    """
    if not distribution:
        return {}

    positive = {
        key: float(value)
        for key, value in distribution.items()
        if float(value) > 0
    }

    if not positive:
        return {}

    raw = {
        key: positive[key]
        / sum(positive.values())
        * total
        for key in positive
    }

    targets = {
        key: int(value)
        for key, value in raw.items()
    }

    remainder = total - sum(targets.values())

    ordered = sorted(
        raw.items(),
        key=lambda item: (
            item[1] - int(item[1])
        ),
        reverse=True,
    )

    for key, _ in ordered[:remainder]:
        targets[key] += 1

    return targets


def _count_dimensions(
    questions: List[Question],
) -> tuple[dict, dict, dict]:
    criterion_counts = {}
    difficulty_counts = {}
    bloom_counts = {}

    for question in questions:
        criterion = question.competency_criterion.value
        difficulty = question.difficulty.value
        bloom = question.bloom_level

        criterion_counts[criterion] = (
            criterion_counts.get(criterion, 0) + 1
        )

        difficulty_counts[difficulty] = (
            difficulty_counts.get(difficulty, 0) + 1
        )

        bloom_counts[bloom] = (
            bloom_counts.get(bloom, 0) + 1
        )

    return (
        criterion_counts,
        difficulty_counts,
        bloom_counts,
    )


def _exact_distribution_possible(
    candidates: List[Question],
    target_count: int,
    criterion_targets: dict,
    difficulty_targets: dict,
    bloom_targets: dict,
) -> Optional[List[Question]]:
    """
    Find an exact quota-matching subset.

    IMPORTANT:
    There is deliberately NO fallback. A non-compliant
    assessment must never be returned as successful.
    """
    if len(candidates) < target_count:
        return None

    # Fast capacity checks before combinations.
    for criterion, target in criterion_targets.items():
        available = sum(
            q.competency_criterion.value == criterion
            for q in candidates
        )
        if available < target:
            return None

    for difficulty, target in difficulty_targets.items():
        available = sum(
            q.difficulty.value == difficulty
            for q in candidates
        )
        if available < target:
            return None

    for bloom, target in bloom_targets.items():
        available = sum(
            q.bloom_level == bloom
            for q in candidates
        )
        if available < target:
            return None

    for combo in itertools.combinations(
        candidates,
        target_count,
    ):
        criterion_counts, difficulty_counts, bloom_counts = (
            _count_dimensions(list(combo))
        )

        if criterion_counts != criterion_targets:
            continue

        if difficulty_counts != difficulty_targets:
            continue

        if bloom_counts != bloom_targets:
            continue

        return list(combo)

    return None


def _format_capacity(
    candidates: List[Question],
) -> str:
    criterion_counts, difficulty_counts, bloom_counts = (
        _count_dimensions(candidates)
    )

    return (
        f"available_count={len(candidates)}, "
        f"criteria={criterion_counts}, "
        f"difficulty={difficulty_counts}, "
        f"bloom={bloom_counts}"
    )


def select_questions(
    mapped_context: MappedContext,
    scenario: Scenario,
    question_bank: Optional[List[Question]] = None,
) -> List[Question]:
    """
    Strict Question Selection.

    Selection requirements:
      1. Correct domain
      2. Durability required for all pathways
      3. Governance required for L2+
      4. Exact competency distribution
      5. Exact difficulty distribution
      6. Exact Bloom distribution

    If the requirements cannot be satisfied, the function
    raises ValueError.

    It NEVER returns a best-effort/non-compliant package.
    """

    if question_bank is None:
        question_bank = load_questions()

    target_count = mapped_context.question_count_target

    if target_count <= 0:
        raise ValueError(
            "Question count target must be greater than zero"
        )

    # ---------------------------------------------------------
    # 1. Domain filter
    # ---------------------------------------------------------
    candidates = [
        question
        for question in question_bank
        if _domain_matches(question, scenario)
    ]

    # ---------------------------------------------------------
    # 2. Durability filter
    # ---------------------------------------------------------
    candidates = [
        question
        for question in candidates
        if question.durability_flag is True
    ]

    # ---------------------------------------------------------
    # 3. Governance filter for L2+
    # ---------------------------------------------------------
    if _is_l2_or_higher(mapped_context.pathway_id):
        candidates = [
            question
            for question in candidates
            if question.governance_flag is True
        ]

    # ---------------------------------------------------------
    # 4. Build exact targets
    # ---------------------------------------------------------
    criterion_targets = _target_counts(
        mapped_context.c_weights,
        target_count,
    )

    difficulty_targets = {
        key: int(value)
        for key, value
        in mapped_context.difficulty_distribution.items()
        if int(value) > 0
    }

    bloom_targets = {
        key: int(value)
        for key, value
        in mapped_context.bloom_distribution.items()
        if int(value) > 0
    }

    # ---------------------------------------------------------
    # 5. Capacity check
    # ---------------------------------------------------------
    if len(candidates) < target_count:
        raise ValueError(
            f"Unable to assemble {mapped_context.pathway_id}. "
            f"Required question count={target_count}; "
            f"eligible questions={len(candidates)}. "
            f"{_format_capacity(candidates)}"
        )

    # ---------------------------------------------------------
    # 6. Exact selection
    # ---------------------------------------------------------
    selected = _exact_distribution_possible(
        candidates=candidates,
        target_count=target_count,
        criterion_targets=criterion_targets,
        difficulty_targets=difficulty_targets,
        bloom_targets=bloom_targets,
    )

    # ---------------------------------------------------------
    # 7. STRICT FAILURE
    # ---------------------------------------------------------
    if selected is None:
        _, available_difficulty, available_bloom = (
            _count_dimensions(candidates)
        )

        raise ValueError(
            f"Unable to assemble compliant assessment "
            f"for {mapped_context.pathway_id}. "
            f"Required count={target_count}; "
            f"required criteria={criterion_targets}; "
            f"required difficulty={difficulty_targets}; "
            f"required bloom={bloom_targets}; "
            f"eligible capacity={_format_capacity(candidates)}; "
            f"available difficulty={available_difficulty}; "
            f"available bloom={available_bloom}. "
            f"No non-compliant fallback is permitted."
        )

    # ---------------------------------------------------------
    # 8. Final defensive validation
    # ---------------------------------------------------------
    if len(selected) != target_count:
        raise ValueError(
            "Internal selection error: selected question count "
            "does not equal target count."
        )

    criterion_counts, difficulty_counts, bloom_counts = (
        _count_dimensions(selected)
    )

    if criterion_counts != criterion_targets:
        raise ValueError(
            "Internal validation failed: competency distribution "
            "does not match mapped requirement."
        )

    if difficulty_counts != difficulty_targets:
        raise ValueError(
            "Internal validation failed: difficulty distribution "
            "does not match mapped requirement."
        )

    if bloom_counts != bloom_targets:
        raise ValueError(
            "Internal validation failed: Bloom distribution "
            "does not match mapped requirement."
        )

    # Defensive durability/governance verification.
    if not all(
        question.durability_flag is True
        for question in selected
    ):
        raise ValueError(
            "Internal validation failed: selected questions "
            "contain a non-durable question."
        )

    if _is_l2_or_higher(mapped_context.pathway_id):
        if not all(
            question.governance_flag is True
            for question in selected
        ):
            raise ValueError(
                "Internal validation failed: L2+ selection "
                "contains a question without governance_flag=true."
            )

    return selected