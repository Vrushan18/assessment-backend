from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from context_processor.schemas import CandidateContextObject
from context_processor.validator import parse_dq_output, validate_context

from mapping_engine.mapper import ContextMapper
from scenario_engine.selector import select_scenario
from question_engine.selector import select_questions
from assessment_package.assembler import assemble_package


app = FastAPI(
    title="PECS Question Engine API",
    description="Context validation and assessment package generation for PECS certification.",
    version="0.1.0"
)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={
            "error": "validation_error",
            "detail": str(exc)
        }
    )


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "detail": "Contact engineering team"
        }
    )


# Root URL redirects to Swagger documentation
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.1.0"
    }


@app.post("/validate-context")
async def validate_context_endpoint(request: Request):
    """
    Step 1 of the pipeline.
    Receives raw DQ Assessment JSON.
    Returns CandidateContextObject + ValidationResult.
    Always returns HTTP 200 — is_valid field signals pass/fail.
    """

    raw_body = await request.json()

    mapped = parse_dq_output(raw_body)
    result = validate_context(mapped)

    response = {
        "validation": result.model_dump()
    }

    if result.is_valid:
        try:
            ctx = CandidateContextObject(**mapped)
            response["candidate_context"] = ctx.model_dump(mode="json")
        except Exception as e:
            response["validation"]["is_valid"] = False
            response["validation"]["errors"].append(
                f"Schema error: {str(e)}"
            )

    return response


@app.post("/mapping/map")
async def map_context(context: CandidateContextObject):
    """
    Step 2 of the pipeline.
    Receives a validated CandidateContextObject.
    Maps the candidate context to a PECS assessment pathway.
    Returns MappedContext.
    """

    mapper = ContextMapper()
    mapped_context = mapper.map(context)

    return mapped_context.model_dump(mode="json")
@app.post("/questions/select")
async def select_questions_endpoint(
    context: CandidateContextObject
):
    """
    Step 3/4 of the PECS assessment pipeline.

    Receives a validated CandidateContextObject.

    Pipeline:
    CandidateContext
        ↓
    MappedContext
        ↓
    Scenario
        ↓
    Selected Questions
        ↓
    AssessmentPackage
    """

    # ---------------------------------------------------------
    # Step 1: Map candidate context
    # ---------------------------------------------------------

    mapper = ContextMapper()
    mapped_context = mapper.map(context)

    # ---------------------------------------------------------
    # Step 2: Select scenario
    # ---------------------------------------------------------

    scenario = select_scenario(mapped_context)

    # ---------------------------------------------------------
    # Step 3: Select questions
    # ---------------------------------------------------------

    questions = select_questions(
        mapped_context,
        scenario
    )

    # ---------------------------------------------------------
    # Step 4: Assemble final assessment package
    # ---------------------------------------------------------

    package = assemble_package(
        candidate_context=context,
        scenario=scenario,
        questions=questions
    )

    return package.model_dump(mode="json")