from datetime import datetime, timezone
from typing import Callable, Dict, List, Any

from assessment_package.schemas import AssessmentPackage
from evaluation_engine.grading import CandidateResponse
from evaluation_engine.grader import PECSGrader
from evaluation_engine.schemas import (
    CriterionScore,
    ScoredResult,
    SkillTier,
)
from evaluation_engine.aggregate import compute_aggregate


CONFIDENCE_REVIEW_THRESHOLD = 0.65


def _skill_tier(score: float) -> SkillTier:
    """
    Convert the final PECS score into the documented skill tier.
    """

    if score < 4.0:
        return SkillTier.WEAK

    if score < 6.0:
        return SkillTier.DEVELOPING

    if score < 8.0:
        return SkillTier.PROFICIENT

    return SkillTier.EXPERT


def _build_explanation(
    aggregate_scores: Dict[str, float],
    overall_score: float,
    skill_tier: SkillTier,
    c5_veto_triggered: bool,
) -> str:
    """
    Build a deterministic explanation from the scored result.

    The explanation does not ask the LLM to determine the final score.
    """

    if c5_veto_triggered:
        return (
            "The assessment triggered the C5 governance veto because "
            "the candidate demonstrated a critical deficiency in AI "
            "governance and ethics. The overall result is therefore "
            "restricted to 0.0 regardless of other competency scores."
        )

    non_zero = {
        criterion: score
        for criterion, score in aggregate_scores.items()
        if score > 0
    }

    if non_zero:
        strongest = max(
            non_zero,
            key=non_zero.get,
        )

        weakest = min(
            non_zero,
            key=non_zero.get,
        )

        return (
            f"The candidate achieved an overall score of "
            f"{overall_score:.2f}, corresponding to the "
            f"{skill_tier.value} skill tier. "
            f"The strongest weighted competency contribution was "
            f"{strongest}, while the weakest was {weakest}. "
            f"Further improvement should focus on strengthening "
            f"the lowest-performing competency while maintaining "
            f"the demonstrated strengths."
        )

    return (
        f"The candidate achieved an overall score of "
        f"{overall_score:.2f}, corresponding to the "
        f"{skill_tier.value} skill tier. "
        f"No positive competency contribution was recorded."
    )


def _retrieve_rubrics(
    rubric_retriever: Any,
    question,
    candidate_context,
):
    """
    Retrieve rubrics using an injected retriever.

    The evaluator does not depend directly on ChromaDB.
    """

    if rubric_retriever is None:
        raise ValueError(
            "A rubric retriever is required for assessment grading."
        )

    # Preferred interface:
    # retriever(question, candidate_context)
    if callable(rubric_retriever):
        return rubric_retriever(
            question,
            candidate_context,
        )

    # Object interface:
    # retriever.retrieve(question, candidate_context)
    if hasattr(rubric_retriever, "retrieve"):
        return rubric_retriever.retrieve(
            question,
            candidate_context,
        )

    raise TypeError(
        "rubric_retriever must be callable or provide "
        "a retrieve() method."
    )


def grade_assessment(
    package: AssessmentPackage,
    candidate_responses: List[CandidateResponse],
    rubric_retriever,
    grader: PECSGrader,
) -> ScoredResult:
    """
    Grade a complete PECS assessment.

    Pipeline:

        AssessmentPackage
              ↓
        Candidate responses
              ↓
        Rubric retrieval
              ↓
        PECSGrader
              ↓
        CriterionScore[]
              ↓
        C1-C6 aggregation
              ↓
        C5 governance veto
              ↓
        Overall score
              ↓
        Skill tier
              ↓
        ScoredResult
    """

    if not candidate_responses:
        raise ValueError(
            "Cannot grade an assessment without candidate responses."
        )

    if not package.questions:
        raise ValueError(
            "Cannot grade an assessment without questions."
        )

    # ---------------------------------------------------------
    # Build response lookup
    # ---------------------------------------------------------

    response_map: Dict[str, CandidateResponse] = {}

    for response in candidate_responses:

        if response.question_id in response_map:
            raise ValueError(
                f"Duplicate candidate response for question "
                f"{response.question_id}."
            )

        response_map[response.question_id] = response

    # ---------------------------------------------------------
    # Validate that every assessment question has a response
    # ---------------------------------------------------------

    missing_questions = [
        question.question_id
        for question in package.questions
        if question.question_id not in response_map
    ]

    if missing_questions:
        raise ValueError(
            "Missing candidate responses for questions: "
            + ", ".join(missing_questions)
        )

    # ---------------------------------------------------------
    # Grade every question
    # ---------------------------------------------------------

    question_scores: List[CriterionScore] = []

    for question in package.questions:

        candidate_response = response_map[
            question.question_id
        ]

        rubrics = _retrieve_rubrics(
            rubric_retriever=rubric_retriever,
            question=question,
            candidate_context=package.candidate_context,
        )

        if not rubrics:
            raise ValueError(
                f"No rubric found for question "
                f"{question.question_id}."
            )

        score = grader.grade_response(
            question=question,
            candidate_response=candidate_response,
            rubrics=rubrics,
        )

        question_scores.append(score)

    # ---------------------------------------------------------
    # Aggregate C1-C6
    # ---------------------------------------------------------

    c_weights = {
        "C1": 0.20,
        "C2": 0.20,
        "C3": 0.20,
        "C4": 0.20,
        "C5": 0.10,
        "C6": 0.10,
    }

    aggregate_scores = compute_aggregate(
        question_scores,
        c_weights,
    )

    # ---------------------------------------------------------
    # Calculate overall score
    # ---------------------------------------------------------

    overall_score = sum(
        aggregate_scores.values()
    )

    # Keep floating-point artifacts from appearing in output.
    overall_score = round(
        overall_score,
        4,
    )

    # ---------------------------------------------------------
    # Calculate confidence
    # ---------------------------------------------------------

    confidence_overall = sum(
        score.confidence
        for score in question_scores
    ) / len(question_scores)

    confidence_overall = round(
        confidence_overall,
        4,
    )

    # ---------------------------------------------------------
    # C5 GOVERNANCE VETO
    # ---------------------------------------------------------

    c5_veto_triggered = any(
        score.criterion == "C5"
        and score.score <= 1.0
        for score in question_scores
    )

    if c5_veto_triggered:
        overall_score = 0.0

    # ---------------------------------------------------------
    # Skill tier
    # ---------------------------------------------------------

    skill_tier = _skill_tier(
        overall_score
    )

    # ---------------------------------------------------------
    # Explanation
    # ---------------------------------------------------------

    explanation = _build_explanation(
        aggregate_scores=aggregate_scores,
        overall_score=overall_score,
        skill_tier=skill_tier,
        c5_veto_triggered=c5_veto_triggered,
    )

    # ---------------------------------------------------------
    # Final result
    # ---------------------------------------------------------

    return ScoredResult(
        candidate_id=package.candidate_context.candidate_id,
        package_id=package.package_id,
        question_scores=question_scores,
        aggregate_scores=aggregate_scores,
        overall_score=overall_score,
        skill_tier=skill_tier,
        confidence_overall=confidence_overall,
        c5_veto_triggered=c5_veto_triggered,
        explanation=explanation,
        graded_at=datetime.now(timezone.utc),
    )