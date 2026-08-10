from datetime import datetime, timezone
from uuid import uuid4

from assessment_package.schemas import (
    AssessmentPackage,
    Question
)

from context_processor.schemas import (
    CandidateContextObject
)

from scenario_engine.schemas import Scenario


def assemble_package(
    candidate_context: CandidateContextObject,
    scenario: Scenario,
    questions: list[Question]
) -> AssessmentPackage:
    """
    Assemble the final AssessmentPackage.

    Includes:
    - unique package ID
    - candidate context
    - selected questions
    - scenario ID
    - creation timestamp
    - C1-C6 competency counts
    """

    if not questions:
        raise ValueError(
            "Cannot create assessment package without questions"
        )

    # ---------------------------------------------------------
    # Count questions for each competency criterion
    # ---------------------------------------------------------

    counts = {
        "C1": 0,
        "C2": 0,
        "C3": 0,
        "C4": 0,
        "C5": 0,
        "C6": 0
    }

    for question in questions:

        criterion = question.competency_criterion.value

        if criterion not in counts:
            raise ValueError(
                f"Invalid competency criterion: {criterion}"
            )

        counts[criterion] += 1

    # ---------------------------------------------------------
    # Integrity check
    # ---------------------------------------------------------

    total_criterion_count = sum(counts.values())

    if total_criterion_count != len(questions):
        raise ValueError(
            "Assessment package integrity check failed: "
            "competency counts do not equal question count"
        )

    # ---------------------------------------------------------
    # Create AssessmentPackage
    # ---------------------------------------------------------

    package = AssessmentPackage(
        package_id=str(uuid4()),
        candidate_context=candidate_context,
        questions=questions,
        scenario_id=scenario.scenario_id,
        created_at=datetime.now(timezone.utc),

        total_c1_count=counts["C1"],
        total_c2_count=counts["C2"],
        total_c3_count=counts["C3"],
        total_c4_count=counts["C4"],
        total_c5_count=counts["C5"],
        total_c6_count=counts["C6"]
    )

    return package