
def split_text(
    text,
    chunk_size=150,
    overlap=30,
    metadata=None
):

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be non-negative and smaller than chunk_size"
        )

    words = text.split()

    chunks = []

    start = 0

    while start < len(words):

        end = min(start + chunk_size, len(words))

        chunk_text = " ".join(words[start:end])

        chunk_data = {
            "chunk_id": len(chunks),
            "text": chunk_text,
            "start_word": start,
            "end_word": end,
            "metadata": metadata or {}
        }

        chunks.append(chunk_data)

        start += chunk_size - overlap

    return chunks
