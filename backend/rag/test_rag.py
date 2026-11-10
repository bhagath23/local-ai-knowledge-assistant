
from rag.retriever import retrieve_documents
from rag.generator import generate_answer


# User question
question = "What is deep learning?"


# Step 1: Retrieve relevant chunks
print("Searching documents...")

documents = retrieve_documents(
    question,
    top_k=3
)

print("Retrieved chunks:", len(documents))


# Step 2: Generate answer
print("\nGenerating answer...")

result = generate_answer(
    question,
    documents
)


# Step 3: Display answer
print("\nAI ANSWER:")
print(result["answer"])


# Step 4: Display sources
print("\nSOURCES:")

for source in result["sources"]:

    print(
        source["source"],
        "| Page:",
        source["page_number"]
    )
