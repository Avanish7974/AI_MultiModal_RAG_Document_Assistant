import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import tempfile

from src.services.chat_manager import (
    create_chat,
    list_chats,
    get_chat,
    delete_chat,
    get_messages,
    save_message,
)

from src.vectorstore.chroma_store import get_chat_collection
from src.retriever.retriever import retrieve_chunks
from src.llm.gemini import generate_response

from src.services.document_service import process_document


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="Multi-Modal RAG Document Assistant API",
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",

        # Current frontend origin shown in browser console
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# REQUEST MODELS
# =========================================================

class MessageRequest(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "message": "Multi-Modal RAG API is running",
        "status": "ok",
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy"
    }


# =========================================================
# LIST CHATS
# =========================================================

@app.get("/api/chats")
def get_all_chats():

    chats = list_chats()

    return {
        "chats": chats
    }


# =========================================================
# CREATE CHAT
# =========================================================

@app.post("/api/chats")
def create_new_chat():

    chat_id = create_chat()

    return {
        "chat_id": chat_id
    }


# =========================================================
# GET SINGLE CHAT
# =========================================================

@app.get("/api/chats/{chat_id}")
def get_single_chat(chat_id: str):

    chat = get_chat(chat_id)

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    return chat


# =========================================================
# DELETE CHAT
# =========================================================

@app.delete("/api/chats/{chat_id}")
def remove_chat(chat_id: str):

    chat = get_chat(chat_id)

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    delete_chat(chat_id)

    return {
        "success": True,
        "chat_id": chat_id
    }


# =========================================================
# GET CHAT MESSAGES
# =========================================================

@app.get("/api/chats/{chat_id}/messages")
def get_chat_messages(chat_id: str):

    chat = get_chat(chat_id)

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    messages = get_messages(chat_id)

    return {
        "chat_id": chat_id,
        "messages": messages
    }


# =========================================================
# SAVE CHAT MESSAGE
# =========================================================

@app.post("/api/chats/{chat_id}/messages")
def add_chat_message(
    chat_id: str,
    request: MessageRequest
):

    chat = get_chat(chat_id)

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    message = {
        "role": request.role,
        "content": request.content,
    }

    save_message(
        chat_id,
        message
    )

    return {
        "success": True,
        "chat_id": chat_id,
        "message": message,
    }

# =========================================================
# UPLOAD DOCUMENT
# =========================================================

@app.post("/api/chats/{chat_id}/upload")
async def upload_document(
    chat_id: str,
    file: UploadFile = File(...)
):

    # -----------------------------------------------------
    # CHECK CHAT
    # -----------------------------------------------------

    chat = get_chat(chat_id)

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    # -----------------------------------------------------
    # VALIDATE FILE
    # -----------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected"
        )

    # -----------------------------------------------------
    # GET CHAT COLLECTION
    # -----------------------------------------------------

    collection = get_chat_collection(chat_id)

    # -----------------------------------------------------
    # SAVE FILE TEMPORARILY
    # -----------------------------------------------------

    temp_path = None

    try:

        suffix = os.path.splitext(
            file.filename
        )[1]

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:

            temp_path = temp_file.name

            content = await file.read()

            temp_file.write(content)

        # -------------------------------------------------
        # PROCESS DOCUMENT
        # -------------------------------------------------

        chunks = process_document(
            file_path=temp_path,
            file_name=file.filename,
            collection=collection
        )

        # -------------------------------------------------
        # CHECK PROCESSING RESULT
        # -------------------------------------------------

        if not chunks:

            raise HTTPException(
                status_code=400,
                detail="Could not extract any content from the document."
            )

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        return {
            "success": True,
            "chat_id": chat_id,
            "file_name": file.filename,
            "chunks": len(chunks),
            "message": "Document uploaded and processed successfully."
        }

    except HTTPException:
        raise

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}"
        )

    finally:

        # -------------------------------------------------
        # DELETE TEMPORARY FILE
        # -------------------------------------------------

        if temp_path and os.path.exists(temp_path):

            try:
                os.remove(temp_path)
            except Exception:
                pass

# =========================================================
# ASK DOCUMENTS — RAG
# =========================================================

