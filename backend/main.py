
import uuid
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Database
from database import initialize_database

# Document processing
from services.document_processor import process_pdf

# Document registry
from services.document_registry import (
    calculate_file_hash,
    find_document,
    register_document,
    unregister_documents_by_filename,
    load_registry
)

# RAG
from rag.retriever import retrieve_documents
from rag.generator import generate_answer

# ChromaDB
from vectorstore.chroma_db import (
    get_all_sources,
    get_chunks_by_source,
    delete_document
)

# Conversation management
from services.conversation_service import (
    create_conversation,
    get_conversations,
    get_conversation_documents,
    attach_document,
    detach_document,
    add_message,
    get_messages,
    delete_conversation,
    rename_conversation,
    remove_document_from_all_conversations
)


# ==================================================
# APPLICATION CONFIGURATION
# ==================================================

app = FastAPI(
    title="Local AI Knowledge Assistant",
    description="Local multi-document RAG assistant using Ollama and ChromaDB.",
    version="2.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

initialize_database()


# ==================================================
# DIRECTORIES
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ==================================================
# REQUEST MODELS
# ==================================================

class QuestionRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=20)
    document_name: Optional[str] = None
    conversation_id: Optional[str] = None


class ConversationRequest(BaseModel):
    document_name: Optional[str] = None
    document_names: Optional[List[str]] = None
    title: str = "New Conversation"


class ConversationDocumentRequest(BaseModel):
    document_name: str


class MessageRequest(BaseModel):
    role: str
    content: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)


class RenameConversationRequest(BaseModel):
    title: str


# ==================================================
# HEALTH CHECK
# ==================================================

@app.get("/")
def home():
    return {
        "message": "Local AI Knowledge Assistant API is running."
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


# ==================================================
# UPLOAD PDF
# ==================================================

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is missing."
        )

    original_filename = Path(file.filename).name

    if Path(original_filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
    file_path = UPLOAD_DIR / unique_filename

    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty."
            )

        with open(file_path, "wb") as uploaded_file:
            uploaded_file.write(content)

        file_hash = calculate_file_hash(file_path)

        existing_document = find_document(file_hash)

        if existing_document:
            file_path.unlink(missing_ok=True)

            return {
                "message": "This document has already been uploaded.",
                "duplicate": True,
                "filename": existing_document.get(
                    "filename", original_filename
                )
            }

        result = process_pdf(
            str(file_path),
            source_name=original_filename
        )

        if result.get("duplicate"):
            file_path.unlink(missing_ok=True)

            return {
                "message": "This document is already indexed.",
                "duplicate": True,
                "filename": original_filename
            }

        if result.get("stored", 0) == 0:
            file_path.unlink(missing_ok=True)

            raise HTTPException(
                status_code=422,
                detail="No text chunks could be extracted from this PDF."
            )

        register_document(file_hash, original_filename)

        return {
            "message": "Document uploaded and processed successfully.",
            "duplicate": False,
            "filename": original_filename,
            "pages": result.get("pages", 0),
            "chunks": result.get("chunks", 0),
            "stored": result.get("stored", 0)
        }

    except HTTPException:
        raise

    except Exception as error:
        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(error)}"
        )


# ==================================================
# LIST DOCUMENTS
# ==================================================

@app.get("/documents")
def list_documents():

    sources = get_all_sources()
    documents = []

    for source in sources:

        results = get_chunks_by_source(source)

        chunks = results.get("documents", [])
        metadatas = results.get("metadatas", [])

        page_numbers = {
            metadata.get("page_number")
            for metadata in metadatas
            if metadata.get("page_number") is not None
        }

        documents.append({
            "filename": source,
            "chunks": len(chunks),
            "pages": len(page_numbers)
        })

    return {
        "total_documents": len(documents),
        "documents": documents
    }


# ==================================================
# PERMANENTLY DELETE DOCUMENT
# ==================================================

