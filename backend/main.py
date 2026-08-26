import os
import uuid
import json
import re

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.services.chat_manager import (
    create_chat,
    list_chats,
    get_chat,
    delete_chat,
    get_messages,
    save_message,
    update_chat_title,
    get_chat_files,
    add_file,
)

from src.vectorstore.chroma_store import (
    get_chat_collection,
    add_youtube_transcript,
)
from src.retriever.retriever import retrieve_chunks
from src.loaders.youtube_loader import (
    extract_youtube_transcript,
    extract_video_id,
)
from src.llm.gemini import (
    generate_response,
    generate_youtube_multimodal_response,
    should_use_youtube_multimodal,
)

from src.services.summary_service import generate_summary
from src.services.comparison_service import generate_comparison
from src.services.quiz_service import generate_quiz
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",

        # Streamlit
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

# =========================================================
# REQUEST MODELS
# =========================================================

class MessageRequest(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str


class ChatUpdateRequest(BaseModel):
    title: str


class YouTubeAskRequest(BaseModel):
    video_url: str
    question: str


class YouTubeAnalyzeRequest(BaseModel):
    video_url: str


class SummaryRequest(BaseModel):
    length: str = "Medium"


class CompareRequest(BaseModel):
    files: list[str]


class QuizRequest(BaseModel):
    num_questions: int = 5
    difficulty: str = "Medium"


class FlashcardsRequest(BaseModel):
    count: int = 10
    difficulty: str = "Medium"    



# =========================================================
# DOCUMENT MODE HELPERS
# =========================================================

def _get_all_document_content(chat_id: str):
    """
    Read all indexed document chunks for a chat.
    This is used by summarize/compare/flashcards because
    those modes need broader context than normal top-k RAG.
    """
    collection = get_chat_collection(chat_id)

    result = collection.get(
        include=[
            "documents",
            "metadatas",
        ]
    )

    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []

    return documents, metadatas


def _build_document_context(
    documents,
    metadatas,
    selected_files=None,
):
    """
    Build a readable context block while optionally limiting
    the context to selected file names.
    """
    selected_set = (
        set(selected_files)
        if selected_files
        else None
    )

    context_parts = []
    selected_metadatas = []

    for index, document in enumerate(documents):
        if not document:
            continue

        metadata = (
            metadatas[index]
            if index < len(metadatas)
            else {}
        )

        if not isinstance(metadata, dict):
            metadata = {}

        file_name = metadata.get(
            "file_name",
            "Unknown file",
        )

        if (
            selected_set is not None
            and file_name not in selected_set
        ):
            continue

        page = metadata.get(
            "page",
            metadata.get(
                "page_number",
                "Unknown",
            ),
        )

        context_parts.append(
            f"""
SOURCE {len(context_parts) + 1}

File: {file_name}

Location: {page}

Content:
{document}
"""
        )

        selected_metadatas.append(metadata)

    return (
        "\n".join(context_parts),
        selected_metadatas,
    )


def _build_sources_from_metadatas(metadatas):
    """
    Convert Chroma metadata into the same source structure
    already returned by the normal /ask endpoint.
    """
    grouped_sources = {}

    for metadata in metadatas or []:
        if not isinstance(metadata, dict):
            continue

        file_name = metadata.get(
            "file_name",
            "Unknown file",
        )

        source_type = metadata.get(
            "source_type",
            "document",
        )

        page = metadata.get(
            "page",
            metadata.get(
                "page_number"
            ),
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
            ]["pages"].add(str(page))

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
                    ValueError,
                ):
                    pass

            if metadata.get("video_id"):
                grouped_sources[
                    file_name
                ]["video_id"] = metadata[
                    "video_id"
                ]

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

        if (
            source["source_type"]
            == "youtube"
        ):
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

    return sources


def _parse_json_response(raw_response):
    """
    Parse JSON returned by Gemini even if it accidentally
    wraps the JSON in Markdown code fences or surrounding text.
    """
    if isinstance(raw_response, dict):
        return raw_response

    if raw_response is None:
        return None

    text = str(raw_response).strip()

    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    try:
        return json.loads(
            text[start:end + 1]
        )
    except Exception:
        return None


