
import requests

OLLAMA_URL = "http://localhost:11434/api/embed"

MODEL_NAME = "nomic-embed-text"


def generate_embedding(text, task="search_document"):

    payload = {
        "model": MODEL_NAME,
        "input": f"{task}: {text}"
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    result = response.json()

    return result["embeddings"][0]


def generate_embeddings(
    texts,
    task="search_document",
    batch_size=16
):

    all_embeddings = []

    total = len(texts)

    for start in range(0, total, batch_size):

        batch = texts[start:start + batch_size]

        # Add Nomic task prefix to every text
        prefixed_texts = [
            f"{task}: {text}"
            for text in batch
        ]

        payload = {
            "model": MODEL_NAME,
            "input": prefixed_texts
        }

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=180
        )

        response.raise_for_status()

        result = response.json()

        batch_embeddings = result["embeddings"]

        all_embeddings.extend(batch_embeddings)

        print(
            f"Embedded {len(all_embeddings)}/{total} chunks"
        )

    return all_embeddings
