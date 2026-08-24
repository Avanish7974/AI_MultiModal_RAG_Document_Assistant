import uuid

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import (
    SentenceTransformerEmbeddingFunction
)


# =========================================================
# EMBEDDING FUNCTION
# =========================================================

embedding_function = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)


# =========================================================
# CHROMA CLIENT
# =========================================================

def get_chroma_client():
    """
    Create the persistent ChromaDB client.

    Persistence remains organized by chat-specific
    collections.
    """

    client = chromadb.PersistentClient(
        path="./chroma_db",
        settings=Settings(
            anonymized_telemetry=False
        ),
    )

    return client


# =========================================================
# GET CHROMA COLLECTION
# =========================================================

def get_chroma_collection(
    collection_name="rag_documents"
):
    """
    Return a ChromaDB collection.

    The application normally passes a chat-specific
    collection name such as:

        rag_chat_<chat_id>

    The default value is retained for backward
    compatibility.
    """

    client = get_chroma_client()

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function,
    )

    return collection


# =========================================================
# CREATE CHAT COLLECTION
# =========================================================

def create_chat_collection(chat_id):
    """
    Create or retrieve the ChromaDB collection
    belonging to one chat.
    """

    collection_name = f"rag_chat_{chat_id}"

    return get_chroma_collection(
        collection_name=collection_name
    )


# =========================================================
# GET CHAT COLLECTION
# =========================================================

def get_chat_collection(chat_id):
    """
    Return the ChromaDB collection belonging
    to a chat.
    """

    return create_chat_collection(
        chat_id
    )


# =========================================================
# CHAT COLLECTION NAME
# =========================================================

def get_chat_collection_name(chat_id):
    """
    Return the deterministic ChromaDB collection
    name for a chat.
    """

    return f"rag_chat_{chat_id}"


# =========================================================
# ADD NORMAL DOCUMENTS
# =========================================================

def add_documents(
    collection,
    chunks,
    file_name
):
    """
    Add normal document chunks to ChromaDB.

    Existing behavior is preserved.

    Metadata:

        file_name
        page
        chunk_number
        source_type
    """

    if not chunks:
        return

    # -----------------------------------------------------
    # DUPLICATE FILE CHECK
    # -----------------------------------------------------

    existing = collection.get(
        where={
            "file_name": file_name
        }
    )

    if existing["ids"]:
        return

    # -----------------------------------------------------
    # UNIQUE IDS
    # -----------------------------------------------------

    ids = [
        str(uuid.uuid4())
        for _ in chunks
    ]

    # -----------------------------------------------------
    # DOCUMENT TEXT
    # -----------------------------------------------------

    documents = [
        chunk["text"]
        for chunk in chunks
    ]

    # -----------------------------------------------------
    # METADATA
    # -----------------------------------------------------

    metadatas = []

    for i, chunk in enumerate(chunks):

        metadatas.append(
            {
                "file_name": file_name,
                "page": str(
                    chunk.get(
                        "page",
                        "Unknown"
                    )
                ),
                "chunk_number": i + 1,
                "source_type": "document",
            }
        )

    # -----------------------------------------------------
    # STORE
    # -----------------------------------------------------

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )


# =========================================================
# ADD YOUTUBE TRANSCRIPT
# =========================================================

