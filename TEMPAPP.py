import streamlit as st
import streamlit.components.v1 as components
import json
import re
from urllib.parse import quote

from src.utils.file_handler import save_uploaded_file
from src.loaders.youtube_loader import extract_youtube_transcript, extract_video_id
from src.vectorstore.chroma_store import add_youtube_transcript
from src.vectorstore.chroma_store import (
    get_chat_collection,
    delete_chat_collection,
)
from src.retriever.retriever import retrieve_chunks
from src.services.document_service import process_document
from src.services.comparison_service import generate_comparison
from src.services.summary_service import generate_summary
from src.services.quiz_service import generate_quiz
from src.services.data_analysis_service import (
    analyze_dataframe,
    build_analysis_context
)
from src.loaders.spreadsheet_loader import (
    load_csv_dataframe,
    load_xlsx_dataframes
)
from src.llm.gemini import (
    generate_response,
    generate_youtube_multimodal_response,
)
from src.services.chat_manager import (
    initialize_chat_database,
    create_chat,
    list_chats,
    get_messages,
    get_chat_files,
    save_message,
    add_file,
    update_chat_title,
    get_chat,
    delete_chat,
)


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Multi-Modal RAG Document Assistant",
    page_icon="📄",
    layout="wide"
)


# =========================================================
# UI STYLING
# =========================================================

st.markdown(
    """
    <style>
    .app-subtitle {
        color: #8b93a3;
        margin-top: -12px;
        margin-bottom: 18px;
    }

    /* Overall balance */
    [data-testid="stSidebar"] {
        min-width: 320px;
        max-width: 360px;
    }

    [data-testid="stAppViewContainer"] .block-container {
        max-width: 1250px;
        padding-top: 2rem;
        padding-left: 2.2rem;
        padding-right: 2.2rem;
    }

    /* Compact sidebar controls */
    [data-testid="stSidebar"] .stButton > button {
        min-height: 40px;
        border-radius: 9px;
        padding: 0.35rem 0.65rem;
    }

    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
        align-items: center;
    }

    [data-testid="stSidebar"] .stPopover > button {
        min-height: 40px;
        padding: 0.2rem 0.35rem;
        font-size: 1.05rem;
    }

    /* Action buttons */
    .action-caption {
        margin-top: -8px;
        margin-bottom: 8px;
    }

    /* Source cards */
    .source-card {
        border: 1px solid rgba(128,128,128,.20);
        border-radius: 10px;
        padding: 10px 12px;
        margin: 7px 0;
        background: rgba(128,128,128,.035);
    }

    .source-card a {
        text-decoration: none;
    }

    /* Sidebar sections */
    .sidebar-section {
        margin-top: 4px;
        margin-bottom: 8px;
        font-weight: 650;
    }

    /* Avoid excessive vertical gaps in sidebar */
    [data-testid="stSidebar"] hr {
        margin: 0.65rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# CHAT / SESSION STATE
# =========================================================

initialize_chat_database()


def _reset_chat_runtime_state():
    """Reset all runtime state that belongs to the active chat."""
    st.session_state.messages = []
    st.session_state.processed_files = set()
    st.session_state.spreadsheet_data = {}
    st.session_state.quiz_data = None
    st.session_state.quiz_submitted = False
    st.session_state.quiz_answers = {}


def _load_chat_runtime_state(chat_id):
    """Load a saved chat's messages/files into Streamlit runtime state."""
    _reset_chat_runtime_state()

    st.session_state.messages = get_messages(chat_id)

    for file_record in get_chat_files(chat_id):
        file_key = file_record.get("file_key")
        file_name = file_record.get("file_name")
        file_path = file_record.get("file_path")

        if file_key:
            st.session_state.processed_files.add(file_key)

        if not file_path:
            continue

        extension = (
            file_name.rsplit(".", 1)[-1].lower()
            if file_name and "." in file_name
            else ""
        )

        try:
            if extension == "csv":
                dataframe = load_csv_dataframe(file_path)
                st.session_state.spreadsheet_data[
                    file_key
                ] = {
                    "file_name": file_name,
                    "sheet_name": None,
                    "dataframe": dataframe,
                }

            elif extension in ["xlsx", "xls"]:
                dataframes = load_xlsx_dataframes(file_path)

                for sheet_name, dataframe in dataframes.items():
                    st.session_state.spreadsheet_data[
                        f"{file_key}::{sheet_name}"
                    ] = {
                        "file_name": file_name,
                        "sheet_name": sheet_name,
                        "dataframe": dataframe,
                    }

        except Exception:
            # A missing/invalid spreadsheet should not prevent an old
            # chat's normal RAG conversation from loading.
            pass


def _append_message(message):
    """Append a message to the active chat and persist it."""
    st.session_state.messages.append(message)
    save_message(
        st.session_state.current_chat_id,
        message
    )


# ---------------------------------------------------------
# CREATE A NEW ACTIVE CHAT AFTER APPLICATION RESTART
# ---------------------------------------------------------

if "current_chat_id" not in st.session_state:
    new_chat_id = create_chat()
    st.session_state.current_chat_id = new_chat_id
    _reset_chat_runtime_state()

# ---------------------------------------------------------
# NORMAL RUNTIME STATE
# ---------------------------------------------------------

if "messages" not in st.session_state:
    _load_chat_runtime_state(
        st.session_state.current_chat_id
    )

if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()

if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None

if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False

if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}

if "flashcards_data" not in st.session_state:
    st.session_state.flashcards_data = None

if "flashcard_index" not in st.session_state:
    st.session_state.flashcard_index = 0

if "flashcard_flipped" not in st.session_state:
    st.session_state.flashcard_flipped = False

if "spreadsheet_data" not in st.session_state:
    st.session_state.spreadsheet_data = {}

if "youtube_player_video_id" not in st.session_state:
    st.session_state.youtube_player_video_id = None

if "youtube_player_start_time" not in st.session_state:
    st.session_state.youtube_player_start_time = 0


# =========================================================
# CURRENT CHAT CHROMA COLLECTION
# =========================================================

collection = get_chat_collection(
    st.session_state.current_chat_id
)


# =========================================================
# UI HELPERS
# =========================================================

def _page_sort_key(value):
    value = str(value)
    return (0, int(value)) if value.isdigit() else (1, value.lower())


def _format_timestamp(seconds):
    """Convert seconds to a compact YouTube timestamp."""
    try:
        total = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        total = 0
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _get_youtube_url_for_question(retrieved_metadatas, youtube_videos):
    """
    Select the YouTube video to use for Level-2 multimodal analysis.

    Priority:
        1. A YouTube URL from the retrieved chunks.
        2. The first indexed YouTube video in the current chat.
    """
    for metadata in retrieved_metadatas or []:
        if not isinstance(metadata, dict):
            continue

        if metadata.get("source_type") != "youtube":
            continue

        youtube_url = metadata.get("youtube_url")

        if youtube_url:
            return youtube_url

        video_id = metadata.get("video_id")

        if video_id:
            return (
                "https://www.youtube.com/watch?v="
                f"{quote(str(video_id))}"
            )

    for video_id, video in (youtube_videos or {}).items():
        youtube_url = video.get("youtube_url")

        if youtube_url:
            return youtube_url

        if video_id:
            return (
                "https://www.youtube.com/watch?v="
                f"{quote(str(video_id))}"
            )

    return None