def _normalize_quiz_data(raw_quiz):
    """
    Validate the quiz JSON before sending it to the frontend.
    """
    data = _parse_json_response(
        raw_quiz
    )

    if not isinstance(data, dict):
        return None

    questions = data.get(
        "questions"
    )

    if not isinstance(
        questions,
        list,
    ):
        return None

    normalized_questions = []

    for item in questions:
        if not isinstance(
            item,
            dict,
        ):
            continue

        question = item.get(
            "question"
        )

        options = item.get(
            "options"
        )

        correct_answer = item.get(
            "correct_answer"
        )

        if not isinstance(
            question,
            str,
        ):
            continue

        if (
            not isinstance(
                options,
                list,
            )
            or len(options) != 4
        ):
            continue

        if not all(
            isinstance(
                option,
                str,
            )
            for option in options
        ):
            continue

        try:
            correct_answer = int(
                correct_answer
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if not (
            0 <= correct_answer < 4
        ):
            continue

        normalized_item = {
            "question": question,
            "options": options,
            "correct_answer": correct_answer,
        }

        explanation = item.get(
            "explanation"
        )

        if isinstance(
            explanation,
            str,
        ):
            normalized_item[
                "explanation"
            ] = explanation

        source = item.get(
            "source"
        )

        if isinstance(
            source,
            str,
        ):
            normalized_item[
                "source"
            ] = source

        normalized_questions.append(
            normalized_item
        )

    if not normalized_questions:
        return None

    return {
        "questions": normalized_questions
    }


def _normalize_flashcard_data(
    raw_flashcards
):
    """
    Validate the flashcard JSON before sending it
    to the frontend.
    """
    data = _parse_json_response(
        raw_flashcards
    )

    if not isinstance(
        data,
        dict,
    ):
        return None

    cards = data.get(
        "flashcards"
    )

    if not isinstance(
        cards,
        list,
    ):
        return None

    normalized_cards = []

    for card in cards:
        if not isinstance(
            card,
            dict,
        ):
            continue

        front = card.get(
            "front"
        )

        back = card.get(
            "back"
        )

        if not isinstance(
            front,
            str,
        ):
            continue

        if not isinstance(
            back,
            str,
        ):
            continue

        normalized_card = {
            "front": front,
            "back": back,
        }

        source = card.get(
            "source"
        )

        if isinstance(
            source,
            str,
        ):
            normalized_card[
                "source"
            ] = source

        normalized_cards.append(
            normalized_card
        )

    if not normalized_cards:
        return None

    return {
        "flashcards": normalized_cards
    }


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
        "status": "healthy",
    }


# =========================================================
# LIST CHATS
# =========================================================

@app.get("/api/chats")
def get_all_chats():

    chats = list_chats()

    return {
        "chats": chats,
    }


# =========================================================
# CREATE CHAT
# =========================================================

@app.post("/api/chats")
def create_new_chat():

    chat_id = create_chat()

    return {
        "chat_id": chat_id,
    }


# =========================================================
# GET SINGLE CHAT
# =========================================================

@app.get("/api/chats/{chat_id}")
def get_single_chat(
    chat_id: str
):

    chat = get_chat(
        chat_id
    )

    if not chat:

        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )

    return chat


# =========================================================
# UPDATE CHAT TITLE
# =========================================================

@app.patch("/api/chats/{chat_id}")
def update_chat(
    chat_id: str,
    request: ChatUpdateRequest,
):

    # -----------------------------------------------------
    # CHECK CHAT
    # -----------------------------------------------------

    chat = get_chat(
        chat_id
    )

    if not chat:

        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )


    # -----------------------------------------------------
    # VALIDATE TITLE
    # -----------------------------------------------------

    title = request.title.strip()

    if not title:

        raise HTTPException(
            status_code=400,
            detail="Chat title cannot be empty",
        )


    # -----------------------------------------------------
    # LIMIT TITLE LENGTH
    # -----------------------------------------------------

    title = title[:100]


    # -----------------------------------------------------
    # UPDATE TITLE
    # -----------------------------------------------------

    update_chat_title(
        chat_id,
        title,
    )


    # -----------------------------------------------------
    # GET UPDATED CHAT
    # -----------------------------------------------------

    updated_chat = get_chat(
        chat_id
    )

    return {
        "success": True,
        "chat": updated_chat,
    }


# =========================================================
# DELETE CHAT
# =========================================================

@app.delete("/api/chats/{chat_id}")
def remove_chat(
    chat_id: str
):

    chat = get_chat(
        chat_id
    )

    if not chat:

        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )


    delete_chat(
        chat_id
    )

    return {
        "success": True,
        "chat_id": chat_id,
    }


# =========================================================
# GET CHAT FILES
# =========================================================

@app.get("/api/chats/{chat_id}/files")
def get_files_for_chat(
    chat_id: str
):

    # -----------------------------------------------------
    # CHECK CHAT
    # -----------------------------------------------------

    chat = get_chat(
        chat_id
    )

    if not chat:

        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )


    # -----------------------------------------------------
    # GET FILES
    # -----------------------------------------------------

    files = get_chat_files(
        chat_id
    )

    return {
        "success": True,
        "chat_id": chat_id,
        "files": files,
    }


