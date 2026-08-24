import os
import json
import sqlite3
import uuid

from datetime import datetime


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

DB_DIR = "data"

DB_PATH = os.path.join(
    DB_DIR,
    "chats.db"
)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def _get_connection():
    """
    Create and return a SQLite database connection.
    """

    os.makedirs(
        DB_DIR,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# INITIALIZE DATABASE
# =========================================================

def initialize_chat_database():
    """
    Create the chat database and required tables.
    """

    connection = _get_connection()

    cursor = connection.cursor()

    cursor.execute(
        "PRAGMA foreign_keys = ON"
    )

    # -----------------------------------------------------
    # CHATS
    # -----------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (
            chat_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    # -----------------------------------------------------
    # MESSAGES
    # -----------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            message_data TEXT,
            created_at TEXT NOT NULL,

            FOREIGN KEY (chat_id)
            REFERENCES chats(chat_id)
            ON DELETE CASCADE
        )
        """
    )

    # -----------------------------------------------------
    # CHAT FILES
    # -----------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            file_key TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,

            UNIQUE(chat_id, file_key),

            FOREIGN KEY (chat_id)
            REFERENCES chats(chat_id)
            ON DELETE CASCADE
        )
        """
    )

    connection.commit()

    connection.close()


# =========================================================
# CREATE CHAT
# =========================================================