@app.post("/api/chats/{chat_id}/ask")
def ask_documents(
    chat_id: str,
    request: AskRequest
):

    # -----------------------------------------------------
    # CHECK CHAT
    # -----------------------------------------------------

    chat = get_chat(chat_id)

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    # -----------------------------------------------------
    # VALIDATE QUESTION
    # -----------------------------------------------------

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    # -----------------------------------------------------
    # GET CHAT-SPECIFIC CHROMA COLLECTION
    # -----------------------------------------------------

    collection = get_chat_collection(chat_id)

    # -----------------------------------------------------
    # CHECK WHETHER DOCUMENTS EXIST
    # -----------------------------------------------------

    results = collection.get()

    if not results.get("ids"):
        raise HTTPException(
            status_code=400,
            detail="No documents found in this chat. Please upload a document first."
        )

    # -----------------------------------------------------
    # SAVE USER QUESTION
    # -----------------------------------------------------

    user_message = {
        "role": "user",
        "content": question,
    }

    save_message(
        chat_id,
        user_message
    )

    # -----------------------------------------------------
    # RETRIEVE RELEVANT CHUNKS
    # -----------------------------------------------------

    try:

        retrieval_result = retrieve_chunks(
            question,
            collection,
            top_k=5
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Document retrieval failed: {str(e)}"
        )

    documents = retrieval_result.get(
        "documents",
        []
    )

    metadatas = retrieval_result.get(
        "metadatas",
        []
    )

    # -----------------------------------------------------
    # CHECK RETRIEVAL RESULT
    # -----------------------------------------------------

    if not documents:

        answer = (
            "I could not find relevant information "
            "in the uploaded documents."
        )

        assistant_message = {
            "role": "assistant",
            "content": answer,
            "sources": []
        }

        save_message(
            chat_id,
            assistant_message
        )

        return {
            "success": True,
            "chat_id": chat_id,
            "question": question,
            "answer": answer,
            "sources": [],
        }

    # -----------------------------------------------------
    # BUILD RETRIEVED CONTEXT
    # -----------------------------------------------------

    context_parts = []

    for i, document in enumerate(
        documents,
        start=1
    ):

        metadata = (
            metadatas[i - 1]
            if i - 1 < len(metadatas)
            else {}
        )

        file_name = metadata.get(
            "file_name",
            "Unknown file"
        )

        page = metadata.get(
            "page",
            metadata.get(
                "page_number",
                "Unknown"
            )
        )

        context_parts.append(
            f"""
SOURCE {i}

File: {file_name}

Location: {page}

Content:
{document}
"""
        )

    retrieved_context = "\n".join(
        context_parts
    )

    # -----------------------------------------------------
    # BUILD CONVERSATION CONTEXT
    # -----------------------------------------------------

    previous_messages = get_messages(
        chat_id
    )

    conversation_parts = []

    for message in previous_messages:

        role = message.get(
            "role",
            ""
        )

        content = message.get(
            "content",
            ""
        )

        # Don't include the current question twice
        if (
            role == "user"
            and content == question
        ):
            continue

        if role == "user":

            conversation_parts.append(
                f"User: {content}"
            )

        elif role == "assistant":

            conversation_parts.append(
                f"Assistant: {content}"
            )

    conversation_context = "\n".join(
        conversation_parts
    )

    # -----------------------------------------------------
    # FINAL RAG CONTEXT
    # -----------------------------------------------------

    final_context = f"""
PREVIOUS CONVERSATION:

{conversation_context}


RETRIEVED DOCUMENT CONTEXT:

{retrieved_context}
"""

    # -----------------------------------------------------
    # GENERATE ANSWER
    # -----------------------------------------------------

    try:

        answer = generate_response(
            context=final_context,
            question=question
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Answer generation failed: {str(e)}"
        )

    # -----------------------------------------------------
    # BUILD SOURCES
    # -----------------------------------------------------

    grouped_sources = {}

    for metadata in metadatas:

        if not isinstance(
            metadata,
            dict
        ):
            continue

        file_name = metadata.get(
            "file_name",
            "Unknown file"
        )

        source_type = metadata.get(
            "source_type",
            "document"
        )

        page = metadata.get(
            "page",
            metadata.get(
                "page_number"
            )
        )

        if file_name not in grouped_sources:

            grouped_sources[file_name] = {
                "file_name": file_name,
                "source_type": source_type,
                "pages": set(),
                "timestamps": set(),
                "video_id": metadata.get(
                    "video_id"
                ),
            }

        if page is not None:

            grouped_sources[
                file_name
            ]["pages"].add(
                str(page)
            )

        # YouTube support
        if source_type == "youtube":

            start_time = metadata.get(
                "start_time"
            )

            if start_time is not None:

                try:

                    grouped_sources[
                        file_name
                    ]["timestamps"].add(
                        float(start_time)
                    )

                except (
                    TypeError,
                    ValueError
                ):
                    pass

            if metadata.get("video_id"):

                grouped_sources[
                    file_name
                ]["video_id"] = metadata[
                    "video_id"
                ]

    # -----------------------------------------------------
    # CONVERT SOURCES TO JSON-SAFE FORMAT
    # -----------------------------------------------------

    sources = []

    for file_name, source in (
        grouped_sources.items()
    ):

        formatted_source = {
            "file_name": file_name,
            "source_type": source[
                "source_type"
            ],
            "pages": sorted(
                source["pages"]
            ),
        }

        # Add YouTube metadata only when applicable
        if source["source_type"] == "youtube":

            formatted_source[
                "video_id"
            ] = source.get(
                "video_id"
            )

            formatted_source[
                "timestamps"
            ] = sorted(
                source["timestamps"]
            )

        sources.append(
            formatted_source
        )

    # -----------------------------------------------------
    # SAVE ASSISTANT MESSAGE
    # -----------------------------------------------------

    assistant_message = {
        "role": "assistant",
        "content": answer,
        "sources": sources,
    }

    save_message(
        chat_id,
        assistant_message
    )

    # -----------------------------------------------------
    # API RESPONSE
    # -----------------------------------------------------

    return {
        "success": True,
        "chat_id": chat_id,
        "question": question,
        "answer": answer,
        "sources": sources,
    }