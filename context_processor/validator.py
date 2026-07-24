from datetime import datetime
from typing import List, Dict
from context_processor.schemas import (
    CandidateContextObject,
    ValidationResult,
    DomainEnum,
    LevelEnum,
    BloomEnum,
)


BLOOM_LEVEL_RULES: Dict[str, List[str]] = {
    "L1": ["Remember", "Understand", "Apply"],
    "L2": ["Remember", "Understand", "Apply", "Analyse"],
    "L3": ["Remember", "Understand", "Apply", "Analyse", "Evaluate"],
    "L4": ["Remember", "Understand", "Apply", "Analyse", "Evaluate", "Create"],
}

VALID_DOMAINS = [e.value for e in DomainEnum]
VALID_LEVELS  = [e.value for e in LevelEnum]
VALID_BLOOMS  = [e.value for e in BloomEnum]


def parse_dq_output(dq_json: dict) -> dict:
    return {
        "candidate_id": dq_json.get("candidate_id", ""),
        "certification_level": dq_json.get(
            "certification_level",
            dq_json.get("level", "")
        ),
        "domain":       dq_json.get("domain", ""),
        "bloom_target": dq_json.get("bloom_target", ""),
        "background":   dq_json.get("background", ""),
        "eligibility_confirmed": dq_json.get("eligibility_confirmed", False),
        "timestamp":    dq_json.get(
            "timestamp",
            datetime.now().isoformat()
        ),
        "source_assessment_id": dq_json.get("source_assessment_id", ""),
    }


def validate_context(raw: dict) -> ValidationResult:
    errors:   List[str] = []
    warnings: List[str] = []

    required_fields = [
        "candidate_id", "domain", "certification_level",
        "bloom_target", "background", "eligibility_confirmed",
        "timestamp", "source_assessment_id",
    ]
    for field in required_fields:
        if field not in raw or raw[field] is None:
            errors.append(f"Missing required field: '{field}'")

    if errors:
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    if raw["domain"] not in VALID_DOMAINS:
        errors.append(
            f"Invalid domain '{raw['domain']}'. "
            f"Must be one of: {', '.join(VALID_DOMAINS)}"
        )

    if raw["certification_level"] not in VALID_LEVELS:
        errors.append(
            f"Invalid certification_level '{raw['certification_level']}'. "
            f"Must be one of: {', '.join(VALID_LEVELS)}"
        )

    level = raw.get("certification_level")
    bloom = raw.get("bloom_target")
    if level in BLOOM_LEVEL_RULES:
        if bloom not in BLOOM_LEVEL_RULES[level]:
            errors.append(
                f"bloom_target '{bloom}' is not allowed at {level}. "
                f"Allowed values: {BLOOM_LEVEL_RULES[level]}"
            )

    background = raw.get("background", "")
    if len(background) > 500:
        errors.append(
            f"background exceeds 500 characters (got {len(background)})."
        )
    elif len(background) < 20:
        warnings.append(
            f"background is very short ({len(background)} chars). "
            "Scenario matching may be less accurate."
        )

    if not raw.get("eligibility_confirmed", False):
        errors.append(
            "Candidate not eligible — eligibility_confirmed is False."
        )

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


def build_candidate_context(dq_json: dict) -> CandidateContextObject:
    mapped = parse_dq_output(dq_json)
    result = validate_context(mapped)
    if not result.is_valid:
        raise ValueError(f"Validation failed: {result.errors}")
    return CandidateContextObject(**mapped)