def create_chat(
    title="New Chat"
):
    """
    Create a new chat and return its ID.
    """

    initialize_chat_database()

    chat_id = str(
        uuid.uuid4()
    )

    now = datetime.now().isoformat()

    clean_title = str(
        title
    ).strip()

    if not clean_title:
        clean_title = "New Chat"

    connection = _get_connection()

    connection.execute(
        """
        INSERT INTO chats (
            chat_id,
            title,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            chat_id,
            clean_title,
            now,
            now
        )
    )

    connection.commit()

    connection.close()

    return chat_id


# =========================================================
# GET CHAT
# =========================================================

def get_chat(
    chat_id
):
    """
    Return one chat.
    """

    if not chat_id:
        return None

    initialize_chat_database()

    connection = _get_connection()

    row = connection.execute(
        """
        SELECT
            chat_id,
            title,
            created_at,
            updated_at
        FROM chats
        WHERE chat_id = ?
        """,
        (
            str(chat_id),
        )
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return dict(row)


# =========================================================
# LIST CHATS
# =========================================================

def list_chats():
    """
    Return chats ordered by latest activity.
    """

    initialize_chat_database()

    connection = _get_connection()

    rows = connection.execute(
        """
        SELECT
            chat_id,
            title,
            created_at,
            updated_at
        FROM chats
        ORDER BY updated_at DESC
        """
    ).fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# DEFAULT TITLE CHECK
# =========================================================

def is_default_chat_title(
    title
):
    """
    Return True when the chat still has a default title.

    Automatic naming is allowed only while the chat has
    one of these default titles.
    """

    if title is None:
        return True

    normalized = (
        str(title)
        .strip()
        .lower()
    )

    return normalized in {
        "",
        "new chat",
        "new conversation",
        "untitled",
        "untitled chat"
    }


# =========================================================
# CLEAN CHAT TITLE
# =========================================================

def clean_chat_title(
    title,
    max_length=100
):
    """
    Normalize a chat title before saving it.
    """

    if title is None:
        return "New Chat"

    title = str(
        title
    ).strip()

    if not title:
        return "New Chat"

    # Remove duplicate whitespace.
    title = " ".join(
        title.split()
    )

    # Prevent excessively long titles.
    title = title[:max_length].strip()

    if not title:
        return "New Chat"

    return title


# =========================================================
# UPDATE CHAT TITLE
# =========================================================

def update_chat_title(
    chat_id,
    title
):
    """
    Permanently update a chat title in SQLite.

    Returns:
        True  -> chat existed and was updated
        False -> chat did not exist
    """

    if not chat_id:
        return False

    initialize_chat_database()

    title = clean_chat_title(
        title
    )

    now = datetime.now().isoformat()

    connection = _get_connection()

    cursor = connection.execute(
        """
        UPDATE chats
        SET
            title = ?,
            updated_at = ?
        WHERE chat_id = ?
        """,
        (
            title,
            now,
            str(chat_id)
        )
    )

    connection.commit()

    updated = (
        cursor.rowcount > 0
    )

    connection.close()

    return updated


# =========================================================
# GENERATE CHAT TITLE FROM QUESTION
# =========================================================

def generate_chat_title_from_question(
    question,
    max_length=60
):
    """
    Generate a simple readable title from the user's first
    question.

    Example:

        What is cloud computing?

    becomes:

        What is cloud computing
    """

    if not question:
        return "New Chat"

    title = str(
        question
    ).strip()

    # Normalize whitespace.
    title = " ".join(
        title.split()
    )

    if not title:
        return "New Chat"

    # -----------------------------------------------------
    # Remove common conversational prefixes.
    # -----------------------------------------------------

    prefixes = [
        "please explain ",
        "can you explain ",
        "could you explain ",
        "can you tell me ",
        "could you tell me ",
        "please tell me ",
        "tell me about ",
    ]

    lower_title = title.lower()

    for prefix in prefixes:

        if lower_title.startswith(
            prefix
        ):

            title = title[
                len(prefix):
            ].strip()

            break

    # -----------------------------------------------------
    # Remove ending punctuation.
    # -----------------------------------------------------

    title = title.rstrip(
        ".?!"
    ).strip()

    if not title:
        return "New Chat"

    # -----------------------------------------------------
    # Capitalize first character.
    # -----------------------------------------------------

    title = (
        title[0].upper() +
        title[1:]
    )

    # -----------------------------------------------------
    # Limit title length.
    # -----------------------------------------------------

    if len(title) > max_length:

        title = (
            title[:max_length - 3]
            .rstrip()
            + "..."
        )

    return title


# =========================================================
# AUTO-NAME CHAT
# =========================================================

def auto_name_chat(
    chat_id,
    question
):
    """
    Automatically name a chat from the first question.

    IMPORTANT:

    If the user has already manually renamed the chat,
    this function will NOT overwrite that title.

    Returns:
        The final chat title, or None if chat doesn't exist.
    """

    if not chat_id:
        return None

    if not question:
        return None

    chat = get_chat(
        chat_id
    )

    if not chat:
        return None

    current_title = chat.get(
        "title",
        "New Chat"
    )

    # -----------------------------------------------------
    # NEVER overwrite an existing custom title.
    # -----------------------------------------------------

    if not is_default_chat_title(
        current_title
    ):

        return current_title

    # -----------------------------------------------------
    # Generate title.
    # -----------------------------------------------------

    new_title = (
        generate_chat_title_from_question(
            question
        )
    )

    if is_default_chat_title(
        new_title
    ):

        return current_title

    # -----------------------------------------------------
    # Save title.
    # -----------------------------------------------------

    update_chat_title(
        chat_id,
        new_title
    )

    return new_title


# =========================================================
# TOUCH CHAT
# =========================================================

def touch_chat(
    chat_id
):
    """
    Update the last activity time of a chat.
    """

    if not chat_id:
        return False

    initialize_chat_database()

    now = datetime.now().isoformat()

    connection = _get_connection()

    cursor = connection.execute(
        """
        UPDATE chats
        SET updated_at = ?
        WHERE chat_id = ?
        """,
        (
            now,
            str(chat_id)
        )
    )

    connection.commit()

    updated = (
        cursor.rowcount > 0
    )

    connection.close()

    return updated


# =========================================================
# SAVE MESSAGE
# =========================================================

def save_message(
    chat_id,
    message
):
    """
    Save a complete chat message.

    Additional fields such as:

        sources
        analysis_result
        metadata

    are preserved inside message_data.
    """

    if not chat_id:
        raise ValueError(
            "chat_id is required"
        )

    if not isinstance(
        message,
        dict
    ):
        raise ValueError(
            "message must be a dictionary"
        )

    initialize_chat_database()

    role = str(
        message.get(
            "role",
            ""
        )
    ).strip()

    content = str(
        message.get(
            "content",
            ""
        )
    )

    if not role:
        raise ValueError(
            "message role is required"
        )

    message_data = json.dumps(
        message,
        ensure_ascii=False,
        default=str
    )

    now = datetime.now().isoformat()

    connection = _get_connection()

    connection.execute(
        """
        INSERT INTO messages (
            chat_id,
            role,
            content,
            message_data,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            str(chat_id),
            role,
            content,
            message_data,
            now
        )
    )

    # -----------------------------------------------------
    # Update chat activity.
    # -----------------------------------------------------

    connection.execute(
        """
        UPDATE chats
        SET updated_at = ?
        WHERE chat_id = ?
        """,
        (
            now,
            str(chat_id)
        )
    )

    connection.commit()

    connection.close()


# =========================================================
# GET MESSAGES
# =========================================================

