from typing import List, Dict, Any

from pydantic import BaseModel

from assessment_package.schemas import Question
from evaluation_engine.schemas import CriterionScore


class CandidateResponse(BaseModel):
    question_id: str
    response: str


class EvaluationRequest(BaseModel):
    package_id: str
    responses: List[CandidateResponse]


class GradingInput(BaseModel):
    question: Question
    candidate_response: CandidateResponse
    rubric: Dict[str, Any]


def grade_mcq(
    question: Question,
    candidate_response: CandidateResponse,
) -> CriterionScore:
    """
    Deterministically grade an MCQ response.
    """

    if question.question_type.value != "MCQ":
        raise ValueError(
            f"Question {question.question_id} is not an MCQ."
        )

    if question.correct_answer_index is None:
        raise ValueError(
            f"Question {question.question_id} has no correct answer index."
        )

    if candidate_response.question_id != question.question_id:
        raise ValueError(
            "Candidate response question_id does not match "
            "the question being graded."
        )

    try:
        selected_index = int(candidate_response.response)
    except ValueError:
        raise ValueError(
            "MCQ response must contain a numeric option index."
        )

    if selected_index < 0:
        raise ValueError(
            "MCQ option index cannot be negative."
        )

    score = (
        10.0
        if selected_index == question.correct_answer_index
        else 0.0
    )

    return CriterionScore(
        question_id=question.question_id,
        criterion=question.competency_criterion.value,
        score=score,
        confidence=1.0,
        rationale=(
            "Candidate selected the correct option."
            if score == 10.0
            else "Candidate selected an incorrect option."
        ),
        rubric_reference="deterministic_mcq_key",
    )