# =========================================================
# GET CHAT MESSAGES
# =========================================================

@app.get("/api/chats/{chat_id}/messages")
def get_chat_messages(
    chat_id: str
):

    chat = get_chat(
        chat_id
    )

    if not chat:

        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )


    messages = get_messages(
        chat_id
    )

    return {
        "chat_id": chat_id,
        "messages": messages,
    }


# =========================================================
# SAVE CHAT MESSAGE
# =========================================================

@app.post("/api/chats/{chat_id}/messages")
def add_chat_message(
    chat_id: str,
    request: MessageRequest,
):

    chat = get_chat(
        chat_id
    )

    if not chat:

        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )


    message = {
        "role": request.role,
        "content": request.content,
    }


    save_message(
        chat_id,
        message,
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
    file: UploadFile = File(...),
):

    # -----------------------------------------------------
    # CHECK CHAT
    # -----------------------------------------------------

    chat = get_chat(
        chat_id
    )

    if not chat:

        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )


    # -----------------------------------------------------
    # VALIDATE FILE
    # -----------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No file selected",
        )


    # -----------------------------------------------------
    # GET CHAT COLLECTION
    # -----------------------------------------------------

    collection = get_chat_collection(
        chat_id
    )


    # -----------------------------------------------------
    # CREATE PERMANENT CHAT UPLOAD DIRECTORY
    # -----------------------------------------------------

    upload_directory = os.path.join(
        "data",
        "uploads",
        chat_id,
    )

    os.makedirs(
        upload_directory,
        exist_ok=True,
    )


    # -----------------------------------------------------
    # SAFE ORIGINAL FILE NAME
    # -----------------------------------------------------

    original_file_name = os.path.basename(
        file.filename
    )


    # -----------------------------------------------------
    # GET FILE EXTENSION
    # -----------------------------------------------------

    extension = os.path.splitext(
        original_file_name
    )[1]


    # -----------------------------------------------------
    # CREATE UNIQUE STORAGE NAME
    # -----------------------------------------------------

    storage_name = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )


    permanent_path = os.path.join(
        upload_directory,
        storage_name,
    )


    # -----------------------------------------------------
    # SAVE UPLOADED FILE PERMANENTLY
    # -----------------------------------------------------

    try:

        content = await file.read()


        with open(
            permanent_path,
            "wb",
        ) as output_file:

            output_file.write(
                content
            )


        file_size = len(
            content
        )


        # -------------------------------------------------
        # PROCESS DOCUMENT
        # -------------------------------------------------

        chunks = process_document(
            file_path=permanent_path,
            file_name=original_file_name,
            collection=collection,
        )


        # -------------------------------------------------
        # CHECK PROCESSING RESULT
        # -------------------------------------------------

        if not chunks:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not extract any content "
                    "from the document."
                ),
            )


        # -------------------------------------------------
        # SAVE FILE METADATA
        # -------------------------------------------------

        file_key = uuid.uuid4().hex


        add_file(
            chat_id=chat_id,
            file_key=file_key,
            file_name=original_file_name,
            file_path=permanent_path,
            file_size=file_size,
        )


        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        return {
            "success": True,
            "chat_id": chat_id,
            "file_key": file_key,
            "file_name": original_file_name,
            "file_path": permanent_path,
            "file_size": file_size,
            "chunks": len(chunks),
            "message": (
                "Document uploaded and processed "
                "successfully."
            ),
        }


    # -----------------------------------------------------
    # HTTP ERROR
    # -----------------------------------------------------

    except HTTPException:

        if os.path.exists(
            permanent_path
        ):

            try:

                os.remove(
                    permanent_path
                )

            except Exception:

                pass

        raise


    # -----------------------------------------------------
    # VALUE ERROR
    # -----------------------------------------------------

    except ValueError as e:

        if os.path.exists(
            permanent_path
        ):

            try:

                os.remove(
                    permanent_path
                )

            except Exception:

                pass


        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


    # -----------------------------------------------------
    # GENERAL ERROR
    # -----------------------------------------------------

    except Exception as e:

        if os.path.exists(
            permanent_path
        ):

            try:

                os.remove(
                    permanent_path
                )

            except Exception:

                pass


        raise HTTPException(
            status_code=500,
            detail=(
                f"Document processing failed: {str(e)}"
            ),
        )


# =========================================================
# ASK DOCUMENTS — RAG
# =========================================================