def _render_youtube_player(youtube_videos):
    """Render the Level-1 YouTube player only for chats containing YouTube sources."""
    if not youtube_videos:
        return

    video_ids = list(youtube_videos.keys())

    current_video_id = st.session_state.get("youtube_player_video_id")
    if current_video_id not in video_ids:
        current_video_id = video_ids[0]
        st.session_state.youtube_player_video_id = current_video_id
        st.session_state.youtube_player_start_time = 0

    # Collect transcript timestamps for the selected video.
    timestamps = []
    try:
        metadata_rows = collection.get(include=["metadatas"]).get("metadatas") or []
        for metadata in metadata_rows:
            if not isinstance(metadata, dict):
                continue
            if metadata.get("source_type") != "youtube":
                continue
            if str(metadata.get("video_id")) != str(current_video_id):
                continue
            start_time = metadata.get("start_time")
            if start_time is not None:
                try:
                    timestamps.append(max(0, int(float(start_time))))
                except (TypeError, ValueError):
                    pass
    except Exception:
        timestamps = []

    timestamps = sorted(set(timestamps))

    st.markdown("### 🎥 YouTube Player")

    player_col, controls_col = st.columns([1.65, 1], gap="medium")

    with controls_col:
        video_options = {
            video_id: youtube_videos[video_id].get(
                "file_name", f"YouTube Video - {video_id}"
            )
            for video_id in video_ids
        }

        selected_video = st.selectbox(
            "Video",
            video_ids,
            index=video_ids.index(current_video_id),
            format_func=lambda value: video_options.get(value, value),
            key=f"youtube_player_video_{st.session_state.current_chat_id}",
        )

        if selected_video != st.session_state.youtube_player_video_id:
            st.session_state.youtube_player_video_id = selected_video
            st.session_state.youtube_player_start_time = 0
            st.rerun()

        jump_time = st.number_input(
            "Jump to timestamp (seconds)",
            min_value=0,
            value=int(st.session_state.get("youtube_player_start_time", 0)),
            step=5,
            key=f"youtube_jump_seconds_{st.session_state.current_chat_id}",
        )

        if st.button(
            "▶ Jump & Play",
            use_container_width=True,
            type="primary",
            key=f"youtube_jump_{st.session_state.current_chat_id}",
        ):
            st.session_state.youtube_player_start_time = int(jump_time)
            st.rerun()

        if timestamps:
            timestamp_labels = [
                f"{_format_timestamp(seconds)} — transcript segment"
                for seconds in timestamps
            ]
            selected_label = st.selectbox(
                "Transcript timestamps",
                timestamp_labels,
                key=f"youtube_timestamp_{st.session_state.current_chat_id}_{selected_video}",
            )
            selected_seconds = timestamps[timestamp_labels.index(selected_label)]

            if st.button(
                "⏱ Jump to selected timestamp",
                use_container_width=True,
                key=f"youtube_timestamp_jump_{st.session_state.current_chat_id}_{selected_video}",
            ):
                st.session_state.youtube_player_start_time = selected_seconds
                st.rerun()

        st.caption(
            "The player appears only when this chat contains an indexed YouTube video."
        )

    with player_col:
        start_time = int(st.session_state.get("youtube_player_start_time", 0))
        embed_url = (
            f"https://www.youtube.com/embed/{quote(str(selected_video))}"
            f"?start={start_time}&autoplay=1&rel=0"
        )

        components.html(
            f"""
            <div style="width:100%; aspect-ratio:16/9; border-radius:12px; overflow:hidden;">
                <iframe
                    src="{embed_url}"
                    title="YouTube video player"
                    style="width:100%; height:100%; border:0;"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    allowfullscreen>
                </iframe>
            </div>
            """,
            height=430,
            scrolling=False,
        )