def add_youtube_transcript(
    collection,
    transcript_segments,
    video_id,
    video_name=None,
    youtube_url=None
):
    """
    Add YouTube transcript segments to ChromaDB.

    Each segment preserves its original timestamp.

    Expected transcript segment:

        {
            "text": "...",
            "start": 125.4,
            "duration": 8.2
        }

    Metadata:

        file_name
        page
        chunk_number
        source_type
        video_id
        youtube_url
        start_time
        duration

    youtube_url is stored so Level-2 multimodal
    analysis can send the original YouTube video
    to Gemini.
    """

    if not transcript_segments:
        return

    # -----------------------------------------------------
    # VIDEO NAME
    # -----------------------------------------------------

    file_name = (
        video_name
        or f"YouTube Video - {video_id}"
    )

    # -----------------------------------------------------
    # VIDEO URL
    # -----------------------------------------------------

    stored_youtube_url = (
        youtube_url
        or f"https://www.youtube.com/watch?v={video_id}"
    )

    # -----------------------------------------------------
    # DUPLICATE CHECK
    # -----------------------------------------------------

    existing = collection.get(
        where={
            "file_name": file_name
        }
    )

    if existing.get("ids"):
        return

    # -----------------------------------------------------
    # DOCUMENT TEXT
    # -----------------------------------------------------

    documents = [
        str(
            segment.get(
                "text",
                ""
            )
        ).strip()
        for segment in transcript_segments
    ]

    # -----------------------------------------------------
    # REMOVE EMPTY SEGMENTS
    # -----------------------------------------------------

    valid_items = []

    for index, document in enumerate(documents):

        if document:

            valid_items.append(
                (
                    index,
                    document
                )
            )

    if not valid_items:
        return

    # -----------------------------------------------------
    # REBUILD VALID IDS/DOCUMENTS/METADATA
    # -----------------------------------------------------

    valid_ids = []

    valid_documents = []

    valid_metadatas = []

    for chunk_number, (
        original_index,
        document
    ) in enumerate(
        valid_items,
        start=1
    ):

        segment = transcript_segments[
            original_index
        ]

        # -------------------------------------------------
        # TIMESTAMP
        # -------------------------------------------------

        start_time = float(
            segment.get(
                "start",
                0
            )
        )

        # -------------------------------------------------
        # DURATION
        # -------------------------------------------------

        duration = float(
            segment.get(
                "duration",
                0
            )
        )

        # -------------------------------------------------
        # ID
        # -------------------------------------------------

        valid_ids.append(
            str(uuid.uuid4())
        )

        # -------------------------------------------------
        # DOCUMENT
        # -------------------------------------------------

        valid_documents.append(
            document
        )

        # -------------------------------------------------
        # METADATA
        # -------------------------------------------------

        valid_metadatas.append(
            {
                "file_name": file_name,
                "page": "YouTube",
                "chunk_number": chunk_number,
                "source_type": "youtube",

                # Existing Level-1 metadata
                "video_id": video_id,
                "start_time": start_time,
                "duration": duration,

                # NEW Level-2 metadata
                "youtube_url": stored_youtube_url,
            }
        )

    # -----------------------------------------------------
    # STORE YOUTUBE TRANSCRIPT
    # -----------------------------------------------------

    collection.add(
        ids=valid_ids,
        documents=valid_documents,
        metadatas=valid_metadatas,
    )


# =========================================================
# DELETE CHAT COLLECTION
# =========================================================

def delete_chat_collection(chat_id):
    """
    Permanently delete the ChromaDB collection
    belonging to the chat.
    """

    client = get_chroma_client()

    collection_name = get_chat_collection_name(
        chat_id
    )

    try:

        client.delete_collection(
            name=collection_name
        )

    except Exception:

        # Collection may not exist.
        pass


# =========================================================
# CLEAR CHAT COLLECTION
# =========================================================

def clear_chat_collection(chat_id):
    """
    Remove all documents from a chat collection
    while keeping the collection itself.
    """

    collection = get_chat_collection(
        chat_id
    )

    existing = collection.get()

    ids = existing.get(
        "ids",
        []
    )

    if ids:

        collection.delete(
            ids=ids
        )


# =========================================================
# GET CHAT DOCUMENT COUNT
# =========================================================

def get_chat_document_count(chat_id):
    """
    Return the number of stored chunks
    in a chat.
    """

    collection = get_chat_collection(
        chat_id
    )

    return collection.count()


# =========================================================
# CHECK WHETHER FILE EXISTS
# =========================================================

def file_exists_in_chat(
    chat_id,
    file_name
):
    """
    Check whether a specific file has already
    been indexed inside a chat.
    """

    collection = get_chat_collection(
        chat_id
    )

    existing = collection.get(
        where={
            "file_name": file_name
        }
    )

    return bool(
        existing.get("ids")
    )