@app.post("/api/chats/{chat_id}/ask")
def ask_documents(
    chat_id: str,
    request: AskRequest,
):

    # -----------------------------------------------------
    # CHECK CHAT
    # -----------------------------------------------------

    chat = get_chat(
        chat_id
    )

    if not chat:

        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )


    # -----------------------------------------------------
    # VALIDATE QUESTION
    # -----------------------------------------------------

    question = request.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty",
        )


    # -----------------------------------------------------
    # GET CHAT-SPECIFIC CHROMA COLLECTION
    # -----------------------------------------------------

    collection = get_chat_collection(
        chat_id
    )


    # -----------------------------------------------------
    # CHECK WHETHER DOCUMENTS EXIST
    # -----------------------------------------------------

    results = collection.get()

    if not results.get("ids"):

        raise HTTPException(
            status_code=400,
            detail=(
                "No source found in this chat. "
                "Please upload a document or analyze a YouTube video first."
            ),
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
        user_message,
    )


    # -----------------------------------------------------
    # RETRIEVE RELEVANT CHUNKS
    # -----------------------------------------------------

    try:

        retrieval_result = retrieve_chunks(
            question,
            collection,
            top_k=5,
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Document retrieval failed: {str(e)}"
            ),
        )


    documents = retrieval_result.get(
        "documents",
        [],
    )


    metadatas = retrieval_result.get(
        "metadatas",
        [],
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
            "sources": [],
        }


        save_message(
            chat_id,
            assistant_message,
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
        start=1,
    ):

        metadata = (
            metadatas[i - 1]
            if i - 1 < len(metadatas)
            else {}
        )


        file_name = metadata.get(
            "file_name",
            "Unknown file",
        )


        page = metadata.get(
            "page",
            metadata.get(
                "page_number",
                "Unknown",
            ),
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
            "",
        )


        content = message.get(
            "content",
            "",
        )


        # -------------------------------------------------
        # IMPORTANT:
        # Don't include current question twice.
        # -------------------------------------------------

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
            question=question,
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Answer generation failed: {str(e)}"
            ),
        )


    # -----------------------------------------------------
    # BUILD SOURCES
    # -----------------------------------------------------

    grouped_sources = {}


    for metadata in metadatas:

        if not isinstance(
            metadata,
            dict,
        ):

            continue


        file_name = metadata.get(
            "file_name",
            "Unknown file",
        )


        source_type = metadata.get(
            "source_type",
            "document",
        )


        page = metadata.get(
            "page",
            metadata.get(
                "page_number"
            ),
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


        # -------------------------------------------------
        # YOUTUBE SUPPORT
        # -------------------------------------------------

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
                    ValueError,
                ):

                    pass


            if metadata.get(
                "video_id"
            ):

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


        # -------------------------------------------------
        # YOUTUBE METADATA
        # -------------------------------------------------

        if (
            source["source_type"]
            == "youtube"
        ):

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
        assistant_message,
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



# =========================================================
# YOUTUBE MODE SOURCE STATUS
# =========================================================

def _get_active_youtube_status(chat_id: str):
    """Return the analyzed YouTube source for a chat, if one exists."""
    video_url = None
    video_id = None
    analyzed = False

    # First use persisted chat messages. The analyze endpoint stores
    # video_url/video_id/youtube_summary on the assistant summary message.
    try:
        messages = get_messages(chat_id) or []
        for message in reversed(messages):
            if not isinstance(message, dict):
                continue
            candidate_url = message.get("video_url")
            if candidate_url:
                video_url = str(candidate_url).strip()
                video_id = message.get("video_id") or extract_video_id(video_url)
                analyzed = bool(message.get("youtube_summary"))
                if analyzed:
                    return {
                        "analyzed": True,
                        "video_url": video_url,
                        "video_id": video_id,
                    }
    except Exception:
        pass

    # Fallback to Chroma metadata so the mode still works even if an older
    # chat message did not persist the extra YouTube fields.
    try:
        collection = get_chat_collection(chat_id)
        result = collection.get(include=["metadatas"])
        for metadata in reversed(result.get("metadatas") or []):
            if not isinstance(metadata, dict):
                continue
            if metadata.get("source_type") != "youtube":
                continue

            video_id = metadata.get("video_id")
            if video_id:
                video_url = (
                    metadata.get("video_url")
                    or f"https://www.youtube.com/watch?v={video_id}"
                )
                return {
                    "analyzed": True,
                    "video_url": str(video_url).strip(),
                    "video_id": video_id,
                }
    except Exception:
        pass

    return {
        "analyzed": False,
        "video_url": None,
        "video_id": None,
    }