def _render_source_cards(sources, title="📚 Sources"):
    if not sources:
        return

    st.markdown(f"### {title}")

    for source in sources:
        file_name = source.get("file_name", "Unknown source")
        source_type = source.get("source_type", "document")

        if source_type == "youtube" and source.get("video_id"):
            video_id = source["video_id"]
            timestamps = source.get("timestamps", [])

            links = []
            for timestamp in timestamps:
                try:
                    seconds = int(float(timestamp))
                except (TypeError, ValueError):
                    seconds = 0

                label = _format_timestamp(seconds)
                url = (
                    f"https://www.youtube.com/watch?v="
                    f"{quote(str(video_id))}&t={seconds}s"
                )
                links.append(
                    f'<a href="{url}" target="_blank">▶ {label}</a>'
                )

            location_text = (
                " • ".join(links)
                if links
                else "YouTube transcript"
            )

            st.markdown(
                f'<div class="source-card">'
                f'<strong>🎥 {file_name}</strong><br>'
                f'<small>{location_text}</small>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            pages = source.get("pages", [])
            pages = sorted(list(pages), key=_page_sort_key)
            page_text = (
                ", ".join(map(str, pages))
                if pages
                else "Location unavailable"
            )
            st.markdown(
                f'<div class="source-card"><strong>📄 {file_name}</strong><br>'
                f'<small>Pages / locations: {page_text}</small></div>',
                unsafe_allow_html=True
            )


def _build_sources(metadatas):
    grouped = {}

    for metadata in metadatas or []:
        if not isinstance(metadata, dict):
            continue

        file_name = metadata.get("file_name", "Unknown source")
        source_type = metadata.get("source_type", "document")

        if file_name not in grouped:
            grouped[file_name] = {
                "source_type": source_type,
                "pages": set(),
                "timestamps": set(),
                "video_id": metadata.get("video_id"),
            }

        page = metadata.get("page", metadata.get("page_number"))
        if page is not None:
            grouped[file_name]["pages"].add(str(page))

        if source_type == "youtube":
            start_time = metadata.get("start_time")
            if start_time is not None:
                grouped[file_name]["timestamps"].add(float(start_time))
            if metadata.get("video_id"):
                grouped[file_name]["video_id"] = metadata["video_id"]

    sources = []

    for file_name, info in grouped.items():
        source = {
            "file_name": file_name,
            "pages": sorted(
                info["pages"],
                key=_page_sort_key
            ),
            "source_type": info["source_type"],
        }

        if info["source_type"] == "youtube":
            source["video_id"] = info["video_id"]
            source["timestamps"] = sorted(info["timestamps"])

        sources.append(source)

    return sources


def _render_retrieved_context(documents, metadatas, label="🔍 View Retrieved Context"):
    if not documents:
        return
    with st.expander(label):
        st.caption(f"Retrieved {len(documents)} relevant chunks.")
        for i, document in enumerate(documents, start=1):
            metadata = metadatas[i - 1] if i - 1 < len(metadatas) else {}
            if not isinstance(metadata, dict):
                metadata = {}
            file_name = metadata.get("file_name", "Unknown file")
            page = metadata.get("page", metadata.get("page_number", "Unknown"))

            if metadata.get("source_type") == "youtube":
                start_time = metadata.get("start_time", 0)
                video_id = metadata.get("video_id")
                timestamp = _format_timestamp(start_time)
                st.markdown(
                    f"**Chunk {i}** — 🎥 {file_name} | "
                    f"Timestamp [{timestamp}]"
                )
                if video_id:
                    url = (
                        f"https://www.youtube.com/watch?v="
                        f"{quote(str(video_id))}&t={int(float(start_time))}s"
                    )
                    st.markdown(
                        f"[▶ Open video at {timestamp}]({url})"
                    )
            else:
                st.markdown(
                    f"**Chunk {i}** — 📄 {file_name} | Location {page}"
                )

            st.write(document)
            if i != len(documents):
                st.markdown("---")


def _collection_stats():
    results = collection.get(include=["metadatas"])
    metadatas = results.get("metadatas") or []
    by_file = {}
    for metadata in metadatas:
        if not isinstance(metadata, dict):
            continue
        file_name = metadata.get("file_name", "Unknown file")
        by_file[file_name] = by_file.get(file_name, 0) + 1
    return len(by_file), len(metadatas), by_file


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        """
        <style>
        /* Compact, consistent Recent Chats rows */
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
            align-items: center;
        }

        /* Keep the three-dot control visually small and clean */
        [data-testid="stSidebar"] button[kind="secondary"] {
            min-height: 42px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("📄 RAG Assistant")

    # -----------------------------------------------------
    # NEW CHAT
    # -----------------------------------------------------

    if st.button(
        "➕ New Chat",
        use_container_width=True
    ):
        new_chat_id = create_chat()
        st.session_state.current_chat_id = new_chat_id
        _reset_chat_runtime_state()
        st.rerun()

    st.markdown("---")

    # -----------------------------------------------------
    # CHAT HISTORY
    # -----------------------------------------------------

    st.markdown("### 🕘 Recent Chats")

    chats = list_chats()

    # -----------------------------------------------------
    # REMOVE EMPTY CHAT ENTRIES FROM RECENT CHATS
    # -----------------------------------------------------
    #
    # A chat should appear in Recent Chats only after it has
    # an actual conversation message. A freshly-created chat
    # is treated as a temporary draft until the user sends
    # something.
    #
    # Empty non-active chats are removed from persistence.
    # The active empty chat is kept internally so the user can
    # start a new conversation without the app creating a
    # visible "New Chat" history entry.
    cleaned_chats = []

    for chat in chats:
        chat_id = chat["chat_id"]
        messages = get_messages(chat_id)

        if messages:
            cleaned_chats.append(chat)
        elif chat_id != st.session_state.current_chat_id:
            try:
                delete_chat(chat_id)
            except Exception:
                pass

    chats = cleaned_chats

    for chat in chats:

        chat_id = chat["chat_id"]
        title = chat.get("title") or "New Chat"

        # Each chat row intentionally has ONLY:
        #   1. The chat title button
        #   2. One ⋮ menu containing Rename + Delete
        history_col, menu_col = st.columns(
            [0.86, 0.14],
            gap="small"
        )

        with history_col:

            if chat_id == st.session_state.current_chat_id:
                label = f"🟢 {title}"
            else:
                label = f"💬 {title}"

            if st.button(
                label,
                key=f"chat_history_{chat_id}",
                use_container_width=True
            ):
                if chat_id != st.session_state.current_chat_id:
                    st.session_state.current_chat_id = chat_id
                    _load_chat_runtime_state(chat_id)
                    st.rerun()

        with menu_col:

            # The menu is deliberately only a ⋮ button.
            # Rename/Delete live inside it.
            # Empty chats never reach this list.
            with st.popover(
                "⋮",
                use_container_width=True
            ):

                st.markdown("**Chat options**")

                # -----------------------------
                # RENAME
                # -----------------------------
                rename_value = st.text_input(
                    "Chat name",
                    value=title,
                    key=f"rename_input_{chat_id}",
                    label_visibility="collapsed",
                    placeholder="Chat name"
                )

                if st.button(
                    "✏️ Rename",
                    key=f"rename_chat_{chat_id}",
                    use_container_width=True
                ):
                    new_title = rename_value.strip()

                    if not new_title:
                        st.warning("Chat name cannot be empty.")
                    else:
                        if len(new_title) > 60:
                            new_title = new_title[:60].rstrip()

                        update_chat_title(
                            chat_id,
                            new_title
                        )
                        st.rerun()

                st.markdown("---")

                # -----------------------------
                # DELETE
                # -----------------------------
                if st.button(
                    "🗑️ Delete",
                    key=f"delete_chat_{chat_id}",
                    type="secondary",
                    use_container_width=True
                ):

                    # Delete this chat's ChromaDB collection first.
                    delete_chat_collection(chat_id)

                    # Delete the SQLite chat, messages and
                    # uploaded-file metadata.
                    delete_chat(chat_id)

                    # Never leave the application without a current
                    # chat. If the deleted chat was active, create
                    # a clean New Chat immediately.
                    if chat_id == st.session_state.current_chat_id:

                        remaining_chats = list_chats()

                        if remaining_chats:
                            next_chat_id = remaining_chats[0]["chat_id"]
                        else:
                            next_chat_id = create_chat()

                        st.session_state.current_chat_id = next_chat_id
                        _reset_chat_runtime_state()

                    st.rerun()

    st.markdown("---")

    # -----------------------------------------------------
    # GEMINI MODE
    # -----------------------------------------------------

    st.markdown(
        """
        <div class="source-card">
            <strong>✨ Gemini Mode</strong><br>
            <small>Using Google Gemini for answer generation.</small>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    # -----------------------------------------------------
    # ASSISTANT MODE
    # -----------------------------------------------------

    if "assistant_mode" not in st.session_state:
        st.session_state.assistant_mode = "Document Q&A"

    st.markdown("### ⚡ What do you want to do?")
    st.caption("Choose a task and use its dedicated controls.")

    mode_col1, mode_col2 = st.columns(2, gap="small")

    def _select_mode(mode):
        st.session_state.assistant_mode = mode
        st.session_state.quiz_data = None
        st.session_state.quiz_submitted = False
        st.session_state.quiz_answers = {}
        st.session_state.flashcards_data = None
        st.session_state.flashcard_index = 0
        st.session_state.flashcard_flipped = False
        st.rerun()

    with mode_col1:
        if st.button(
            "💬 Ask Documents",
            key="mode_qa",
            type="primary" if st.session_state.assistant_mode == "Document Q&A" else "secondary",
            use_container_width=True,
            help="Ask questions grounded in your documents and YouTube transcripts."
        ):
            _select_mode("Document Q&A")

        if st.button(
            "🔄 Compare Documents",
            key="mode_compare",
            type="primary" if st.session_state.assistant_mode == "Compare Documents" else "secondary",
            use_container_width=True,
            help="Compare selected uploaded documents."
        ):
            _select_mode("Compare Documents")

        if st.button(
            "📑 Flashcards",
            key="mode_flashcards",
            type="primary" if st.session_state.assistant_mode == "Flashcards" else "secondary",
            use_container_width=True,
            help="Create study flashcards from indexed sources."
        ):
            _select_mode("Flashcards")

    with mode_col2:
        if st.button(
            "📄 Summarize Document",
            key="mode_summary",
            type="primary" if st.session_state.assistant_mode == "Summarize Document" else "secondary",
            use_container_width=True,
            help="Create one summary from all indexed sources."
        ):
            _select_mode("Summarize Document")

        if st.button(
            "🎯 Generate Quiz",
            key="mode_quiz",
            type="primary" if st.session_state.assistant_mode == "Generate Quiz" else "secondary",
            use_container_width=True,
            help="Generate an interactive quiz from indexed sources."
        ):
            _select_mode("Generate Quiz")

    assistant_mode = st.session_state.assistant_mode

    # -----------------------------------------------------
    # MODE-SPECIFIC CONTROLS
    # -----------------------------------------------------

    summarize_all_button = False
    summary_length = "Medium"
    compare_files = []
    compare_button = False

    if assistant_mode == "Summarize Document":
        st.markdown("### 📝 Summary Settings")
        summary_length = st.selectbox("Summary length", ["Short", "Medium", "Detailed"], index=1, key="summary_length")
        summarize_all_button = st.button("✨ Summarize All Documents", type="primary", use_container_width=True)

    elif assistant_mode == "Compare Documents":
        current_files_for_compare = get_chat_files(st.session_state.current_chat_id)
        compare_options = [record.get("file_name", "Unknown file") for record in current_files_for_compare]
        compare_files = st.multiselect("Select documents", compare_options, default=compare_options[:2] if len(compare_options) >= 2 else compare_options, key="compare_files")
        if len(compare_options) < 2:
            st.info("Upload at least two documents to compare them.")
        compare_button = st.button("🔄 Compare Selected Documents", type="primary", use_container_width=True, disabled=len(compare_files) < 2)

    elif assistant_mode == "Generate Quiz":
        st.markdown("### ⚙️ Quiz Settings")
        quiz_questions = st.slider("Number of Questions", 3, 15, 5, key="quiz_questions")
        quiz_difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"], key="quiz_difficulty")
        generate_quiz_button = st.button("🎯 Generate Quiz", type="primary", use_container_width=True)

    elif assistant_mode == "Flashcards":
        st.markdown("### 🃏 Flashcard Settings")
        flashcard_count = st.slider(
            "Number of Flashcards",
            5,
            20,
            10,
            key="flashcard_count"
        )
        flashcard_difficulty = st.selectbox(
            "Difficulty",
            ["Easy", "Medium", "Hard"],
            index=1,
            key="flashcard_difficulty"
        )
        generate_flashcards_button = st.button(
            "🃏 Generate Flashcards",
            type="primary",
            use_container_width=True
        )

    else:
        generate_quiz_button = False
        quiz_questions = 5
        quiz_difficulty = "Medium"
        generate_flashcards_button = False
        flashcard_count = 10
        flashcard_difficulty = "Medium"

    st.markdown("---")

    # -----------------------------------------------------
    # CURRENT CHAT DOCUMENTS
    # -----------------------------------------------------

    current_files = get_chat_files(
        st.session_state.current_chat_id
    )

    st.markdown(f"### 📚 Document Library ({len(current_files)})")

    if current_files:
        try:
            _, total_chunks, chunks_by_file = _collection_stats()
        except Exception:
            total_chunks, chunks_by_file = 0, {}

        for file_record in current_files:
            file_name = file_record.get("file_name", "Unknown file")
            file_size = file_record.get("file_size", 0) or 0
            size_text = f"{file_size / 1024:.1f} KB" if file_size else "Size unavailable"
            chunk_count = chunks_by_file.get(file_name, 0)
            with st.expander(f"📄 {file_name}"):
                st.caption(f"{size_text} • {chunk_count} chunks")

        st.markdown("#### 🧠 Document Insights")
        insight_col1, insight_col2 = st.columns(2)
        with insight_col1:
            st.metric("Documents", len(current_files))
        with insight_col2:
            st.metric("Chunks", total_chunks)
    else:
        st.info("📂 No documents or YouTube videos yet. Add a document or paste a YouTube link from the sidebar to get started.")

    # -----------------------------------------------------
    # INDEXED YOUTUBE VIDEOS
    # -----------------------------------------------------

    youtube_videos = {}

    try:
        collection_metadata = (
            collection.get(include=["metadatas"]).get("metadatas") or []
        )

        for metadata in collection_metadata:
            if not isinstance(metadata, dict):
                continue
            if metadata.get("source_type") != "youtube":
                continue

            video_id = metadata.get("video_id")
            if not video_id:
                continue

            if video_id not in youtube_videos:
                youtube_videos[video_id] = {
                    "file_name": metadata.get(
                        "file_name",
                        f"YouTube Video - {video_id}"
                    ),
                    "youtube_url": metadata.get(
                        "youtube_url"
                    ),
                    "segments": 0,
                }

            # Keep the URL if an older metadata row did not have it
            # but a newer row does.
            if (
                not youtube_videos[video_id].get("youtube_url")
                and metadata.get("youtube_url")
            ):
                youtube_videos[video_id]["youtube_url"] = (
                    metadata.get("youtube_url")
                )

            youtube_videos[video_id]["segments"] += 1

    except Exception:
        youtube_videos = {}

    if youtube_videos:
        st.markdown("#### 🎥 YouTube Videos")

        for video_id, video in youtube_videos.items():
            with st.expander(f"🎥 {video['file_name']}"):
                st.caption(
                    f"{video['segments']} transcript segments"
                )
                st.markdown(
                    f"[▶ Open YouTube video]"
                    f"(https://www.youtube.com/watch?v={quote(str(video_id))})"
                )

    # -----------------------------------------------------
    # YOUTUBE VIDEO
    # -----------------------------------------------------

    st.markdown("### 🎥 YouTube Video")
    st.caption("Paste a YouTube link to index its transcript into this chat.")

    youtube_url = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=...",
        key=f"youtube_url_{st.session_state.current_chat_id}",
        label_visibility="collapsed",
    )

    analyze_youtube_button = st.button(
        "🎥 Analyze YouTube Video",
        use_container_width=True,
        type="secondary",
        disabled=not youtube_url.strip(),
        key=f"analyze_youtube_{st.session_state.current_chat_id}",
    )

    if analyze_youtube_button:
        try:
            with st.spinner("🎙️ Extracting YouTube transcript..."):
                video_id = extract_video_id(youtube_url)
                transcript_segments = extract_youtube_transcript(youtube_url)

            before_count = collection.count()

            add_youtube_transcript(
    collection=collection,
    transcript_segments=transcript_segments,
    video_id=video_id,
    video_name=f"YouTube Video - {video_id}",
    youtube_url=youtube_url,
)

            after_count = collection.count()

            if after_count > before_count:
                st.success(
                    f"✅ YouTube video indexed successfully — "
                    f"{len(transcript_segments)} transcript segments stored."
                )
            else:
                st.info("ℹ️ This YouTube video is already indexed in this chat.")

            st.caption(
                "The transcript is now available to Ask, Summarize, "
                "Quiz, Flashcards, and retrieval."
            )

        except Exception as e:
            st.error(f"❌ Could not analyze this YouTube video: {e}")

    st.markdown("---")

    # -----------------------------------------------------
    # FILE UPLOADER
    # -----------------------------------------------------

    uploaded_files = st.file_uploader(
        "Upload Documents",
        type=[
            "pdf",
            "docx",
            "pptx",
            "txt",
            "csv",
            "xlsx",
            "png",
            "jpg",
            "jpeg"
        ],
        accept_multiple_files=True,
        key=(
            f"uploader_"
            f"{st.session_state.current_chat_id}"
        )
    )