@app.delete("/documents")
def permanently_delete_document(filename: str):

    filename = filename.strip()

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="Document filename is required."
        )

    # Verify that the exact source exists
    available_sources = get_all_sources()

    if filename not in available_sources:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    try:
        # 1. Find registry entries for this exact filename
        registry_entries = load_registry()

        matching_hashes = [
            file_hash
            for file_hash, entry in registry_entries.items()
            if entry.get("filename") == filename
        ]

        # 2. Find uploaded PDFs by their exact content hashes
        files_to_delete = []

        for uploaded_file in UPLOAD_DIR.iterdir():

            if not uploaded_file.is_file():
                continue

            if uploaded_file.suffix.lower() != ".pdf":
                continue

            file_hash = calculate_file_hash(uploaded_file)

            if file_hash in matching_hashes:
                files_to_delete.append(uploaded_file)

        # 3. Delete the exact source from ChromaDB
        delete_document(filename)

        # 4. Remove this document from all conversations.
        # Conversation messages and conversation records are preserved.
        remove_document_from_all_conversations(filename)

        # 5. Remove registry entries
        unregister_documents_by_filename(filename)

        # 6. Delete matching uploaded PDF files
        deleted_uploads = 0

        for uploaded_file in files_to_delete:
            uploaded_file.unlink(missing_ok=True)
            deleted_uploads += 1

        return {
            "message": "Document permanently deleted.",
            "filename": filename,
            "deleted_uploads": deleted_uploads,
            "deleted_registry_entries": len(matching_hashes),
            "conversation_history_preserved": True
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Document deletion failed: {str(error)}"
        )


# ==================================================
# CREATE CONVERSATION
# ==================================================

@app.post("/conversations")
def create_new_conversation(request: ConversationRequest):

    document_names = request.document_names

    if document_names is None and request.document_name:
        document_names = [request.document_name]

    if not document_names:
        raise HTTPException(
            status_code=400,
            detail="At least one document must be selected."
        )

    document_names = list(dict.fromkeys(
        name.strip()
        for name in document_names
        if name and name.strip()
    ))

    if not document_names:
        raise HTTPException(
            status_code=400,
            detail="At least one valid document must be selected."
        )

    available_sources = get_all_sources()

    missing_documents = [
        name for name in document_names
        if name not in available_sources
    ]

    if missing_documents:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Some documents were not found in ChromaDB.",
                "missing_documents": missing_documents
            }
        )

    try:
        return create_conversation(
            document_names=document_names,
            title=request.title
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


# ==================================================
# LIST CONVERSATIONS
# ==================================================

@app.get("/conversations")
def list_all_conversations():

    conversations = get_conversations()

    return {
        "total_conversations": len(conversations),
        "conversations": conversations
    }


# ==================================================
# RENAME CONVERSATION
# ==================================================

@app.patch("/conversations/{conversation_id}")
def update_conversation_title(
    conversation_id: str,
    request: RenameConversationRequest
):

    title = request.title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Conversation title cannot be empty."
        )

    if len(title) > 100:
        raise HTTPException(
            status_code=400,
            detail="Conversation title cannot exceed 100 characters."
        )

    updated = rename_conversation(
        conversation_id,
        title
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    return {
        "message": "Conversation renamed successfully.",
        "conversation_id": conversation_id,
        "title": title
    }


# ==================================================
# GET DOCUMENTS ATTACHED TO CONVERSATION
# ==================================================

@app.get("/conversations/{conversation_id}/documents")
def list_conversation_documents(conversation_id: str):

    conversations = get_conversations()

    exists = any(
        item["id"] == conversation_id
        for item in conversations
    )

    if not exists:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    return {
        "conversation_id": conversation_id,
        "documents": get_conversation_documents(conversation_id)
    }


# ==================================================
# ATTACH DOCUMENT
# ==================================================

@app.post("/conversations/{conversation_id}/documents")
def add_document_to_conversation(
    conversation_id: str,
    request: ConversationDocumentRequest
):

    document_name = request.document_name.strip()

    if not document_name:
        raise HTTPException(
            status_code=400,
            detail="Document name cannot be empty."
        )

    if document_name not in get_all_sources():
        raise HTTPException(
            status_code=404,
            detail="Document not found in ChromaDB."
        )

    attached = attach_document(
        conversation_id,
        document_name
    )

    if not attached:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    return {
        "message": "Document attached successfully.",
        "conversation_id": conversation_id,
        "documents": get_conversation_documents(conversation_id)
    }


# ==================================================
# DETACH DOCUMENT
# ==================================================

@app.delete("/conversations/{conversation_id}/documents/{document_name}")
def remove_document_from_conversation(
    conversation_id: str,
    document_name: str
):

    detached = detach_document(
        conversation_id,
        document_name
    )

    if not detached:
        raise HTTPException(
            status_code=404,
            detail="Conversation or document association not found."
        )

    return {
        "message": "Document detached successfully.",
        "conversation_id": conversation_id,
        "documents": get_conversation_documents(conversation_id)
    }


# ==================================================
# ASK QUESTION USING MULTI-DOCUMENT RAG
# ==================================================

@app.post("/ask")
def ask_question(request: QuestionRequest):

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    document_names = []

    if request.conversation_id:

        conversations = get_conversations()

        conversation = next(
            (
                item for item in conversations
                if item["id"] == request.conversation_id
            ),
            None
        )

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found."
            )

        document_names = get_conversation_documents(
            request.conversation_id
        )

        if not document_names:
            raise HTTPException(
                status_code=400,
                detail="Attach at least one document to this conversation."
            )

        if (
            request.document_name
            and request.document_name not in document_names
        ):
            raise HTTPException(
                status_code=400,
                detail="Selected document is not attached to this conversation."
            )

    elif request.document_name:

        document_names = [request.document_name]

    else:

        raise HTTPException(
            status_code=400,
            detail="Select a document or provide a conversation ID."
        )

    available_sources = get_all_sources()

    missing_documents = [
        name for name in document_names
        if name not in available_sources
    ]

    if missing_documents:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Some documents are no longer indexed.",
                "missing_documents": missing_documents
            }
        )

    try:
        retrieved_documents = retrieve_documents(
            question=question,
            top_k=request.top_k,
            document_names=document_names
        )

        if not retrieved_documents:
            raise HTTPException(
                status_code=404,
                detail="No relevant document chunks were retrieved."
            )

        result = generate_answer(
            question,
            retrieved_documents
        )

        answer = result["answer"]
        sources = result["sources"]

        if request.conversation_id:

            add_message(
                conversation_id=request.conversation_id,
                role="user",
                content=question
            )

            add_message(
                conversation_id=request.conversation_id,
                role="assistant",
                content=answer,
                sources=sources
            )

            updated_conversations = get_conversations()

            updated_conversation = next(
                (
                    item for item in updated_conversations
                    if item["id"] == request.conversation_id
                ),
                None
            )

            conversation_title = (
                updated_conversation["title"]
                if updated_conversation else None
            )

        else:
            conversation_title = None

        return {
            "question": question,
            "conversation_id": request.conversation_id,
            "conversation_title": conversation_title,
            "document_names": document_names,
            "answer": answer,
            "sources": sources,
            "retrieved_chunks": len(retrieved_documents)
        }

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Question processing failed: {str(error)}"
        )


