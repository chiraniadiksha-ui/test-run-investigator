from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from settings import QDRANT_URL


PROJECT_DIR = Path(__file__).resolve().parent
KB_DIR = PROJECT_DIR / "knowledge_base"
DB_PATH = PROJECT_DIR / "vector_db"

COLLECTION_NAME = "troubleshooting_guides"
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"


def main():
    # 1. Read the guides.
    documents = []

    for path in sorted(KB_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()

        if text:
            documents.append({
                "source": path.name,
                "text": text,
            })

    if not documents:
        raise ValueError(f"No guides found in {KB_DIR}")

    # 2. Convert the guides into vectors.
    print("Loading embedding model...")
    embedding_model = SentenceTransformer(MODEL_ID, device="cpu")

    vectors = embedding_model.encode(
        [document["text"] for document in documents],
        convert_to_numpy=True,
    )

    # 3. Open a database stored on disk.
    client = QdrantClient(url=QDRANT_URL, timeout=30)

    try:
        # A collection holds vectors with the same dimensions.
        if not client.collection_exists(COLLECTION_NAME):
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=int(vectors.shape[1]),
                    distance=models.Distance.COSINE,
                ),
            )

        # 4. Pair each vector with its original text and source.
        points = []

        for document, vector in zip(documents, vectors):
            # Same filename produces the same ID on future runs.
            document_id = str(
                uuid5(NAMESPACE_URL, document["source"])
            )

            points.append(
                models.PointStruct(
                    id=document_id,
                    vector=vector.tolist(),
                    payload={
                        "source": document["source"],
                        "text": document["text"],
                        "embedding_model": MODEL_ID,
                    },
                )
            )

        # Insert new records or update records with existing IDs.
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True,
        )

        print(f"Indexed {len(points)} guides.")
        print(f"Database location: {DB_PATH}")

    finally:
        client.close()


if __name__ == "__main__":
    main()