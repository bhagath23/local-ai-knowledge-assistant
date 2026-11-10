
import chromadb
from pathlib import Path


# ==================================================
# CHROMADB CONFIGURATION
# ==================================================

# Current file:
# backend/vectorstore/chroma_db.py

# Original database:
# Local - AI - Knowledge - Assistant/chroma_db

BASE_DIR = Path(__file__).resolve().parent.parent

CHROMA_DB_PATH = BASE_DIR.parent / "chroma_db"

COLLECTION_NAME = "knowledge_documents"


# Connect to the original persistent database
client = chromadb.PersistentClient(
    path=str(CHROMA_DB_PATH)
)


# Get existing collection.
# Do not create a new collection.
collection = client.get_collection(
    name=COLLECTION_NAME
)


# ==================================================
# ADD CHUNKS
# ==================================================

def add_chunks(chunks, embeddings):

    if len(chunks) != len(embeddings):
        raise ValueError(
            "Number of chunks and embeddings must match."
        )

    if not chunks:
        return

    ids = []
    documents = []
    metadatas = []
    embedding_list = []

    for index, (chunk, embedding) in enumerate(
        zip(chunks, embeddings)
    ):

        metadata = dict(chunk.get("metadata", {}))

        source = metadata.get("source")

        if not source:
            raise ValueError(
                "Every chunk must contain source metadata."
            )

        chunk_id = metadata.get("chunk_id", index)

        metadata["chunk_id"] = int(chunk_id)

        ids.append(
            f"{source}_{chunk_id}"
        )

        documents.append(chunk["text"])

        metadatas.append(metadata)

        embedding_list.append(embedding)

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embedding_list
    )

    print(
        f"Successfully stored {len(chunks)} chunks."
    )


# ==================================================
# SEARCH CHUNKS
# Supports single and multiple PDF filtering
# ==================================================

def search_chunks(
    query_embedding,
    top_k=5,
    where=None
):

    if top_k <= 0:
        raise ValueError(
            "top_k must be positive."
        )

    total_chunks = collection.count()

    if total_chunks == 0:

        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, total_chunks),
        where=where,
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    return results


# ==================================================
# GET CHUNKS BY DOCUMENT SOURCE
# ==================================================

def get_chunks_by_source(source):

    return collection.get(
        where={
            "source": source
        },
        include=[
            "documents",
            "metadatas"
        ]
    )


# ==================================================
# GET ALL INDEXED DOCUMENT SOURCES
# ==================================================

def get_all_sources():

    results = collection.get(
        include=[
            "metadatas"
        ]
    )

    sources = set()

    for metadata in results.get("metadatas", []):

        if metadata and metadata.get("source"):
            sources.add(metadata["source"])

    return sorted(sources)


# ==================================================
# DELETE DOCUMENT CHUNKS
# ==================================================

def delete_document(source):

    results = collection.get(
        where={
            "source": source
        },
        include=[]
    )

    ids = results.get("ids", [])

    if not ids:
        return 0

    collection.delete(
        ids=ids
    )

    print(
        f"Deleted {len(ids)} chunks for {source}."
    )

    return len(ids)


# ==================================================
# GET COLLECTION COUNT
# ==================================================

def get_collection_count():

    return collection.count()


# ==================================================
# DATABASE DIAGNOSTICS
# ==================================================

if __name__ == "__main__":

    print("\nChromaDB connection successful!")

    print("Database path:", CHROMA_DB_PATH)

    print("Collection:", COLLECTION_NAME)

    print("\nIndexed documents:")

    for source in get_all_sources():
        print("-", source)

    print("\nTotal chunks:")
    print(get_collection_count())

    print("\nAll collections:")

    for col in client.list_collections():
        print(
            "Collection:",
            col.name,
            "| Count:",
            col.count()
        )
