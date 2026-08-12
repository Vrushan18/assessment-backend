from pathlib import Path
import json
import chromadb


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CHROMA_PATH = PROJECT_ROOT / "data" / "chroma_db"
RUBRICS_PATH = PROJECT_ROOT / "data" / "rubrics.json"

COLLECTION_NAME = "pecs_rubrics"


def get_chroma_client():
    """
    Return the persistent ChromaDB client for PECS.
    """
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)

    return chromadb.PersistentClient(
        path=str(CHROMA_PATH)
    )


def get_rubric_collection():
    """
    Return the persistent PECS rubric collection.
    """
    client = get_chroma_client()

    return client.get_or_create_collection(
        name=COLLECTION_NAME
    )


def load_rubrics():
    """
    Load approved PECS rubric records from data/rubrics.json
    into the persistent ChromaDB collection.

    Production rubric content must come from the approved
    Companion PECS Rubric.
    """

    if not RUBRICS_PATH.exists():
        raise FileNotFoundError(
            f"Approved rubric file not found: {RUBRICS_PATH}"
        )

    with open(RUBRICS_PATH, "r", encoding="utf-8") as file:
        rubrics = json.load(file)

    if not isinstance(rubrics, list):
        raise ValueError(
            "rubrics.json must contain a JSON array."
        )

    collection = get_rubric_collection()

    ids = []
    documents = []
    metadatas = []

    for rubric in rubrics:

        required_fields = [
            "id",
            "document",
            "metadata",
        ]

        for field in required_fields:
            if field not in rubric:
                raise ValueError(
                    f"Rubric record missing required field: {field}"
                )

        metadata = rubric["metadata"]

        for field in ["criterion", "level", "domain"]:
            if field not in metadata:
                raise ValueError(
                    f"Rubric metadata missing required field: {field}"
                )

        ids.append(rubric["id"])
        documents.append(rubric["document"])
        metadatas.append(metadata)

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    return {
        "collection": COLLECTION_NAME,
        "loaded": len(ids),
    }