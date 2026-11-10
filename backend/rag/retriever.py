
from embeddings.embedding_model import generate_embedding
from vectorstore.chroma_db import search_chunks


def retrieve_documents(
    question,
    top_k=5,
    document_name=None,
    document_names=None
):
    """
    Retrieve relevant chunks from one or multiple PDFs.

    Args:
        question: User's question.
        top_k: Maximum number of chunks to retrieve.
        document_name: Optional single PDF filename.
        document_names: Optional list of PDF filenames.

    Returns:
        List of retrieved chunks containing:
        - text
        - metadata
        - distance
    """

    # ==========================================
    # 1. VALIDATE INPUT
    # ==========================================

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    if not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be a positive integer.")

    question = question.strip()

    print("\n" + "#" * 75)
    print("RAG RETRIEVAL STARTED")
    print("#" * 75)

    print("Question:", question)
    print("Top K:", top_k)

    # ==========================================
    # 2. GENERATE QUERY EMBEDDING
    # ==========================================

    query_embedding = generate_embedding(
        question,
        task="search_query"
    )

    if query_embedding is None:
        raise RuntimeError("Failed to generate query embedding.")

    print("Query embedding generated.")
    print("Embedding dimensions:", len(query_embedding))

    # ==========================================
    # 3. BUILD DOCUMENT FILTER
    # ==========================================

    metadata_filter = None

    if document_names is not None:

        if isinstance(document_names, str):
            document_names = [document_names]

        cleaned_names = list(
            dict.fromkeys(
                name.strip()
                for name in document_names
                if isinstance(name, str) and name.strip()
            )
        )

        if not cleaned_names:
            print("No valid document names provided.")
            return []

        if len(cleaned_names) == 1:
            metadata_filter = {
                "source": cleaned_names[0]
            }
        else:
            metadata_filter = {
                "source": {
                    "$in": cleaned_names
                }
            }

    elif document_name:

        metadata_filter = {
            "source": document_name.strip()
        }

    print("Document filter:", metadata_filter or "All documents")

    # ==========================================
    # 4. SEARCH CHROMADB
    # ==========================================

    results = search_chunks(
        query_embedding=query_embedding,
        top_k=top_k,
        where=metadata_filter
    )

    retrieved_documents = []

    if not results or not results.get("documents"):
        print("No results returned by ChromaDB.")
        return retrieved_documents

    documents = results["documents"][0] or []
    metadatas = results["metadatas"][0] or []
    distances = results["distances"][0] or []

    if not documents:
        print("No matching document chunks found.")
        return retrieved_documents

    # ==========================================
    # 5. DISPLAY RETRIEVED CHUNKS
    # ==========================================

    print("\nRetrieved chunks:", len(documents))

    for index, (document, metadata, distance) in enumerate(
        zip(documents, metadatas, distances),
        start=1
    ):

        metadata = metadata or {}

        chunk = {
            "text": document,
            "metadata": metadata,
            "distance": float(distance)
        }

        retrieved_documents.append(chunk)

        print("\n" + "=" * 75)
        print(f"RETRIEVED CHUNK #{index}")
        print("=" * 75)

        print("Source:", metadata.get("source", "Unknown"))
        print("Page:", metadata.get("page_number", "Unknown"))
        print("Chunk ID:", metadata.get("chunk_id", "Unknown"))

        print("Distance:", round(float(distance), 4))

        print("\nRetrieved Text:")
        print(document)

        print("=" * 75)

    # ==========================================
    # 6. RETRIEVAL SUMMARY
    # ==========================================

    print("\n" + "#" * 75)
    print("RETRIEVAL SUMMARY")
    print("#" * 75)

    print("Question:", question)
    print("Chunks retrieved:", len(retrieved_documents))

    if retrieved_documents:
        best_distance = min(
            item["distance"]
            for item in retrieved_documents
        )

        print("Best distance:", round(best_distance, 4))

    print("RAG RETRIEVAL COMPLETED")
    print("#" * 75 + "\n")

    return retrieved_documents
