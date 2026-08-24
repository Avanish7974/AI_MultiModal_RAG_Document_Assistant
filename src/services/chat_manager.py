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
            str(title),
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
# UPDATE CHAT TITLE
# =========================================================

def update_chat_title(
    chat_id,
    title
):
    """
    Update a chat title.
    """

    initialize_chat_database()

    title = str(
        title
    ).strip()

    if not title:
        title = "New Chat"

    now = datetime.now().isoformat()

    connection = _get_connection()

    connection.execute(
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

    connection.close()


# =========================================================
# TOUCH CHAT
# =========================================================

def touch_chat(
    chat_id
):
    """
    Update the last activity time of a chat.
    """

    initialize_chat_database()

    now = datetime.now().isoformat()

    connection = _get_connection()

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

    are preserved inside message_data.
    """

    initialize_chat_database()

    role = str(
        message.get(
            "role",
            ""
        )
    )

    content = str(
        message.get(
            "content",
            ""
        )
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

        raw_data = row["message_data"]

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

        messages.append(
            {
                "role": row["role"],
                "content": row["content"]
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

    initialize_chat_database()

    # -----------------------------------------------------
    # NORMALIZE VALUES BEFORE SQLITE
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
    # INSERT FILE
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
    # UPDATE CHAT TIME
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

    initialize_chat_database()

    connection = _get_connection()

    rows = connection.execute(
        """
        SELECT
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
    """

    initialize_chat_database()

    connection = _get_connection()

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.execute(
        """
        DELETE FROM chats
        WHERE chat_id = ?
        """,
        (
            str(chat_id),
        )
    )

    connection.commit()

    connection.close()


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