def get_messages(
    chat_id
):
    """
    Load all messages for a chat.
    """

    if not chat_id:
        return []

    initialize_chat_database()

    connection = _get_connection()

    rows = connection.execute(
        """
        SELECT
            message_data,
            role,
            content
        FROM messages
        WHERE chat_id = ?
        ORDER BY id ASC
        """,
        (
            str(chat_id),
        )
    ).fetchall()

    connection.close()

    messages = []

    for row in rows:

        raw_data = row[
            "message_data"
        ]

        if raw_data:

            try:

                message = json.loads(
                    raw_data
                )

                if isinstance(
                    message,
                    dict
                ):

                    messages.append(
                        message
                    )

                    continue

            except (
                json.JSONDecodeError,
                TypeError
            ):

                pass

        # -------------------------------------------------
        # Fallback for old messages.
        # -------------------------------------------------

        messages.append(
            {
                "role":
                    row["role"],

                "content":
                    row["content"]
            }
        )

    return messages


# =========================================================
# ADD FILE TO CHAT
# =========================================================

def add_file(
    chat_id,
    file_key,
    file_name,
    file_path,
    file_size=None
):
    """
    Associate an uploaded file with a chat.

    IMPORTANT:
    Streamlit/file handling on Windows may return
    pathlib.WindowsPath.

    SQLite cannot bind WindowsPath directly, so the path
    is explicitly converted to a normal string.
    """

    if not chat_id:
        raise ValueError(
            "chat_id is required"
        )

    initialize_chat_database()

    # -----------------------------------------------------
    # Normalize values.
    # -----------------------------------------------------

    chat_id = str(
        chat_id
    )

    file_key = str(
        file_key
    )

    file_name = str(
        file_name
    )

    file_path = str(
        file_path
    )

    if file_size is not None:

        try:

            file_size = int(
                file_size
            )

        except (
            TypeError,
            ValueError
        ):

            file_size = None

    # -----------------------------------------------------
    # Insert file.
    # -----------------------------------------------------

    connection = _get_connection()

    connection.execute(
        """
        INSERT OR IGNORE INTO chat_files (
            chat_id,
            file_key,
            file_name,
            file_path,
            file_size
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            chat_id,
            file_key,
            file_name,
            file_path,
            file_size
        )
    )

    # -----------------------------------------------------
    # Update chat activity.
    # -----------------------------------------------------

    connection.execute(
        """
        UPDATE chats
        SET updated_at = ?
        WHERE chat_id = ?
        """,
        (
            datetime.now().isoformat(),
            chat_id
        )
    )

    connection.commit()

    connection.close()


# =========================================================
# GET CHAT FILES
# =========================================================

def get_chat_files(
    chat_id
):
    """
    Return all files belonging to a chat.
    """

    if not chat_id:
        return []

    initialize_chat_database()

    connection = _get_connection()

    rows = connection.execute(
        """
        SELECT
            id,
            file_key,
            file_name,
            file_path,
            file_size
        FROM chat_files
        WHERE chat_id = ?
        ORDER BY id ASC
        """,
        (
            str(chat_id),
        )
    ).fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# DELETE CHAT
# =========================================================

def delete_chat(
    chat_id
):
    """
    Delete a chat and its messages/files metadata.

    Because the database uses ON DELETE CASCADE,
    associated messages and chat_files records are also
    removed.
    """

    if not chat_id:
        return False

    initialize_chat_database()

    connection = _get_connection()

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    cursor = connection.execute(
        """
        DELETE FROM chats
        WHERE chat_id = ?
        """,
        (
            str(chat_id),
        )
    )

    connection.commit()

    deleted = (
        cursor.rowcount > 0
    )

    connection.close()

    return deleted


# =========================================================
# DELETE ALL CHATS
# =========================================================

def delete_all_chats():
    """
    Delete all saved chats.
    """

    initialize_chat_database()

    connection = _get_connection()

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.execute(
        "DELETE FROM chats"
    )

    connection.commit()

    connection.close()


# =========================================================
# CHECK CHAT EXISTENCE
# =========================================================

def chat_exists(
    chat_id
):
    """
    Return True when a chat exists.
    """

    if not chat_id:
        return False

    initialize_chat_database()

    connection = _get_connection()

    row = connection.execute(
        """
        SELECT 1
        FROM chats
        WHERE chat_id = ?
        LIMIT 1
        """,
        (
            str(chat_id),
        )
    ).fetchone()

    connection.close()

    return row is not None


# =========================================================
# END CHAT MANAGER
# =========================================================