# =========================================================
# DOCUMENT PROCESSING
# =========================================================

if uploaded_files:

    st.success(
        f"{len(uploaded_files)} file(s) uploaded successfully!"
    )

    for file in uploaded_files:

        # -------------------------------------------------
        # UNIQUE FILE KEY
        # -------------------------------------------------

        file_key = (
            f"{file.name}_"
            f"{file.size}"
        )

        # -------------------------------------------------
        # SAVE FILE
        # -------------------------------------------------

        saved_path = save_uploaded_file(file)

        st.write(
            f"📄 **{file.name}**"
        )

        st.write(
            f"📁 Saved to: `{saved_path}`"
        )

        st.write(
            f"📦 Size: "
            f"{round(file.size / 1024, 2)} KB"
        )

        # -------------------------------------------------
        # PROCESS ONLY ONCE PER SESSION
        # -------------------------------------------------

        if file_key not in st.session_state.processed_files:

            try:

                with st.spinner(
                    f"⚙️ Processing {file.name}..."
                ):

                    chunks = process_document(
                        file_path=saved_path,
                        file_name=file.name,
                        collection=collection
                    )

                st.session_state.processed_files.add(
                    file_key
                )

                add_file(
                    chat_id=st.session_state.current_chat_id,
                    file_key=file_key,
                    file_name=file.name,
                    file_path=saved_path,
                    file_size=file.size
                )

                # -------------------------------------------------
                # STORE SPREADSHEET DATAFRAMES
                # -------------------------------------------------
                # Keep the original pandas DataFrame(s) available
                # for Smart CSV/XLSX Data Analysis. This is an
                # additional path and does not replace ChromaDB.

                file_extension = (
                    file.name.rsplit(".", 1)[-1].lower()
                    if "." in file.name
                    else ""
                )

                try:

                    if file_extension == "csv":

                        dataframe = load_csv_dataframe(
                            saved_path
                        )

                        st.session_state.spreadsheet_data[
                            f"{file_key}::CSV"
                        ] = {
                            "file_name": file.name,
                            "sheet_name": None,
                            "dataframe": dataframe
                        }

                    elif file_extension in ["xlsx", "xls"]:

                        dataframes = load_xlsx_dataframes(
                            saved_path
                        )

                        for sheet_name, dataframe in dataframes.items():

                            st.session_state.spreadsheet_data[
                                f"{file_key}::{sheet_name}"
                            ] = {
                                "file_name": file.name,
                                "sheet_name": sheet_name,
                                "dataframe": dataframe
                            }

                except Exception as spreadsheet_error:

                    # Do not break normal document ingestion if the
                    # analysis DataFrame cannot be loaded.
                    st.warning(
                        f"⚠️ Smart data analysis could not load "
                        f"{file.name}: {spreadsheet_error}"
                    )

                # -------------------------------------------------
                # SUCCESS
                # -------------------------------------------------

                with st.expander(
                    "🔍 Document Processing Details"
                ):

                    st.success(
                        f"{file.name} processed successfully."
                    )

                    st.write(
                        f"**Total Chunks:** {len(chunks)}"
                    )

                    st.write("✅ Stored in ChromaDB")
                    st.write("🔎 Ready for semantic retrieval")
                    st.write("🤖 Ready for Q&A, summary, comparison, quiz, and flashcards")

            except Exception as e:

                st.error(
                    f"❌ Error processing "
                    f"{file.name}: {e}"
                )

        else:

            st.info(
                "✅ Already processed in this session."
            )

        st.markdown("---")


# =========================================================
# MAIN TITLE
# =========================================================

st.title("📄 Multi-Modal RAG Document Assistant")
st.markdown(
    '<div class="app-subtitle">Upload your documents, choose what you want to do, and get grounded AI results with sources.</div>',
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# YOUTUBE PLAYER — ONLY FOR CHATS WITH YOUTUBE VIDEOS
# ---------------------------------------------------------
# The existing YouTube URL input/indexing flow in the sidebar
# remains unchanged. This is only the Level-1 playback UI.
_render_youtube_player(youtube_videos)

st.markdown("---")


# =========================================================
# DISPLAY PREVIOUS CHAT
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.write(
            message["content"]
        )

        # -------------------------------------------------
        # SOURCES
        # -------------------------------------------------

        if (
            message["role"] == "assistant"
            and message.get("sources")
        ):
            _render_source_cards(message["sources"])



# =========================================================
# QUIZ HELPERS
# =========================================================

def _extract_json_object(value):
    """Safely convert the quiz service response into a Python dict."""
    if isinstance(value, dict):
        return value

    if not isinstance(value, str):
        return None

    cleaned = value.strip()

    # Remove markdown code fences if Gemini returned them.
    cleaned = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        cleaned,
        flags=re.IGNORECASE
    ).strip()

    # First try the complete response.
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    # Then try the first JSON object embedded in the response.
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)

    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _normalize_flashcard_data(raw_flashcards):
    """Validate the JSON structure required by the flashcard UI."""
    data = _extract_json_object(raw_flashcards)

    if not isinstance(data, dict):
        return None

    raw_cards = data.get("flashcards")

    if not isinstance(raw_cards, list):
        return None

    normalized_cards = []

    for item in raw_cards:
        if not isinstance(item, dict):
            return None

        front = item.get("front")
        back = item.get("back")

        if not isinstance(front, str) or not front.strip():
            return None

        if not isinstance(back, str) or not back.strip():
            return None

        card = {
            "front": front.strip(),
            "back": back.strip()
        }

        source = item.get("source")
        if isinstance(source, str) and source.strip():
            card["source"] = source.strip()

        normalized_cards.append(card)

    if not normalized_cards:
        return None

    data["flashcards"] = normalized_cards
    return data