# ==================================================
# GET CONVERSATION MESSAGES
# ==================================================

@app.get("/conversations/{conversation_id}/messages")
def list_conversation_messages(conversation_id: str):

    conversations = get_conversations()

    exists = any(
        item["id"] == conversation_id
        for item in conversations
    )

    if not exists:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    messages = get_messages(conversation_id)

    return {
        "conversation_id": conversation_id,
        "total_messages": len(messages),
        "messages": messages
    }


# ==================================================
# SAVE MESSAGE MANUALLY
# ==================================================

@app.post("/conversations/{conversation_id}/messages")
def save_conversation_message(
    conversation_id: str,
    request: MessageRequest
):

    if request.role not in ["user", "assistant"]:
        raise HTTPException(
            status_code=400,
            detail="Role must be either user or assistant."
        )

    if not request.content.strip():
        raise HTTPException(
            status_code=400,
            detail="Message content cannot be empty."
        )

    try:
        add_message(
            conversation_id=conversation_id,
            role=request.role,
            content=request.content,
            sources=request.sources
        )

    except (sqlite3.IntegrityError, ValueError):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    return {
        "message": "Message saved successfully.",
        "conversation_id": conversation_id
    }


# ==================================================
# DELETE CONVERSATION
# ==================================================

@app.delete("/conversations/{conversation_id}")
def remove_conversation(conversation_id: str):

    deleted = delete_conversation(conversation_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    return {
        "message": "Conversation and its messages deleted successfully."
    }
