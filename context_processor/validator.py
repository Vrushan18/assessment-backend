# File: context_processor/validator.py

from typing import Dict, Any, List
from context_processor.schemas import CandidateContextObject


def validate_context(context: CandidateContextObject) -> Dict[str, Any]:
    """
    Executes sequential validation rules against a CandidateContextObject.
    """
    errors: List[str] = []

    # Check 1: Candidate Eligibility Flag
    if not context.eligibility_confirmed:
        errors.append("Candidate eligibility is not confirmed.")

    # Check 2: Criteria Focus List
    if not context.criteria_focus:
        errors.append("Criteria focus list cannot be empty.")

    # Check 3: Candidate ID String Integrity
    if not context.candidate_id or not context.candidate_id.strip():
        errors.append("Candidate ID cannot be empty or whitespace.")

    # Overall validation flag
    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "errors": errors,
        "candidate_id": context.candidate_id,
        "domain": context.domain,
        "level": context.level
    }