
from pathlib import Path

from ingestion.pdf_loader import extract_pdf
from ingestion.text_splitter import split_text

from embeddings.embedding_model import generate_embeddings

from vectorstore.chroma_db import (
    add_chunks,
    delete_document,
    get_chunks_by_source
)


def process_pdf(file_path, source_name=None):

    print("\nStarting document processing...")

    # 1. Standardize document filename
    source_name = Path(
        source_name or file_path
    ).name.strip()

    if not source_name.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported.")

    # 2. Prevent duplicate indexing
    existing = get_chunks_by_source(source_name)

    if existing["ids"]:

        print("Document already exists:", source_name)

        return {
            "pages": 0,
            "chunks": len(existing["ids"]),
            "stored": 0,
            "duplicate": True,
            "filename": source_name
        }

    # 3. Extract PDF pages
    pages = extract_pdf(file_path)

    print("Pages extracted:", len(pages))

    all_chunks = []

    # 4. Split pages into chunks
    for page in pages:

        metadata = {
            "source": source_name,
            "page_number": int(page["page_number"])
        }

        chunks = split_text(
            page["text"],
            chunk_size=150,
            overlap=30,
            metadata=metadata
        )

        all_chunks.extend(chunks)

    print("Total chunks created:", len(all_chunks))

    if not all_chunks:

        return {
            "pages": len(pages),
            "chunks": 0,
            "stored": 0,
            "duplicate": False,
            "filename": source_name
        }

    # 5. Generate embeddings
    print("\nGenerating embeddings...")

    texts = [
        chunk["text"]
        for chunk in all_chunks
    ]

    embeddings = generate_embeddings(
        texts,
        task="search_document",
        batch_size=16
    )

    print("Embeddings generated:", len(embeddings))

    # 6. Store chunks in ChromaDB
    ids = add_chunks(
        all_chunks,
        embeddings
    )

    print("\nSuccessfully indexed:", source_name)

    return {
        "pages": len(pages),
        "chunks": len(all_chunks),
        "stored": len(ids),
        "duplicate": False,
        "filename": source_name
    }
