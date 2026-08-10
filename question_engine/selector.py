import json
from pathlib import Path
from typing import List, Optional

from assessment_package.schemas import Question
from mapping_engine.schemas import MappedContext
from scenario_engine.schemas import Scenario


QUESTION_BANK_PATH = (
    Path(__file__).resolve().parent / "question_bank.json"
)


def load_questions() -> List[Question]:
    """Load and validate questions from the question bank."""

    if not QUESTION_BANK_PATH.exists():
        raise FileNotFoundError(
            f"Question bank not found: {QUESTION_BANK_PATH}"
        )

    with open(QUESTION_BANK_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "Question bank must contain a JSON array"
        )

    return [Question(**item) for item in data]


def _is_l2_or_higher(pathway_id: str) -> bool:
    """Check whether the assessment is L2, L3, or L4."""

    pathway = pathway_id.upper()

    return any(
        level in pathway
        for level in ("_L2", "_L3", "_L4")
    )


def _domain_matches(
    question: Question,
    scenario: Scenario
) -> bool:
    return (
        question.domain.lower()
        == scenario.domain.lower()
    )


def _criterion_matches(
    question: Question,
    scenario: Scenario
) -> bool:
    return (
        question.competency_criterion.value
        in scenario.criteria
    )


def _bloom_matches(
    question: Question,
    mapped_context: MappedContext
) -> bool:
    """Check whether the question's Bloom level is required."""

    required_levels = [
        level
        for level, count
        in mapped_context.bloom_distribution.items()
        if count > 0
    ]

    if not required_levels:
        return True

    return question.bloom_level in required_levels


def _governance_allowed(
    question: Question,
    mapped_context: MappedContext
) -> bool:
    """
    L2+ assessments require governance-aware questions.
    L1 does not use governance as a restriction.
    """

    if _is_l2_or_higher(mapped_context.pathway_id):
        return question.governance_flag

    return True


def _score_question(
    question: Question,
    mapped_context: MappedContext,
    scenario: Scenario
) -> int:
    """
    Calculate question suitability score.

    Domain match       = +3
    Criterion match    = +2
    Bloom match        = +2
    Durable question   = +1
    Governance aware   = +1
    """

    score = 0

    if _domain_matches(question, scenario):
        score += 3

    if _criterion_matches(question, scenario):
        score += 2

    if _bloom_matches(question, mapped_context):
        score += 2

    if question.durability_flag:
        score += 1

    if question.governance_flag:
        score += 1

    return score


def select_questions(
    mapped_context: MappedContext,
    scenario: Scenario,
    question_bank: Optional[List[Question]] = None
) -> List[Question]:
    """
    Select questions using:
    - domain
    - competency criteria
    - Bloom level
    - difficulty distribution
    - durability
    - governance
    """

    if question_bank is None:
        question_bank = load_questions()

    if not question_bank:
        raise ValueError("No questions available")

    target_count = mapped_context.question_count_target

    if target_count <= 0:
        raise ValueError(
            "Question count target must be greater than zero"
        )

    # ---------------------------------------------------------
    # 1. Domain filtering
    # ---------------------------------------------------------

    candidates = [
        question
        for question in question_bank
        if _domain_matches(question, scenario)
    ]

    if not candidates:
        raise ValueError(
            f"No questions available for domain: "
            f"{scenario.domain}"
        )

    # ---------------------------------------------------------
    # 2. Governance filtering for L2+
    # ---------------------------------------------------------

    if _is_l2_or_higher(mapped_context.pathway_id):

        governance_candidates = [
            question
            for question in candidates
            if question.governance_flag
        ]

        if governance_candidates:
            candidates = governance_candidates

    # ---------------------------------------------------------
    # 3. Score candidates
    # ---------------------------------------------------------

    scored_questions = [
        (
            _score_question(
                question,
                mapped_context,
                scenario
            ),
            question
        )
        for question in candidates
    ]

    scored_questions.sort(
        key=lambda item: item[0],
        reverse=True
    )

    # ---------------------------------------------------------
    # 4. Follow difficulty distribution
    # ---------------------------------------------------------

    selected = []
    used_ids = set()

    for difficulty, required_count in (
        mapped_context.difficulty_distribution.items()
    ):

        if required_count <= 0:
            continue

        difficulty_candidates = [
            (score, question)
            for score, question in scored_questions
            if (
                question.difficulty.value == difficulty
                and question.question_id not in used_ids
            )
        ]

        selected_for_difficulty = 0

        for _, question in difficulty_candidates:

            if selected_for_difficulty >= required_count:
                break

            selected.append(question)
            used_ids.add(question.question_id)
            selected_for_difficulty += 1

    # ---------------------------------------------------------
    # 5. Fill remaining slots
    # ---------------------------------------------------------

    if len(selected) < target_count:

        remaining = [
            (score, question)
            for score, question in scored_questions
            if question.question_id not in used_ids
        ]

        for _, question in remaining:

            if len(selected) >= target_count:
                break

            selected.append(question)
            used_ids.add(question.question_id)

    # ---------------------------------------------------------
    # 6. Final validation
    # ---------------------------------------------------------

    if len(selected) < target_count:
        raise ValueError(
            f"Unable to select {target_count} questions. "
            f"Only {len(selected)} suitable questions available."
        )

    return selected[:target_count]