def _normalize_quiz_data(raw_quiz):
    """
    Validate the structure needed by the interactive quiz.
    No answer is invented if the generator does not provide one.
    """
    data = _extract_json_object(raw_quiz)

    if not isinstance(data, dict):
        return None

    raw_questions = data.get("questions")

    if not isinstance(raw_questions, list):
        return None

    normalized_questions = []

    for item in raw_questions:
        if not isinstance(item, dict):
            return None

        question_text = item.get("question")
        options = item.get("options")
        correct_answer = item.get("correct_answer")

        if not isinstance(question_text, str):
            return None

        if not isinstance(options, list) or len(options) != 4:
            return None

        if not all(isinstance(option, str) for option in options):
            return None

        if not isinstance(correct_answer, int):
            return None

        if correct_answer < 0 or correct_answer >= len(options):
            return None

        normalized_item = {
            "question": question_text,
            "options": options,
            "correct_answer": correct_answer
        }

        explanation = item.get("explanation")
        if isinstance(explanation, str):
            normalized_item["explanation"] = explanation

        source = item.get("source")
        if isinstance(source, str):
            normalized_item["source"] = source

        normalized_questions.append(normalized_item)

    if not normalized_questions:
        return None

    data["questions"] = normalized_questions
    return data


# =========================================================
# SUMMARIZE ALL DOCUMENTS BUTTON
# =========================================================

