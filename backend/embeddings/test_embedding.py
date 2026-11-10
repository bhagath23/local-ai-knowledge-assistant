
from embeddings.embedding_model import generate_embedding

text = "Machine learning is a subset of artificial intelligence."

embedding = generate_embedding(text)

print("Embedding generated successfully!")

print("Vector dimensions:", len(embedding))

print("First 10 values:")

print(embedding[:10])
