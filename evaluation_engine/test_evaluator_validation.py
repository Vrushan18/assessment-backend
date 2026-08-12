import json
from datetime import datetime

from assessment_package.schemas import AssessmentPackage, Question
from context_processor.schemas import (
    CandidateContextObject,
    DomainEnum,
    LevelEnum,
    BloomEnum,
)
from evaluation_engine.grading import CandidateResponse
from evaluation_engine.schemas import CriterionScore
from evaluation_engine.evaluator import grade_assessment


with open(
    "question_engine/question_bank.json",
    encoding="utf-8"
) as f:
    raw_questions = json.load(f)

questions = [
    Question(**q)
    for q in raw_questions[:10]
]

counts = {
    "C1": 0,
    "C2": 0,
    "C3": 0,
    "C4": 0,
    "C5": 0,
    "C6": 0,
}

for q in questions:
    counts[q.competency_criterion.value] += 1


context = CandidateContextObject(
    candidate_id="TEST-VALIDATION",
    domain=DomainEnum.engineering,
    certification_level=LevelEnum.L1,
    bloom_target=BloomEnum.apply,
    background="Evaluator validation test.",
    eligibility_confirmed=True,
    timestamp=datetime.fromisoformat(
        "2026-08-12T21:00:00"
    ),
    source_assessment_id="TEST-VALIDATION-ASSESSMENT",
)


package = AssessmentPackage(
    package_id="TEST-VALIDATION-PACKAGE",
    candidate_context=context,
    questions=questions,
    scenario_id="TEST-VALIDATION-SCENARIO",
    created_at=datetime.fromisoformat(
        "2026-08-12T21:00:00"
    ),
    total_c1_count=counts["C1"],
    total_c2_count=counts["C2"],
    total_c3_count=counts["C3"],
    total_c4_count=counts["C4"],
    total_c5_count=counts["C5"],
    total_c6_count=counts["C6"],
)


responses = [
    CandidateResponse(
        question_id=q.question_id,
        response="Test candidate response."
    )
    for q in questions
]


class FakeGrader:

    def grade_response(
        self,
        question,
        candidate_response,
        rubrics,
    ):
        return CriterionScore(
            question_id=question.question_id,
            criterion=question.competency_criterion.value,
            score=8.0,
            confidence=0.9,
            rationale="Validation test.",
            rubric_reference="TEST-RUBRIC",
        )


def fake_retriever(question, candidate_context):
    return [
        {
            "id": "TEST-RUBRIC",
            "document": "Validation rubric."
        }
    ]


print("=== TEST 1: Missing response ===")

missing = responses[:-1]

try:
    grade_assessment(
        package,
        missing,
        fake_retriever,
        FakeGrader(),
    )
    print("FAIL: missing response was accepted")
except ValueError as e:
    print("PASS:", e)


print()
print("=== TEST 2: Duplicate response ===")

duplicate = responses + [
    CandidateResponse(
        question_id=responses[0].question_id,
        response="Duplicate response."
    )
]

try:
    grade_assessment(
        package,
        duplicate,
        fake_retriever,
        FakeGrader(),
    )
    print("FAIL: duplicate response was accepted")
except ValueError as e:
    print("PASS:", e)


print()
print("=== TEST 3: Missing rubric ===")


def empty_retriever(question, candidate_context):
    return []


try:
    grade_assessment(
        package,
        responses,
        empty_retriever,
        FakeGrader(),
    )
    print("FAIL: missing rubric was accepted")
except ValueError as e:
    print("PASS:", e)


print()
print("=== VALIDATION TESTS COMPLETE ===")