if assistant_mode == "Summarize Document" and summarize_all_button:

    # -----------------------------------------------------
    # CHECK DOCUMENTS
    # -----------------------------------------------------

    results = collection.get(
        include=["documents", "metadatas"]
    )

    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []

    if not documents:
        st.warning(
            "Please upload at least one document before "
            "summarizing."
        )
        st.stop()

    # -----------------------------------------------------
    # BUILD CONTEXT FROM ALL UPLOADED DOCUMENTS
    # -----------------------------------------------------

    summary_parts = []

    for index, document in enumerate(documents):

        if not document:
            continue

        metadata = (
            metadatas[index]
            if index < len(metadatas)
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

        summary_parts.append(
            f"[Document: {file_name} | Page: {page}]\n"
            f"{document}"
        )

    all_documents_context = "\n\n".join(
        summary_parts
    )

    if not all_documents_context.strip():
        st.warning(
            "The uploaded documents do not contain readable "
            "text to summarize."
        )
        st.stop()

    # -----------------------------------------------------
    # GENERATE COMBINED SUMMARY
    # -----------------------------------------------------

    with st.spinner(
        "📝 Reading all documents and generating a summary..."
    ):

        try:

            summary_answer = generate_summary(
                context=all_documents_context,
                question=(
                    f"Summarize ALL of the uploaded documents together. "
                    f"Summary length: {summary_length}. "
                    "Give a clear, well-structured combined summary covering "
                    "the most important information from every document. "
                    "Do not focus on only one document. Use headings and bullet "
                    "points where helpful. Only use information supported by the documents."
                )
            )

        except Exception as e:

            st.error(
                "Sorry, I could not summarize the documents "
                "right now."
            )

            with st.expander("Technical details"):
                st.code(str(e))

            st.stop()

    # -----------------------------------------------------
    # GROUP ALL SOURCES
    # -----------------------------------------------------

    grouped_sources = {}

    for metadata in metadatas:

        file_name = metadata.get(
            "file_name",
            "Unknown file"
        )

        page = metadata.get(
            "page",
            metadata.get(
                "page_number"
            )
        )

        if file_name not in grouped_sources:
            grouped_sources[file_name] = set()

        if page is not None:
            grouped_sources[file_name].add(
                str(page)
            )

    sources = []

    for file_name, pages in grouped_sources.items():

        sources.append(
            {
                "file_name": file_name,
                "pages": sorted(
                    pages,
                    key=lambda value: (
                        int(value)
                        if str(value).isdigit()
                        else str(value)
                    )
                )
            }
        )

    # Save the generated summary into the current chat so
    # it remains visible after Streamlit reruns.
    _append_message(
        {
            "role": "assistant",
            "content": summary_answer,
            "sources": sources
        }
    )

    st.rerun()


# =========================================================
# COMPARE SELECTED DOCUMENTS
# =========================================================

if assistant_mode == "Compare Documents" and compare_button:

    results = collection.get(include=["documents", "metadatas"])
    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []

    selected_set = set(compare_files)
    selected_parts = []
    selected_metadatas = []

    for index, document in enumerate(documents):
        metadata = metadatas[index] if index < len(metadatas) else {}
        if not isinstance(metadata, dict):
            metadata = {}
        if metadata.get("file_name") in selected_set and document:
            selected_parts.append(
                f"SOURCE {len(selected_parts) + 1}\n"
                f"File: {metadata.get('file_name', 'Unknown file')}\n"
                f"Location: {metadata.get('page', metadata.get('page_number', 'Unknown'))}\n"
                f"Content:\n{document}"
            )
            selected_metadatas.append(metadata)

    if len(selected_parts) < 2:
        st.warning("I need content from at least two selected documents to compare them.")
    else:
        comparison_context = "\n\n".join(selected_parts)
        comparison_request = (
            "Compare the selected documents. Start with a clear Markdown table "
            "showing the main topics and how the documents differ. Then provide "
            "a short Key Similarities section and a Key Differences section. "
            "Use only information supported by the supplied context. If a topic "
            "is not present in a document, say 'Not specified'."
        )

        with st.spinner("🔄 Comparing the selected documents..."):
            try:
                comparison_answer = generate_comparison(
                    context=comparison_context,
                    question=comparison_request
                )
            except Exception as e:
                st.error("I couldn't compare those documents right now.")
                with st.expander("Technical details"):
                    st.code(str(e))
                comparison_answer = None

        if comparison_answer:
            sources = _build_sources(selected_metadatas)
            _append_message({"role": "assistant", "content": comparison_answer, "sources": sources})
            with st.chat_message("assistant"):
                st.markdown("### 🔄 Comparison")
                st.markdown(comparison_answer)
                _render_source_cards(sources)
                _render_retrieved_context(selected_parts, selected_metadatas, "🔍 View Comparison Context")

    st.stop()


# =========================================================
# GENERATE FLASHCARDS BUTTON
# =========================================================

if assistant_mode == "Flashcards" and generate_flashcards_button:

    st.session_state.flashcards_data = None
    st.session_state.flashcard_index = 0
    st.session_state.flashcard_flipped = False

    results = collection.get(
        include=["documents", "metadatas"]
    )

    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []

    if not documents:
        st.warning(
            "Please upload a document before generating flashcards."
        )
    else:
        context_parts = []

        for i, document in enumerate(documents):
            if not document:
                continue

            metadata = (
                metadatas[i]
                if i < len(metadatas)
                else {}
            )

            if not isinstance(metadata, dict):
                metadata = {}

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
SOURCE {i + 1}
File: {file_name}
Page: {page}

Content:
{document}
"""
            )

        flashcard_context = "\n".join(context_parts)

        if not flashcard_context.strip():
            st.warning(
                "I could not find readable document content "
                "to create flashcards."
            )
        else:
            flashcard_request = f"""
Create exactly {flashcard_count} study flashcards from the
supplied document context.

Difficulty: {flashcard_difficulty}

Return ONLY valid JSON. Do not use Markdown fences.

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
- Create exactly {flashcard_count} flashcards.
- Front should test one clear concept.
- Back should provide the answer or explanation.
- Keep cards concise and useful for revision.
- Cover different important concepts instead of repeating the same fact.
- Every card must be supported by the supplied documents.
- Do not invent information.
- Include the source file and page when available.

Document context:

{flashcard_context}
"""

            with st.spinner(
                "🧠 Reading your documents and creating flashcards..."
            ):
                try:
                    raw_flashcards = generate_response(
                        context=flashcard_context,
                        question=flashcard_request
                    )

                    flashcard_data = _normalize_flashcard_data(
                        raw_flashcards
                    )

                    if flashcard_data is None:
                        st.error(
                            "The flashcard generator returned an "
                            "invalid format. Please try again."
                        )
                    else:
                        cards = flashcard_data.get(
                            "flashcards",
                            []
                        )

                        flashcard_data["flashcards"] = cards[
                            :flashcard_count
                        ]

                        st.session_state.flashcards_data = (
                            flashcard_data
                        )
                        st.session_state.flashcard_index = 0
                        st.session_state.flashcard_flipped = False

                except Exception as e:
                    st.error(
                        "Sorry, I could not generate flashcards right now."
                    )
                    with st.expander("Technical details"):
                        st.code(str(e))


# =========================================================
# FLASHCARD VIEWER
# =========================================================

if (
    assistant_mode == "Flashcards"
    and st.session_state.flashcards_data
):

    cards = st.session_state.flashcards_data.get(
        "flashcards",
        []
    )

    if cards:
        index = min(
            max(st.session_state.flashcard_index, 0),
            len(cards) - 1
        )

        card = cards[index]

        st.markdown("---")
        st.markdown("## 🃏 Flashcards")
        st.caption(
            f"Card {index + 1} of {len(cards)} • "
            f"Click **Flip Card** to reveal the answer."
        )

        card_text = (
            card["back"]
            if st.session_state.flashcard_flipped
            else card["front"]
        )

        card_label = (
            "ANSWER"
            if st.session_state.flashcard_flipped
            else "QUESTION"
        )

        st.markdown(
            f"""
            <div style="
                border:1px solid rgba(128,128,128,.25);
                border-radius:18px;
                padding:32px 28px;
                min-height:220px;
                display:flex;
                flex-direction:column;
                justify-content:center;
                text-align:center;
                margin:12px 0 18px 0;
            ">
                <div style="
                    font-size:0.82rem;
                    font-weight:700;
                    letter-spacing:0.08em;
                    opacity:0.65;
                    margin-bottom:18px;
                ">{card_label}</div>
                <div style="
                    font-size:1.35rem;
                    line-height:1.55;
                    font-weight:600;
                ">{card_text}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if card.get("source"):
            st.caption(f"📚 Source: {card['source']}")

        flip_col, prev_col, next_col = st.columns(
            [1, 1, 1],
            gap="small"
        )

        with flip_col:
            if st.button(
                "🔄 Flip Card",
                use_container_width=True
            ):
                st.session_state.flashcard_flipped = (
                    not st.session_state.flashcard_flipped
                )
                st.rerun()

        with prev_col:
            if st.button(
                "← Previous",
                use_container_width=True,
                disabled=index == 0
            ):
                st.session_state.flashcard_index = index - 1
                st.session_state.flashcard_flipped = False
                st.rerun()

        with next_col:
            if st.button(
                "Next →",
                use_container_width=True,
                disabled=index >= len(cards) - 1
            ):
                st.session_state.flashcard_index = index + 1
                st.session_state.flashcard_flipped = False
                st.rerun()

        if index == len(cards) - 1:
            st.success(
                "🎉 You've reached the end of the flashcard deck."
            )

            if st.button(
                "🔄 Start Again",
                use_container_width=True
            ):
                st.session_state.flashcard_index = 0
                st.session_state.flashcard_flipped = False
                st.rerun()


# =========================================================
# GENERATE QUIZ BUTTON
# =========================================================

if assistant_mode == "Generate Quiz" and generate_quiz_button:

    # A new quiz starts a fresh attempt.
    st.session_state.quiz_data = None
    st.session_state.quiz_submitted = False
    st.session_state.quiz_answers = {}

    # -----------------------------------------------------
    # CHECK CHROMA
    # -----------------------------------------------------

    results = collection.get()

    if not results.get("ids"):
        st.warning(
            "Please upload a document before generating a quiz."
        )
    else:

        # -------------------------------------------------
        # RETRIEVE DOCUMENT CONTENT
        # -------------------------------------------------

        with st.spinner(
            "🔎 Retrieving document content..."
        ):

            retrieval_result = retrieve_chunks(
                "Generate a quiz from the uploaded documents",
                collection,
                top_k=10
            )

        documents = retrieval_result.get(
            "documents",
            []
        )

        metadatas = retrieval_result.get(
            "metadatas",
            []
        )

        if not documents:
            st.warning(
                "I could not retrieve enough document content "
                "to generate a quiz."
            )
        else:

            # -------------------------------------------------
            # BUILD QUIZ CONTEXT
            # -------------------------------------------------

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

                if not isinstance(metadata, dict):
                    metadata = {}

                file_name = metadata.get(
                    "file_name",
                    "Unknown file"
                )

                page = metadata.get(
                    "page",
                    "Unknown"
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

            # -------------------------------------------------
            # STRICT QUIZ REQUEST
            # -------------------------------------------------

            quiz_request = f"""
Generate exactly {quiz_questions} multiple-choice questions
from the supplied document context.

Difficulty: {quiz_difficulty}

Return ONLY valid JSON.
Do not use Markdown.
Do not include ```json.
Do not include any text before or after the JSON.

Use exactly this structure:

{{
  "questions": [
    {{
      "question": "Question text",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "correct_answer": 0,
      "explanation": "Short explanation based only on the document",
      "source": "Source/file/page supporting the answer"
    }}
  ]
}}

Rules:
- "correct_answer" must be the zero-based option index: 0, 1, 2, or 3.
- Every question must have exactly four options.
- The correct answer must be supported by the document context.
- Do not reveal answers outside the JSON field.
- Do not invent information that is not present in the document.

Document context:

{quiz_context}
"""

            # -------------------------------------------------
            # GENERATE QUIZ
            # -------------------------------------------------

            with st.spinner(
                "🧠 Generating quiz..."
            ):

                try:

                    raw_quiz = generate_quiz(
    context=quiz_context,
    num_questions=quiz_questions,
    difficulty=quiz_difficulty
)

                    quiz_data = _normalize_quiz_data(
                        raw_quiz
                    )

                    if quiz_data is None:
                        st.error(
                            "The quiz generator returned an "
                            "invalid quiz format. Please try "
                            "Generate Quiz again."
                        )
                    else:
                        st.session_state.quiz_data = quiz_data
                        st.session_state.quiz_submitted = False
                        st.session_state.quiz_answers = {}

                except Exception as e:

                    st.error(
                        "Sorry, I could not generate the quiz "
                        "right now."
                    )

                    st.caption(
                        f"Error: {e}"
                    )


# =========================================================
# INTERACTIVE QUIZ
# =========================================================

if (
    assistant_mode == "Generate Quiz"
    and st.session_state.quiz_data
):

    quiz_data = st.session_state.quiz_data

    questions = quiz_data.get(
        "questions",
        []
    )

    st.markdown("---")

    st.markdown(
        "## 🧠 Quiz"
    )

    st.caption(
        f"{len(questions)} questions • "
        f"{quiz_difficulty} difficulty"
    )

    # -----------------------------------------------------
    # QUESTIONS
    # -----------------------------------------------------

    for i, q in enumerate(
        questions
    ):

        st.markdown(
            f"### Question {i + 1}"
        )

        st.write(
            q["question"]
        )

        answer = st.radio(
            "Choose your answer:",
            q["options"],
            key=f"quiz_question_{i}",
            index=None
        )

        st.session_state.quiz_answers[i] = answer

        # -------------------------------------------------
        # ANSWER REVIEW
        # -------------------------------------------------

        if st.session_state.quiz_submitted:

            correct_index = q["correct_answer"]
            correct_answer = q["options"][correct_index]

            if answer == correct_answer:

                st.success(
                    f"✅ Correct! {correct_answer}"
                )

            elif answer is None:

                st.error(
                    f"❌ Not answered. "
                    f"Correct answer: {correct_answer}"
                )

            else:

                st.error(
                    f"❌ Your answer: {answer}"
                )

                st.success(
                    f"✅ Correct answer: {correct_answer}"
                )

            explanation = q.get("explanation")

            if explanation:
                st.info(
                    f"💡 {explanation}"
                )

            source = q.get("source")

            if source:
                st.caption(
                    f"📚 Source: {source}"
                )

        st.markdown("---")

    # -----------------------------------------------------
    # SUBMIT QUIZ
    # -----------------------------------------------------

    if not st.session_state.quiz_submitted:

        submit_quiz = st.button(
            "✅ Submit Quiz",
            type="primary",
            use_container_width=True
        )

        if submit_quiz:

            score = 0

            for i, q in enumerate(
                questions
            ):

                selected_answer = (
                    st.session_state.quiz_answers.get(i)
                )

                correct_index = q["correct_answer"]
                correct_answer = q["options"][correct_index]

                if selected_answer == correct_answer:
                    score += 1

            st.session_state.quiz_submitted = True

            st.rerun()

    else:

        score = 0

        for i, q in enumerate(
            questions
        ):

            selected_answer = (
                st.session_state.quiz_answers.get(i)
            )

            correct_index = q["correct_answer"]
            correct_answer = q["options"][correct_index]

            if selected_answer == correct_answer:
                score += 1

        percentage = (
            (score / len(questions)) * 100
            if questions
            else 0
        )

        if percentage >= 80:

            st.success(
                f"🎉 Excellent!\n\n"
                f"You scored {score}/{len(questions)} "
                f"({percentage:.0f}%)"
            )

        elif percentage >= 50:

            st.info(
                f"👍 Good job!\n\n"
                f"You scored {score}/{len(questions)} "
                f"({percentage:.0f}%)"
            )

        else:

            st.warning(
                f"📚 Keep practicing!\n\n"
                f"You scored {score}/{len(questions)} "
                f"({percentage:.0f}%)"
            )

        st.markdown("## 📋 Answer Review")

        metric_col1, metric_col2, metric_col3 = st.columns(3)
        with metric_col1:
            st.metric("Score", f"{score}/{len(questions)}")
        with metric_col2:
            st.metric("Percentage", f"{percentage:.0f}%")
        with metric_col3:
            st.metric("Correct", score)

        if st.button("🔄 Retake Quiz", use_container_width=True):
            st.session_state.quiz_data = None
            st.session_state.quiz_submitted = False
            st.session_state.quiz_answers = {}
            st.rerun()


# =========================================================
# SMART DATA ANALYSIS HELPERS
# =========================================================

def _looks_like_data_analysis_question(question):
    """
    Detect questions that are likely asking for a numerical,
    tabular, sorting, grouping, filtering, or aggregation
    operation.

    This is only a routing hint. The actual calculation is
    performed by pandas inside data_analysis_service.py.
    """

    normalized_question = question.lower().strip()

    analysis_phrases = [
        "average",
        "mean",
        "avg",
        "minimum",
        "maximum",
        "min",
        "max",
        "lowest",
        "highest",
        "smallest",
        "largest",
        "top ",
        "bottom ",
        "how many",
        "count",
        "number of",
        "sum",
        "total",
        "revenue",
        "percentage",
        "percent",
        "sort",
        "sorted",
        "order by",
        "group by",
        "group ",
        "department",
        "salary",
        "records"
    ]

    return any(
        phrase in normalized_question
        for phrase in analysis_phrases
    )


def _find_spreadsheet_analysis(question):
    """
    Try the loaded CSV/XLSX DataFrames and return the first
    successful pandas analysis result.

    If the question explicitly mentions a file name or sheet,
    prefer that spreadsheet/sheet.
    """

    if not st.session_state.spreadsheet_data:
        return None

    normalized_question = question.lower()

    candidates = list(
        st.session_state.spreadsheet_data.values()
    )

    # -----------------------------------------------------
    # Prefer an explicitly mentioned file or sheet.
    # -----------------------------------------------------

    explicit_candidates = []

    for item in candidates:

        file_name = str(
            item.get("file_name", "")
        ).lower()

        sheet_name = str(
            item.get("sheet_name", "")
        ).lower()

        if (
            file_name
            and file_name in normalized_question
        ) or (
            sheet_name
            and sheet_name in normalized_question
        ):
            explicit_candidates.append(item)

    if explicit_candidates:
        candidates = explicit_candidates

    # -----------------------------------------------------
    # Run the controlled pandas analysis.
    # -----------------------------------------------------

    for item in candidates:

        dataframe = item.get("dataframe")

        result = analyze_dataframe(
            dataframe=dataframe,
            question=question,
            file_name=item.get("file_name"),
            sheet_name=item.get("sheet_name")
        )

        if result.get("success"):
            return result

    return None


# =========================================================
# EMPTY STATE
# =========================================================

if assistant_mode == "Document Q&A":
    try:
        _, total_chunks, _ = _collection_stats()
    except Exception:
        total_chunks = 0
    if total_chunks == 0:
        st.info(
            "📂 No documents are ready yet. Upload a document from the sidebar, "
            "then ask a question here."
        )


# =========================================================
# CHAT INPUT
# =========================================================

# =========================================================
# CHAT INPUT
# =========================================================

if assistant_mode == "Document Q&A":
    question = st.chat_input(
        "Ask anything about your documents..."
    )
else:
    question = None


# =========================================================
# QUESTION PROCESSING
# =========================================================

if question and assistant_mode == "Document Q&A":

    # -----------------------------------------------------
    # PREVIOUS CONVERSATION
    # -----------------------------------------------------

    previous_history = list(
        st.session_state.messages
    )

    # -----------------------------------------------------
    # SAVE USER MESSAGE
    # -----------------------------------------------------

    _append_message(
        {
            "role": "user",
            "content": question
        }
    )

    # Give a new chat a useful title after its first question.
    current_chat = get_chat(
        st.session_state.current_chat_id
    )

    if current_chat and current_chat.get("title") == "New Chat":
        chat_title = question.strip().replace("\n", " ")
        if len(chat_title) > 45:
            chat_title = chat_title[:45].rstrip() + "..."
        update_chat_title(
            st.session_state.current_chat_id,
            chat_title or "New Chat"
        )

    with st.chat_message("user"):

        st.write(question)

    # =====================================================
    # SMART CSV/XLSX DATA ANALYSIS
    # =====================================================
    # Only Document Q&A uses this analytical route.
    # Compare, Summarize, and Quiz keep their existing
    # behavior unchanged.

    if (
        assistant_mode == "Document Q&A"
        and st.session_state.spreadsheet_data
        and _looks_like_data_analysis_question(question)
    ):

        with st.spinner(
            "📊 Analyzing spreadsheet data..."
        ):

            try:

                analysis_result = _find_spreadsheet_analysis(
                    question
                )

                if analysis_result:

                    analysis_context = build_analysis_context(
                        analysis_result=analysis_result,
                        question=question
                    )

                    with st.spinner(
                        "✨ Explaining the calculated result..."
                    ):

                        answer = generate_response(
                            context=analysis_context,
                            question=question
                        )

                    source_file = analysis_result.get(
                        "file_name",
                        "Unknown spreadsheet"
                    )

                    sheet_name = analysis_result.get(
                        "sheet_name"
                    )

                    if sheet_name:
                        source_location = (
                            f"Sheet: {sheet_name}"
                        )
                    else:
                        source_location = "Spreadsheet data"

                    sources = [
                        {
                            "file_name": source_file,
                            "pages": {source_location}
                        }
                    ]

                    _append_message(
                        {
                            "role": "assistant",
                            "content": answer,
                            "sources": sources
                        }
                    )

                    with st.chat_message("assistant"):

                        st.markdown(
                            "### 📊 Data Analysis"
                        )

                        st.write(answer)

                        st.markdown(
                            "### 📚 Sources"
                        )

                        st.markdown(
                            f"📊 **{source_file}**  \n"
                            f"Source: **{source_location}**"
                        )

                        with st.expander(
                            "🔍 View Pandas Calculation"
                        ):

                            st.write(
                                f"**Operation:** "
                                f"{analysis_result.get('operation')}"
                            )

                            st.write(
                                f"**Calculated Result:** "
                                f"{analysis_result.get('result')}"
                            )

                            st.caption(
                                analysis_result.get(
                                    "description",
                                    ""
                                )
                            )

                    # The analytical question has been fully
                    # handled. Do not send it through ChromaDB.
                    st.stop()

            except Exception as analysis_error:

                # If analysis fails, fall back to the existing
                # RAG pipeline rather than breaking document Q&A.
                st.warning(
                    "⚠️ Smart data analysis could not process "
                    f"this question. Falling back to normal RAG. "
                    f"Details: {analysis_error}"
                )

    # -----------------------------------------------------
    # CHECK CHROMA
    # -----------------------------------------------------

    results = collection.get()

    if not results["ids"]:

        answer = (
            "Please upload a document before "
            "asking a question."
        )

        sources = []

        documents = []

        metadatas = []

    else:

        # -------------------------------------------------
        # NORMAL RETRIEVAL FOR OTHER MODES
        # -------------------------------------------------

        # -------------------------------------------------
        # RETRIEVAL
        # -------------------------------------------------

        with st.spinner(
            "🔎 Searching your documents..."
        ):

            retrieval_result = retrieve_chunks(
                question,
                collection,
                top_k=5
            )

        documents = retrieval_result.get(
            "documents",
            []
        )

        metadatas = retrieval_result.get(
            "metadatas",
            []
        )

        # -------------------------------------------------
        # BUILD RETRIEVED CONTEXT
        # -------------------------------------------------

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

            if not isinstance(metadata, dict):
                metadata = {}

            file_name = metadata.get(
                "file_name",
                "Unknown file"
            )

            source_type = metadata.get(
                "source_type",
                "document"
            )

            if source_type == "youtube":

                start_time = metadata.get(
                    "start_time",
                    0
                )

                video_id = metadata.get(
                    "video_id",
                    ""
                )

                youtube_url = metadata.get(
                    "youtube_url",
                    ""
                )

                timestamp = _format_timestamp(
                    start_time
                )

                context_parts.append(
                    f"""
SOURCE {i}

Source Type: YouTube

Video: {file_name}

Video ID: {video_id}

YouTube URL: {youtube_url}

Timestamp: [{timestamp}]

Timestamp Seconds: {start_time}

Transcript:
{document}
"""
                )

            else:

                page = metadata.get(
                    "page",
                    "Unknown"
                )

                context_parts.append(
                    f"""
SOURCE {i}

Source Type: Document

File: {file_name}

Location: {page}

Content:
{document}
"""
                )

        retrieved_context = "\n".join(
            context_parts
        )

        # -------------------------------------------------
        # BUILD CONVERSATION CONTEXT
        # -------------------------------------------------

        conversation_parts = []

        for message in previous_history:

            role = message.get(
                "role",
                ""
            )

            content = message.get(
                "content",
                ""
            )

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

        # -------------------------------------------------
        # FINAL RAG CONTEXT
        # -------------------------------------------------

        final_context = f"""
PREVIOUS CONVERSATION:

{conversation_context}


RETRIEVED DOCUMENT CONTEXT:

{retrieved_context}
"""

        # =================================================
        # COMPARE DOCUMENTS MODE
        # =================================================

        if assistant_mode == "Compare Documents":

            with st.spinner(
                "⚖️ Comparing documents..."
            ):

                try:

                    answer = generate_comparison(
                        context=final_context,
                        question=question
                    )

                except Exception as e:

                    answer = (
                        "Sorry, I could not compare "
                        "the documents right now.\n\n"
                        f"Error: {e}"
                    )

            # -------------------------------------------------
            # GROUP SOURCES
            # -------------------------------------------------

            grouped_sources = {}

            for metadata in metadatas:

                file_name = metadata.get(
                    "file_name",
                    "Unknown file"
                )

                page = metadata.get(
                    "page"
                )

                if file_name not in grouped_sources:

                    grouped_sources[file_name] = set()

                if page is not None:

                    grouped_sources[
                        file_name
                    ].add(page)

            sources = []

            for file_name, pages in (
                grouped_sources.items()
            ):

                sources.append(
                    {
                        "file_name": file_name,
                        "pages": pages
                    }
                )

            # -------------------------------------------------
            # SAVE COMPARISON RESPONSE
            # -------------------------------------------------

            _append_message(
                {
                    "role": "assistant",
                    "content": answer,
                    "sources": sources
                }
            )

            # -------------------------------------------------
            # DISPLAY COMPARISON
            # -------------------------------------------------

            with st.chat_message("assistant"):

                st.markdown(
                    "### ⚖️ Comparison"
                )

                st.write(answer)

                if sources:

                    st.markdown(
                        "### 📚 Sources"
                    )

                    for source in sources:

                        file_name = source[
                            "file_name"
                        ]

                        pages = source[
                            "pages"
                        ]

                        page_text = ", ".join(
                            map(
                                str,
                                sorted(
                                    pages,
                                    key=str
                                )
                            )
                        )

                        st.markdown(
                            f"📄 **{file_name}**  \n"
                            f"Pages / Locations: "
                            f"**{page_text}**"
                        )

            # -------------------------------------------------
            # DEBUG CONTEXT
            # -------------------------------------------------

            if documents:

                with st.expander(
                    "🔍 Debug: View Retrieved Context"
                ):

                    st.info(
                        f"Retrieved "
                        f"{len(documents)} "
                        f"relevant chunks."
                    )

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
                            "Unknown"
                        )

                        st.markdown(
                            f"**Chunk {i}** — "
                            f"📄 {file_name} | "
                            f"Location {page}"
                        )

                        st.write(
                            document
                        )

                        st.markdown("---")

            # IMPORTANT:
            # Stop comparison mode from reaching
            # normal Q&A generation.

            st.stop()


        # =================================================
        # SUMMARIZE DOCUMENT MODE
        # =================================================

        if assistant_mode == "Summarize Document":

            with st.spinner(
                "📝 Generating document summary..."
            ):

                try:

                    answer = generate_summary(
                        context=final_context,
                        question=question
                    )

                except Exception as e:

                    answer = (
                        "Sorry, I could not summarize "
                        "the document right now.\n\n"
                        f"Error: {e}"
                    )

            # -------------------------------------------------
            # GROUP SOURCES
            # -------------------------------------------------

            grouped_sources = {}

            for metadata in metadatas:

                file_name = metadata.get(
                    "file_name",
                    "Unknown file"
                )

                page = metadata.get(
                    "page"
                )

                if file_name not in grouped_sources:

                    grouped_sources[file_name] = set()

                if page is not None:

                    grouped_sources[
                        file_name
                    ].add(page)

            sources = []

            for file_name, pages in (
                grouped_sources.items()
            ):

                sources.append(
                    {
                        "file_name": file_name,
                        "pages": pages
                    }
                )

            # -------------------------------------------------
            # SAVE SUMMARY RESPONSE
            # -------------------------------------------------

            _append_message(
                {
                    "role": "assistant",
                    "content": answer,
                    "sources": sources
                }
            )

            # -------------------------------------------------
            # DISPLAY SUMMARY
            # -------------------------------------------------

            with st.chat_message("assistant"):

                st.markdown(
                    "### 📝 Summary"
                )

                st.markdown(answer)

                if sources:

                    st.markdown(
                        "### 📚 Sources"
                    )

                    for source in sources:

                        file_name = source[
                            "file_name"
                        ]

                        pages = source[
                            "pages"
                        ]

                        page_text = ", ".join(
                            map(
                                str,
                                sorted(
                                    pages,
                                    key=str
                                )
                            )
                        )

                        st.markdown(
                            f"📄 **{file_name}**  \n"
                            f"Pages / Locations: "
                            f"**{page_text}**"
                        )

            # -------------------------------------------------
            # DEBUG CONTEXT
            # -------------------------------------------------

            if documents:

                with st.expander(
                    "🔍 Debug: View Retrieved Context"
                ):

                    st.info(
                        f"Retrieved "
                        f"{len(documents)} "
                        f"relevant chunks."
                    )

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
                            "Unknown"
                        )

                        st.markdown(
                            f"**Chunk {i}** — "
                            f"📄 {file_name} | "
                            f"Location {page}"
                        )

                        st.write(
                            document
                        )

                        st.markdown("---")

            # IMPORTANT:
            # Stop summary mode from reaching
            # normal Q&A generation.

            st.stop()


        # =================================================
        # NORMAL DOCUMENT Q&A / LEVEL-2 YOUTUBE Q&A
        # =================================================

        # -------------------------------------------------
        # FIND WHETHER THIS CHAT CONTAINS A YOUTUBE VIDEO
        # -------------------------------------------------

        youtube_url_for_analysis = (
            _get_youtube_url_for_question(
                retrieved_metadatas=metadatas,
                youtube_videos=youtube_videos
            )
        )

        # -------------------------------------------------
        # LEVEL 2 — TRUE MULTIMODAL YOUTUBE ANALYSIS
        # -------------------------------------------------

        if youtube_url_for_analysis:

            with st.spinner(
                "🎬 Gemini is watching the YouTube video "
                "and analyzing audio + visuals..."
            ):

                try:

                    answer = generate_youtube_multimodal_response(
                        video_url=youtube_url_for_analysis,
                        context=final_context,
                        question=question
                    )

                except Exception as multimodal_error:

                    # -------------------------------------------------
                    # SAFE FALLBACK
                    # -------------------------------------------------
                    # If Gemini's multimodal video request fails,
                    # preserve the existing transcript RAG behavior.
                    st.warning(
                        "⚠️ Multimodal video analysis failed. "
                        "Falling back to transcript RAG."
                    )

                    with st.expander(
                        "Technical details"
                    ):
                        st.code(
                            str(multimodal_error)
                        )

                    with st.spinner(
                        "✨ Generating transcript-based answer..."
                    ):

                        try:

                            answer = generate_response(
                                context=final_context,
                                question=question
                            )

                        except Exception as e:

                            answer = (
                                "Sorry, I could not generate "
                                "an answer right now.\n\n"
                                f"Error: {e}"
                            )

        # -------------------------------------------------
        # NORMAL DOCUMENT RAG
        # -------------------------------------------------

        else:

            with st.spinner(
                "✨ Generating answer..."
            ):

                try:

                    answer = generate_response(
                        context=final_context,
                        question=question
                    )

                except Exception as e:

                    answer = (
                        "Sorry, I could not generate "
                        "an answer right now.\n\n"
                        f"Error: {e}"
                    )

        # -------------------------------------------------
        # GROUP SOURCES
        # -------------------------------------------------

        sources = _build_sources(metadatas)

    # =====================================================
    # SAVE ASSISTANT MESSAGE
    # =====================================================

    _append_message(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources
        }
    )

    # =====================================================
    # DISPLAY NORMAL ANSWER
    # =====================================================

    with st.chat_message(
        "assistant"
    ):

        st.markdown(
            "### 🤖 Answer"
        )

        st.write(
            answer
        )

        # -------------------------------------------------
        # SOURCES
        # -------------------------------------------------

        _render_source_cards(sources)
        _render_retrieved_context(documents, metadatas, "🔍 View Retrieved Context")

        # -------------------------------------------------
        # DEBUG CONTEXT
        # -------------------------------------------------

        if documents:

            with st.expander(
                "🔍 Debug: View Retrieved Context"
            ):

                st.info(
                    f"Retrieved "
                    f"{len(documents)} "
                    f"relevant chunks."
                )

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
                        "Unknown"
                    )

                    st.markdown(
                        f"**Chunk {i}** — "
                        f"📄 {file_name} | "
                        f"Location {page}"
                    )

                    st.write(
                        document
                    )

                    st.markdown("---")
                    