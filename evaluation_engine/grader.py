import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
import litellm

from assessment_package.schemas import Question
from evaluation_engine.grading import CandidateResponse
from evaluation_engine.schemas import CriterionScore


load_dotenv()

MODEL_NAME = os.getenv("PECS_GRADING_MODEL")

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
GRADING_ERROR_LOG = LOG_DIR / "grading_errors.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)


C1_C6_FRAMEWORK = """
C1 — Systems Understanding:
What can and cannot AI do, independent of any particular model?

C2 — Interaction System Design:
Can the candidate design a governed human-AI workflow?

C3 — Output Governance:
Can the candidate specify, validate, and quality-control AI outputs?

C4 — Domain Value Creation:
Can the candidate create measurable professional value using AI?

C5 — AI Governance & Ethics:
Can the candidate design accountability, oversight, and audit structures?

C6 — System Evaluation:
Can the candidate evaluate whether the human-AI system is working and improve it?
"""


DURABILITY_RULE = """
Durability Rule:
The assessment must remain meaningful if answered using an AI system
released several years in the future. Do not reward knowledge of a
specific AI model, vendor, interface, or temporary implementation detail.
Evaluate professional judgment and system design instead.
"""


class PECSGrader:
    """
    Model-agnostic PECS rubric-based grader.

    Rubrics are supplied externally by the RAG layer.
    The evaluator does not contain production rubric anchors.
    """

    def __init__(self, rubric_retriever=None, llm_client=None):
        self.rubric_retriever = rubric_retriever
        self.llm_client = llm_client

    def grade_response(
        self,
        question: Question,
        candidate_response: CandidateResponse,
        rubrics: List[Dict[str, Any]],
    ) -> CriterionScore:

        if candidate_response.question_id != question.question_id:
            raise ValueError(
                "Candidate response question_id does not match "
                "the question being graded."
            )

        if not candidate_response.response.strip():
            raise ValueError(
                "Candidate response cannot be empty."
            )

        if not rubrics:
            raise ValueError(
                f"No rubric supplied for question {question.question_id}."
            )

        if not MODEL_NAME and self.llm_client is None:
            raise RuntimeError(
                "PECS_GRADING_MODEL is not configured and no LLM client "
                "was supplied."
            )

        rubric_text = self._format_rubrics(rubrics)

        system_prompt = f"""
You are a professional PECS assessment evaluator.

Your task is to evaluate ONE candidate response against the supplied
PECS competency rubric.

You must score only the candidate's demonstrated professional capability.
Do not reward model-specific knowledge, prompt-writing tricks, or vendor
knowledge.

{C1_C6_FRAMEWORK}

{DURABILITY_RULE}

QUESTION:
{question.question_text}

COMPETENCY:
{question.competency_criterion.value}

CERTIFICATION CONTEXT:
Level associated with the supplied rubric.

RUBRIC:
{rubric_text}

Return ONLY valid JSON with exactly these fields:

{{
  "criterion": "C1-C6",
  "score": 0.0,
  "confidence": 0.0,
  "rationale": "brief evidence-based rationale",
  "rubric_reference": "rubric identifier"
}}

Rules:
- score must be between 0 and 10
- confidence must be between 0 and 1
- criterion must match the question's competency criterion
- rationale must explain the evidence in the candidate response
- do not invent evidence that is absent from the response
"""

        user_prompt = f"""
Candidate response:

{candidate_response.response}
"""

        start_time = time.perf_counter()

        try:
            if self.llm_client is not None:
                raw_response = self.llm_client(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
            else:
                response = litellm.completion(
                    model=MODEL_NAME,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                )

                raw_response = response.choices[0].message.content

            latency = time.perf_counter() - start_time

            logger.info(
                "grading_complete question_id=%s criterion=%s "
                "model=%s latency=%.4f",
                question.question_id,
                question.competency_criterion.value,
                MODEL_NAME or "injected_client",
                latency,
            )

            return self._parse_result(
                raw_response,
                question,
            )

        except Exception as exc:
            latency = time.perf_counter() - start_time

            logger.exception(
                "grading_failed question_id=%s latency=%.4f error=%s",
                question.question_id,
                latency,
                exc,
            )

            self._log_grading_error(
                question=question,
                raw_response=str(exc),
            )

            return CriterionScore(
                question_id=question.question_id,
                criterion=question.competency_criterion.value,
                score=0.0,
                confidence=0.0,
                rationale="Grading error: malformed model response",
                rubric_reference="grading_error",
            )

    @staticmethod
    def _format_rubrics(
        rubrics: List[Dict[str, Any]]
    ) -> str:

        formatted = []

        for rubric in rubrics:
            rubric_id = rubric.get("id", "unknown")

            if "document" in rubric:
                document = rubric["document"]
            else:
                document = str(rubric)

            formatted.append(
                f"[{rubric_id}]\n{document}"
            )

        return "\n\n".join(formatted)

    @staticmethod
    def _parse_result(
        raw_response: Any,
        question: Question,
    ) -> CriterionScore:

        if not isinstance(raw_response, str):
            raw_response = str(raw_response)

        cleaned = raw_response.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.replace("```json", "", 1)
            cleaned = cleaned.replace("```", "")
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Model returned malformed JSON."
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                "Model response must be a JSON object."
            )

        criterion = data.get("criterion")
        score = data.get("score")
        confidence = data.get("confidence")
        rationale = data.get("rationale")
        rubric_reference = data.get("rubric_reference")

        if criterion != question.competency_criterion.value:
            raise ValueError(
                "Model returned an incorrect competency criterion."
            )

        if score is None or confidence is None:
            raise ValueError(
                "Model response is missing score or confidence."
            )

        score = float(score)
        confidence = float(confidence)

        if not 0 <= score <= 10:
            raise ValueError(
                "Model score must be between 0 and 10."
            )

        if not 0 <= confidence <= 1:
            raise ValueError(
                "Model confidence must be between 0 and 1."
            )

        if not rationale:
            raise ValueError(
                "Model response is missing rationale."
            )

        if not rubric_reference:
            raise ValueError(
                "Model response is missing rubric_reference."
            )

        return CriterionScore(
            question_id=question.question_id,
            criterion=criterion,
            score=score,
            confidence=confidence,
            rationale=str(rationale),
            rubric_reference=str(rubric_reference),
        )

    @staticmethod
    def _log_grading_error(
        question: Question,
        raw_response: str,
    ):

        with open(
            GRADING_ERROR_LOG,
            "a",
            encoding="utf-8",
        ) as file:

            file.write(
                json.dumps(
                    {
                        "question_id": question.question_id,
                        "criterion": question.competency_criterion.value,
                        "raw_response": raw_response,
                    }
                )
                + "\n"
            )