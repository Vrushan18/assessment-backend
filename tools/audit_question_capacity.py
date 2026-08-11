import json
from collections import Counter
from pathlib import Path


BANK_PATH = (
    Path(__file__).resolve().parents[1]
    / "question_engine"
    / "question_bank.json"
)


PATHWAYS = {
    "L1": {
        "count": 15,
        "difficulty": {"Easy": 8, "Medium": 5, "Hard": 2},
    },
    "L2_ENGINEERING_SCIENCE": {
        "count": 20,
        "difficulty": {"Easy": 5, "Medium": 10, "Hard": 5},
    },
    "L2_COMMERCE_ARTS": {
        "count": 20,
        "difficulty": {"Easy": 6, "Medium": 9, "Hard": 5},
    },
    "L3": {
        "count": 25,
        "difficulty": {"Easy": 4, "Medium": 10, "Hard": 11},
    },
    "L4": {
        "count": 30,
        "difficulty": {"Easy": 2, "Medium": 10, "Hard": 18},
    },
}


BLOOMS_BY_LEVEL = {
    "L1": ["Remember", "Understand", "Apply"],
    "L2": ["Remember", "Understand", "Apply", "Analyse"],
    "L3": [
        "Remember",
        "Understand",
        "Apply",
        "Analyse",
        "Evaluate",
    ],
    "L4": [
        "Remember",
        "Understand",
        "Apply",
        "Analyse",
        "Evaluate",
        "Create",
    ],
}


DOMAINS = [
    "Engineering",
    "Science",
    "Commerce",
    "Arts",
]


def load_bank():
    with BANK_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def capacity(questions):
    return {
        "total": len(questions),
        "bloom": Counter(q["bloom_level"] for q in questions),
        "difficulty": Counter(q["difficulty"] for q in questions),
        "criterion": Counter(
            q["competency_criterion"] for q in questions
        ),
        "durability": sum(
            q["durability_flag"] is True
            for q in questions
        ),
        "governance": sum(
            q["governance_flag"] is True
            for q in questions
        ),
    }


def main():
    questions = load_bank()

    print("=" * 80)
    print("QUESTION BANK CAPACITY AUDIT")
    print("=" * 80)

    for domain in DOMAINS:
        domain_questions = [
            q for q in questions
            if q["domain"] == domain
        ]

        c = capacity(domain_questions)

        print()
        print(f"DOMAIN: {domain}")
        print(f"TOTAL: {c['total']}")
        print(f"BLOOM: {dict(c['bloom'])}")
        print(f"DIFFICULTY: {dict(c['difficulty'])}")
        print(f"CRITERIA: {dict(c['criterion'])}")
        print(f"DURABILITY TRUE: {c['durability']}")
        print(f"GOVERNANCE TRUE: {c['governance']}")

        for level in ["L1", "L2", "L3", "L4"]:
            if level == "L2":
                pathway_names = [
                    "L2_ENGINEERING_SCIENCE"
                    if domain in ("Engineering", "Science")
                    else "L2_COMMERCE_ARTS"
                ]
            else:
                pathway_names = [level]

            for pathway_name in pathway_names:
                rule = PATHWAYS[pathway_name]

                print()
                print(
                    f"  {pathway_name}: "
                    f"COUNT={rule['count']} "
                    f"DIFFICULTY={rule['difficulty']}"
                )

                count_ok = c["total"] >= rule["count"]

                difficulty_ok = all(
                    c["difficulty"][difficulty] >= required
                    for difficulty, required
                    in rule["difficulty"].items()
                )

                print(
                    f"    count capacity: "
                    f"{'PASS' if count_ok else 'FAIL'}"
                )

                print(
                    f"    difficulty capacity: "
                    f"{'PASS' if difficulty_ok else 'FAIL'}"
                )

                for bloom in BLOOMS_BY_LEVEL[level]:
                    available = c["bloom"][bloom]
                    required = rule["count"]

                    print(
                        f"    Bloom {bloom}: "
                        f"{available}/{required} "
                        f"{'PASS' if available >= required else 'FAIL'}"
                    )

    print()
    print("=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()