@app.get("/api/chats/{chat_id}/youtube/status")
def youtube_status(chat_id: str):
    chat = get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    return {
        "success": True,
        "chat_id": chat_id,
        **_get_active_youtube_status(chat_id),
    }

# =========================================================
# SUMMARIZE DOCUMENTS
# =========================================================

@app.post("/api/chats/{chat_id}/summarize")
def summarize_documents(
    chat_id: str,
    request: SummaryRequest,
):
    chat = get_chat(chat_id)

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )

    documents, metadatas = (
        _get_all_document_content(
            chat_id
        )
    )

    youtube = _get_active_youtube_status(chat_id)

    if not documents and not youtube.get("analyzed"):
        raise HTTPException(
            status_code=400,
            detail=(
                "No source found in this chat. "
                "Please upload a document or analyze a YouTube video first."
            ),
        )

    context, source_metadatas = (
        _build_document_context(
            documents,
            metadatas,
        )
    )

    if not context.strip():
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not extract readable content from the available source."
            ),
        )

    length = (
        request.length.strip()
        or "Medium"
    )

    if length not in {
        "Short",
        "Medium",
        "Detailed",
    }:
        length = "Medium"

    question = f"""
Summarize ALL available source content in this chat.

Summary length: {length}

Requirements:
- If the source is a YouTube transcript, summarize the video itself, not the existence of the transcript.
- Cover the important information and main ideas.
- Organize the answer with clear headings and bullet points where useful.
- Do not focus only on the beginning of the source.
- Do not invent information.
- Only use information supported by the supplied source context.
- If multiple sources are present, clearly distinguish important differences.
"""

    try:
        answer = generate_summary(
            context=context,
            question=question,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Summary generation failed: {str(e)}"
            ),
        )

    sources = _build_sources_from_metadatas(
        source_metadatas
    )

    assistant_message = {
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "mode": "summarize",
    }

    save_message(
        chat_id,
        assistant_message,
    )

    return {
        "success": True,
        "chat_id": chat_id,
        "answer": answer,
        "sources": sources,
        "mode": "summarize",
    }


# =========================================================
# COMPARE DOCUMENTS
# =========================================================

@app.post("/api/chats/{chat_id}/compare")
def compare_documents(
    chat_id: str,
    request: CompareRequest,
):
    chat = get_chat(chat_id)

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )

    selected_files = [
        file_name.strip()
        for file_name in request.files
        if isinstance(
            file_name,
            str,
        )
        and file_name.strip()
    ]

    selected_files = list(
        dict.fromkeys(
            selected_files
        )
    )

    if len(selected_files) < 2:
        raise HTTPException(
            status_code=400,
            detail=(
                "Select at least two documents to compare."
            ),
        )

    documents, metadatas = (
        _get_all_document_content(
            chat_id
        )
    )

    context, source_metadatas = (
        _build_document_context(
            documents,
            metadatas,
            selected_files=selected_files,
        )
    )

    selected_source_files = {
        metadata.get(
            "file_name"
        )
        for metadata in source_metadatas
        if isinstance(
            metadata,
            dict,
        )
    }

    if len(
        selected_source_files
    ) < 2:
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not find content for at least "
                "two of the selected documents."
            ),
        )

    question = """
Compare the selected documents carefully.

Provide:
1. A clear comparison table covering the main topics.
2. Key similarities.
3. Key differences.
4. Important unique points from each document.

Rules:
- Compare the documents directly rather than summarizing only one.
- If a topic is not mentioned in a document, say "Not specified".
- Do not invent information.
- Only use information supported by the supplied context.
"""

    try:
        answer = generate_comparison(
            context=context,
            question=question,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Comparison generation failed: {str(e)}"
            ),
        )

    sources = _build_sources_from_metadatas(
        source_metadatas
    )

    assistant_message = {
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "mode": "compare",
    }

    save_message(
        chat_id,
        assistant_message,
    )

    return {
        "success": True,
        "chat_id": chat_id,
        "answer": answer,
        "sources": sources,
        "mode": "compare",
        "files": selected_files,
    }


# =========================================================
# GENERATE QUIZ
# =========================================================

