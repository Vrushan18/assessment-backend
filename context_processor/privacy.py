# File: context_processor/privacy.py

from context_processor.schemas import CandidateContextObject


def anonymize_context(context: CandidateContextObject) -> dict:
    """
    Masks sensitive candidate identifiers for privacy protection
    before passing context downstream to evaluation/AI modules.
    """
    raw_id = context.candidate_id

    # Mask ID: "CAND-1001" -> "C***-1001"
    if len(raw_id) > 4:
        masked_id = raw_id[0] + "***" + raw_id[-4:]
    else:
        masked_id = "***"

    anonymized_data = context.model_dump(mode="json")
    anonymized_data["candidate_id"] = masked_id

    return anonymized_data