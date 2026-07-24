# File: main.py

from fastapi import FastAPI, HTTPException, status
from context_processor.schemas import CandidateContextObject
from context_processor.validator import validate_context
from context_processor.privacy import anonymize_context

app = FastAPI(
    title="Assessment Backend - Context Processing API",
    description="Member 1 API for Candidate Validation and Data Privacy",
    version="1.0.0",
)


@app.get("/")
def health_check():
    return {"status": "online", "module": "Context Processor (Member 1)"}


@app.post("/validate-context", status_code=status.HTTP_200_OK)
def process_candidate_context(context: CandidateContextObject):
    """
    Receives candidate context payload, performs eligibility and validation checks,
    and returns sanitized data if valid.
    """
    validation_result = validate_context(context)

    if not validation_result["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Candidate context validation failed.",
                "errors": validation_result["errors"],
            },
        )

    # If valid, apply privacy masking
    safe_context = anonymize_context(context)

    return {
        "status": "success",
        "message": "Candidate context successfully validated.",
        "validated_data": safe_context,
    }