@app.post("/api/chats/{chat_id}/quiz")
def generate_document_quiz(
    chat_id: str,
    request: QuizRequest,
):
    chat = get_chat(chat_id)

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )

    question_count = max(
        3,
        min(
            int(request.num_questions),
            15,
        ),
    )

    difficulty = (
        request.difficulty.strip()
        or "Medium"
    )

    if difficulty not in {
        "Easy",
        "Medium",
        "Hard",
    }:
        difficulty = "Medium"

    collection = get_chat_collection(
        chat_id
    )

    try:
        retrieval_result = retrieve_chunks(
            "Generate a quiz covering the important concepts "
            "from all indexed sources in this chat",
            collection,
            top_k=10,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Quiz retrieval failed: {str(e)}"
            ),
        )

    documents = (
        retrieval_result.get(
            "documents",
            [],
        )
        or []
    )

    metadatas = (
        retrieval_result.get(
            "metadatas",
            [],
        )
        or []
    )

    if not documents:
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not retrieve source content for quiz generation."
            ),
        )

    context_parts = []

    for i, document in enumerate(
        documents,
        start=1,
    ):
        metadata = (
            metadatas[i - 1]
            if i - 1 < len(metadatas)
            else {}
        )

        if not isinstance(
            metadata,
            dict,
        ):
            metadata = {}

        file_name = metadata.get(
            "file_name",
            "Unknown file",
        )

        page = metadata.get(
            "page",
            metadata.get(
                "page_number",
                "Unknown",
            ),
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

    quiz_context = "\n".join(
        context_parts
    )

    try:
        raw_quiz = generate_quiz(
            context=quiz_context,
            num_questions=question_count,
            difficulty=difficulty,
        )

        quiz_data = _normalize_quiz_data(
            raw_quiz
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Quiz generation failed: {str(e)}"
            ),
        )

    if quiz_data is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "The quiz generator returned an invalid "
                "quiz format. Please try again."
            ),
        )

    quiz_data["questions"] = (
        quiz_data["questions"][
            :question_count
        ]
    )

    if not quiz_data["questions"]:
        raise HTTPException(
            status_code=500,
            detail=(
                "The quiz generator did not return "
                "any valid questions."
            ),
        )

    sources = _build_sources_from_metadatas(
        metadatas
    )

    assistant_message = {
        "role": "assistant",
        "content": (
            f"🧠 Generated an interactive "
            f"{len(quiz_data['questions'])}-question "
            f"{difficulty} quiz."
        ),
        "sources": sources,
        "mode": "quiz",
        # Persist the complete quiz so refresh/chat switching can
        # reconstruct the interactive quiz in the frontend.
        "quiz": quiz_data,
        "difficulty": difficulty,
    }

    save_message(
        chat_id,
        assistant_message,
    )

    return {
        "success": True,
        "chat_id": chat_id,
        "quiz": quiz_data,
        "sources": sources,
        "mode": "quiz",
        "difficulty": difficulty,
    }


# =========================================================
# GENERATE FLASHCARDS
# =========================================================

@app.post("/api/chats/{chat_id}/flashcards")
def generate_document_flashcards(
    chat_id: str,
    request: FlashcardsRequest,
):
    chat = get_chat(chat_id)

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )

    card_count = max(
        3,
        min(
            int(request.count),
            30,
        ),
    )

    difficulty = (
        request.difficulty.strip()
        or "Medium"
    )

    if difficulty not in {
        "Easy",
        "Medium",
        "Hard",
    }:
        difficulty = "Medium"

    documents, metadatas = (
        _get_all_document_content(
            chat_id
        )
    )

    if not documents:
        raise HTTPException(
            status_code=400,
            detail=(
                "No documents found in this chat. "
                "Please upload a document first."
            ),
        )

    context, source_metadatas = (
        _build_document_context(
            documents,
            metadatas,
        )
    )

    if not context.strip():
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not extract readable source content for flashcards."
            ),
        )

    flashcard_request = f"""
Create exactly {card_count} study flashcards from
the supplied document context.

Difficulty: {difficulty}

Return ONLY valid JSON.
Do not use Markdown fences.

Use exactly this structure:

{{
  "flashcards": [
    {{
      "front": "A concise question or concept",
      "back": "A concise, accurate answer or explanation",
      "source": "File name and page"
    }}
  ]
}}

Rules:
- Create exactly {card_count} flashcards.
- Front should test one clear concept.
- Back should provide the answer or explanation.
- Keep cards concise and useful for revision.
- Cover different important concepts instead of repeating the same fact.
- Every card must be supported by the supplied source context.
- Do not invent information.
- Include the source file and page when available.

Document context:

{context}
"""

    try:
        raw_flashcards = generate_response(
            context=context,
            question=flashcard_request,
        )

        flashcard_data = (
            _normalize_flashcard_data(
                raw_flashcards
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Flashcard generation failed: {str(e)}"
            ),
        )

    if flashcard_data is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "The flashcard generator returned an "
                "invalid format. Please try again."
            ),
        )

    flashcard_data["flashcards"] = (
        flashcard_data["flashcards"][
            :card_count
        ]
    )

    if not flashcard_data["flashcards"]:
        raise HTTPException(
            status_code=500,
            detail=(
                "The flashcard generator did not return "
                "any valid cards."
            ),
        )

    sources = _build_sources_from_metadatas(
        source_metadatas
    )

    assistant_message = {
        "role": "assistant",
        "content": (
            f"📑 Generated "
            f"{len(flashcard_data['flashcards'])} "
            "interactive flashcards."
        ),
        "sources": sources,
        "mode": "flashcards",
        # Persist the complete flashcard set so refresh/chat switching can
        # reconstruct the interactive cards in the frontend.
        "flashcards": flashcard_data,
        "difficulty": difficulty,
    }

    save_message(
        chat_id,
        assistant_message,
    )

    return {
        "success": True,
        "chat_id": chat_id,
        "flashcards": flashcard_data,
        "sources": sources,
        "mode": "flashcards",
        "difficulty": difficulty,
    }


