
import sqlite3
from pathlib import Path

# Database location
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "conversations.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # ------------------------------------------
        # CONVERSATIONS TABLE
        # ------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                document_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ------------------------------------------
        # MESSAGES TABLE
        # ------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL
                    CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                sources_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (conversation_id)
                REFERENCES conversations(id)
                ON DELETE CASCADE
            )
        """)

        # ------------------------------------------
        # NEW: CONVERSATION DOCUMENTS TABLE
        # ------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_documents (
                conversation_id TEXT NOT NULL,
                document_name TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                PRIMARY KEY (conversation_id, document_name),

                FOREIGN KEY (conversation_id)
                REFERENCES conversations(id)
                ON DELETE CASCADE
            )
        """)

        # ------------------------------------------
        # MIGRATE EXISTING CONVERSATIONS
        # ------------------------------------------

        # Every old conversation already has one
        # document_name. Add it to the new relationship
        # table without creating duplicates.

        cursor.execute("""
            INSERT OR IGNORE INTO conversation_documents
            (conversation_id, document_name)
            SELECT id, document_name
            FROM conversations
            WHERE document_name IS NOT NULL
        """)

        # ------------------------------------------
        # INDEXES
        # ------------------------------------------

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
            ON messages(conversation_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation_documents
            ON conversation_documents(document_name)
        """)

        connection.commit()

        print("SQLite database initialized successfully!")
        print("Conversation document relationships migrated.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
