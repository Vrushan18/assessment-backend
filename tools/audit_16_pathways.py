import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio

from context_processor.schemas import CandidateContextObject
from main import select_questions_endpoint


DOMAINS = [
    "Engineering",
    "Science",
    "Commerce",
    "Arts",
]

LEVELS = [
    "L1",
    "L2",
    "L3",
    "L4",
]

BLOOM_BY_LEVEL = {
    "L1": "Apply",
    "L2": "Analyse",
    "L3": "Analyse",
    "L4": "Analyse",
}


async def run_audit():
    print("=" * 80)
    print("16-PATHWAY QUESTION SELECTION AUDIT")
    print("=" * 80)

    results = []

    for domain in DOMAINS:
        for level in LEVELS:

            bloom = BLOOM_BY_LEVEL[level]

            context = CandidateContextObject(
                candidate_id=f"AUDIT-{domain}-{level}",
                domain=domain,
                certification_level=level,
                bloom_target=bloom,
                background=f"Automated {domain} {level} question selection audit",
                eligibility_confirmed=True,
                timestamp="2026-08-11T12:00:00Z",
                source_assessment_id=f"AUDIT-{domain}-{level}",
            )

            try:
                package = await select_questions_endpoint(context)

                # Endpoint returns package.model_dump(mode="json")
                # Find the actual question list.
                questions = package.get("questions", [])

                actual_count = len(questions)

                # Read expected count from the mapping rules through
                # the returned package only for reporting.
                expected_counts = {
                    "L1": 15,
                    "L2": 20,
                    "L3": 25,
                    "L4": 30,
                }

                expected_count = expected_counts[level]

                if actual_count == expected_count:
                    status = "PASS"
                    detail = f"{actual_count} questions"
                else:
                    status = "FAIL"
                    detail = (
                        f"returned {actual_count}, "
                        f"required {expected_count}"
                    )

                print(
                    f"{domain:12} {level:2} "
                    f"Bloom={bloom:9} "
                    f"-> {status} ({detail})"
                )

                results.append(
                    {
                        "domain": domain,
                        "level": level,
                        "status": status,
                        "detail": detail,
                    }
                )

            except Exception as exc:

                message = str(exc).replace("\n", " ")

                print(
                    f"{domain:12} {level:2} "
                    f"Bloom={bloom:9} "
                    f"-> REJECTED"
                )
                print(f"    Reason: {message}")

                results.append(
                    {
                        "domain": domain,
                        "level": level,
                        "status": "REJECTED",
                        "detail": message,
                    }
                )

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(
        r["status"] == "PASS"
        for r in results
    )

    failed = sum(
        r["status"] == "FAIL"
        for r in results
    )

    rejected = sum(
        r["status"] == "REJECTED"
        for r in results
    )

    print(f"PASS:      {passed}/16")
    print(f"FAIL:      {failed}/16")
    print(f"REJECTED:  {rejected}/16")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_audit())