# =========================================================
# YOUTUBE — TRANSCRIPT INGESTION + INITIAL SUMMARY
# =========================================================

@app.post("/api/chats/{chat_id}/youtube/analyze")
def analyze_youtube_video(
    chat_id: str,
    request: YouTubeAnalyzeRequest,
):
    """
    Fast/free-tier friendly YouTube initialization.

    1. Extract the transcript.
    2. Store transcript segments in the chat's Chroma collection.
    3. Generate ONE text-only summary from the transcript.
    4. Persist that summary in chat history as the video's context.

    No full-video multimodal Gemini request is made here.
    This keeps the initial YouTube setup much faster and cheaper.
    """

    chat = get_chat(chat_id)
    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found",
        )

    video_url = request.video_url.strip()
    if not video_url:
        raise HTTPException(
            status_code=400,
            detail="YouTube video URL is required",
        )

    try:
        video_id = extract_video_id(video_url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")

        transcript_segments = extract_youtube_transcript(video_url)
        if not transcript_segments:
            raise ValueError("No transcript could be extracted from this video")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"YouTube transcript extraction failed: {str(e)}",
        )

    collection = get_chat_collection(chat_id)
    video_name = f"YouTube Video - {video_id}"

    # add_youtube_transcript already performs a duplicate check.
    try:
        add_youtube_transcript(
            collection=collection,
            transcript_segments=transcript_segments,
            video_id=video_id,
            video_name=video_name,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"YouTube transcript indexing failed: {str(e)}",
        )

    # Read back only this video's transcript so the initial summary is
    # grounded in the same ChromaDB source used for later questions.
    try:
        indexed = collection.get(
            where={"video_id": video_id},
            include=["documents", "metadatas"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"YouTube transcript retrieval failed: {str(e)}",
        )

    documents = indexed.get("documents") or []
    metadatas = indexed.get("metadatas") or []

    if not documents:
        raise HTTPException(
            status_code=500,
            detail="YouTube transcript was not available after indexing.",
        )

    # Preserve chronological order for a coherent summary.
    items = []
    for index, document in enumerate(documents):
        metadata = metadatas[index] if index < len(metadatas) else {}
        if not isinstance(metadata, dict):
            metadata = {}
        try:
            start_time = float(metadata.get("start_time", 0))
        except (TypeError, ValueError):
            start_time = 0.0
        items.append((start_time, str(document).strip()))

    items.sort(key=lambda item: item[0])

    transcript_parts = []
    for start_time, document in items:
        if not document:
            continue
        minutes = int(start_time // 60)
        seconds = int(start_time % 60)
        transcript_parts.append(
            f"[{minutes:02d}:{seconds:02d}] {document}"
        )

    transcript_context = "\n".join(transcript_parts)

    summary_prompt = f"""
You are summarizing a YouTube video for a RAG assistant.

Create a clear, useful summary using ONLY the supplied transcript.
Do not use outside knowledge and do not invent details.

Include:
- A short overview of what the video is about.
- The main topics/concepts in logical order.
- Important explanations, examples, or conclusions.
- A concise list of key takeaways.
- Important timestamps when they are present in the transcript.

Keep the summary reasonably concise so the user can read it in chat,
but cover the important content rather than summarizing only the beginning.

VIDEO TRANSCRIPT
=========================================================
{transcript_context}
=========================================================
"""

    try:
        summary = generate_response(
            context=transcript_context,
            question=summary_prompt,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"YouTube summary generation failed: {str(e)}",
        )

    assistant_message = {
        "role": "assistant",
        "content": summary,
        "video_url": video_url,
        "source_type": "youtube",
        "youtube_summary": True,
        "video_id": video_id,
    }

    save_message(chat_id, assistant_message)

    return {
        "success": True,
        "chat_id": chat_id,
        "video_url": video_url,
        "video_id": video_id,
        "answer": summary,
        "summary": summary,
        "source_type": "youtube",
        "transcript_segments": len(transcript_parts),
    }


# =========================================================
# YOUTUBE LEVEL 2 — MULTIMODAL / TRANSCRIPT ASK
# =========================================================

@app.post("/api/chats/{chat_id}/youtube/ask")
def ask_youtube_multimodal(
    chat_id: str,
    request: YouTubeAskRequest,
):
    """
    Answer a question about an already indexed YouTube video.

    Normal questions use transcript RAG (fast/free-tier friendly).
    Questions that clearly require a visual/timestamp check use the
    existing multimodal Gemini function on a targeted video window.
    """

    chat = get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    video_url = request.video_url.strip()
    question = request.question.strip()

    if not video_url:
        raise HTTPException(status_code=400, detail="YouTube video URL is required")
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    collection = get_chat_collection(chat_id)

    # Retrieve transcript chunks relevant to the question.
    try:
        retrieval_result = retrieve_chunks(
            question,
            collection,
            top_k=5,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"YouTube transcript retrieval failed: {str(e)}",
        )

    documents = retrieval_result.get("documents") or []
    metadatas = retrieval_result.get("metadatas") or []

    # Restrict context to YouTube transcript chunks.
    context_parts = []
    for index, document in enumerate(documents):
        metadata = metadatas[index] if index < len(metadatas) else {}
        if not isinstance(metadata, dict):
            metadata = {}
        if metadata.get("source_type") != "youtube":
            continue

        file_name = metadata.get("file_name", "YouTube transcript")
        start_time = metadata.get("start_time")
        timestamp_text = ""
        if start_time is not None:
            try:
                seconds = int(float(start_time))
                timestamp_text = f"{seconds // 60:02d}:{seconds % 60:02d}"
            except (TypeError, ValueError):
                timestamp_text = str(start_time)

        context_parts.append(
            f"SOURCE {len(context_parts) + 1}\n"
            f"File: {file_name}\n"
            f"Timestamp: [{timestamp_text}]\n"
            f"Transcript: {document}"
        )

    retrieved_context = "\n\n".join(context_parts)

    if not retrieved_context:
        retrieved_context = "No directly matching transcript chunk was retrieved."

    # Include the saved initial summary and recent conversation so follow-up
    # questions can refer naturally to the video's earlier discussion.
    previous_messages = get_messages(chat_id) or []
    conversation_parts = []
    saved_summary = ""

    for message in previous_messages:
        if not isinstance(message, dict):
            continue
        content = str(message.get("content", ""))
        role = message.get("role", "")
        if message.get("youtube_summary") and not saved_summary:
            saved_summary = content
        if content and content != question:
            conversation_parts.append(
                f"{'User' if role == 'user' else 'Assistant'}: {content}"
            )

    conversation_context = "\n".join(conversation_parts[-10:])

    final_context = f"""
YOUTUBE VIDEO SUMMARY:
{saved_summary or 'No saved summary is available.'}

RELEVANT TRANSCRIPT CHUNKS:
{retrieved_context}

RECENT CONVERSATION:
{conversation_context}
"""

    # Save the user question before generating the answer, matching the
    # existing chat persistence behavior.
    save_message(
        chat_id,
        {
            "role": "user",
            "content": question,
            "video_url": video_url,
        },
    )

    try:
        if should_use_youtube_multimodal(question):
            # Existing multimodal engine is retained for visual/timestamp
            # questions where transcript-only RAG is insufficient.
            answer = generate_youtube_multimodal_response(
                video_url=video_url,
                context=final_context,
                question=question,
            )
            response_mode = "youtube_multimodal"
        else:
            answer = generate_response(
                context=final_context,
                question=question,
            )
            response_mode = "youtube_transcript_rag"
    except Exception as e:
        print("❌ YouTube answer generation failed:", e)
        raise HTTPException(
            status_code=500,
            detail=f"YouTube answer generation failed: {str(e)}",
        )

    assistant_message = {
        "role": "assistant",
        "content": answer,
        "video_url": video_url,
        "source_type": "youtube",
        "response_mode": response_mode,
    }

    save_message(chat_id, assistant_message)

    return {
        "success": True,
        "chat_id": chat_id,
        "video_url": video_url,
        "question": question,
        "answer": answer,
        "source_type": "youtube",
        "response_mode": response_mode,
    }

