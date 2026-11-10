
import uuid
import json

from database import get_connection


# ==================================================
# CREATE CONVERSATION
# ==================================================

def create_conversation(
    document_name=None,
    title="New Conversation",
    document_names=None
):
    conversation_id = str(uuid.uuid4())

    if document_names is None:
        document_names = [document_name] if document_name else []

    document_names = list(dict.fromkeys(
        name.strip()
        for name in document_names
        if name and name.strip()
    ))

    if not document_names:
        raise ValueError("At least one document is required.")

    title = title.strip() or "New Conversation"

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO conversations (id, title, document_name)
            VALUES (?, ?, ?)
            """,
            (conversation_id, title, document_names[0])
        )

        cursor.executemany(
            """
            INSERT INTO conversation_documents
            (conversation_id, document_name)
            VALUES (?, ?)
            """,
            [
                (conversation_id, name)
                for name in document_names
            ]
        )

        connection.commit()

        return {
            "id": conversation_id,
            "title": title,
            "document_name": document_names[0],
            "document_names": document_names
        }

    finally:
        connection.close()


# ==================================================
# GENERATE CONVERSATION TITLE
# ==================================================

def generate_conversation_title(question):
    """
    Generate a readable title from the first user question.
    """

    title = " ".join(question.strip().split())

    if not title:
        return "New Conversation"

    if len(title) > 48:
        title = title[:45].rsplit(" ", 1)[0] + "..."

    return title


# ==================================================
# RENAME CONVERSATION
# ==================================================

def rename_conversation(conversation_id, title):

    title = title.strip()

    if not title:
        return False

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE conversations
            SET title = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (title, conversation_id)
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:
        connection.close()


# ==================================================
# GET DOCUMENTS ATTACHED TO A CONVERSATION
# ==================================================

def get_conversation_documents(conversation_id):

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT document_name
            FROM conversation_documents
            WHERE conversation_id = ?
            ORDER BY added_at ASC
            """,
            (conversation_id,)
        ).fetchall()

        return [row["document_name"] for row in rows]

    finally:
        connection.close()


# ==================================================
# ATTACH ANOTHER DOCUMENT
# ==================================================

def attach_document(conversation_id, document_name):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        conversation = cursor.execute(
            """
            SELECT id
            FROM conversations
            WHERE id = ?
            """,
            (conversation_id,)
        ).fetchone()

        if not conversation:
            return False

        cursor.execute(
            """
            INSERT OR IGNORE INTO conversation_documents
            (conversation_id, document_name)
            VALUES (?, ?)
            """,
            (conversation_id, document_name)
        )

        connection.commit()

        return True

    finally:
        connection.close()


# ==================================================
# DETACH DOCUMENT FROM CONVERSATION
# ==================================================

def detach_document(conversation_id, document_name):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        conversation = cursor.execute(
            """
            SELECT id
            FROM conversations
            WHERE id = ?
            """,
            (conversation_id,)
        ).fetchone()

        if not conversation:
            return False

        cursor.execute(
            """
            DELETE FROM conversation_documents
            WHERE conversation_id = ?
            AND document_name = ?
            """,
            (conversation_id, document_name)
        )

        if cursor.rowcount == 0:
            return False

        remaining = cursor.execute(
            """
            SELECT document_name
            FROM conversation_documents
            WHERE conversation_id = ?
            ORDER BY added_at ASC
            LIMIT 1
            """,
            (conversation_id,)
        ).fetchone()

        next_document = (
            remaining["document_name"] if remaining else ""
        )

        cursor.execute(
            """
            UPDATE conversations
            SET document_name = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (next_document, conversation_id)
        )

        connection.commit()

        return True

    finally:
        connection.close()


# ==================================================
# GET ALL CONVERSATIONS
# ==================================================

def get_conversations():

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM conversations
            ORDER BY updated_at DESC
            """
        ).fetchall()

        conversations = []

        for row in rows:

            conversation = dict(row)

            documents = connection.execute(
                """
                SELECT document_name
                FROM conversation_documents
                WHERE conversation_id = ?
                ORDER BY added_at ASC
                """,
                (conversation["id"],)
            ).fetchall()

            conversation["document_names"] = [
                item["document_name"] for item in documents
            ]

            if not conversation["document_names"]:
                legacy_name = conversation.get("document_name")

                if legacy_name:
                    conversation["document_names"] = [legacy_name]

            # Repair generic titles for older conversations
            if conversation["title"] == "New Conversation":

                first_message = connection.execute(
                    """
                    SELECT content
                    FROM messages
                    WHERE conversation_id = ?
                    AND role = 'user'
                    ORDER BY id ASC
                    LIMIT 1
                    """,
                    (conversation["id"],)
                ).fetchone()

                if first_message:
                    new_title = generate_conversation_title(
                        first_message["content"]
                    )

                    connection.execute(
                        """
                        UPDATE conversations
                        SET title = ?
                        WHERE id = ?
                        """,
                        (new_title, conversation["id"])
                    )

                    conversation["title"] = new_title

            conversations.append(conversation)

        connection.commit()

        return conversations

    finally:
        connection.close()


# ==================================================
# ADD MESSAGE
# ==================================================

def add_message(conversation_id, role, content, sources=None):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        conversation = cursor.execute(
            """
            SELECT id, title
            FROM conversations
            WHERE id = ?
            """,
            (conversation_id,)
        ).fetchone()

        if not conversation:
            raise ValueError("Conversation not found.")

        cursor.execute(
            """
            INSERT INTO messages
            (conversation_id, role, content, sources_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                conversation_id,
                role,
                content,
                json.dumps(sources or [])
            )
        )

        # Automatically title the conversation from its first question
        if (
            role == "user"
            and conversation["title"] == "New Conversation"
        ):
            new_title = generate_conversation_title(content)

            cursor.execute(
                """
                UPDATE conversations
                SET title = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (new_title, conversation_id)
            )

        else:
            cursor.execute(
                """
                UPDATE conversations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (conversation_id,)
            )

        connection.commit()

    finally:
        connection.close()


# ==================================================
# GET MESSAGES
# ==================================================

def get_messages(conversation_id):

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,)
        ).fetchall()

        messages = []

        for row in rows:

            message = dict(row)

            message["sources"] = json.loads(
                message.pop("sources_json") or "[]"
            )

            messages.append(message)

        return messages

    finally:
        connection.close()


# ==================================================
# DELETE CONVERSATION
# ==================================================

def delete_conversation(conversation_id):

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            DELETE FROM conversations
            WHERE id = ?
            """,
            (conversation_id,)
        )

        connection.commit()

        # Foreign-key cascade removes:
        # 1. Messages
        # 2. Conversation-document associations

        return cursor.rowcount > 0

    finally:
        connection.close()


# ==================================================
# REMOVE DOCUMENT FROM ALL CONVERSATIONS
# ==================================================

def remove_document_from_all_conversations(document_name):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Remove document associations, but preserve conversations
        cursor.execute(
            """
            DELETE FROM conversation_documents
            WHERE document_name = ?
            """,
            (document_name,)
        )

        # Update the legacy document_name field
        # to the next attached document, if available
        cursor.execute(
            """
            UPDATE conversations
            SET document_name = COALESCE(
                (
                    SELECT cd.document_name
                    FROM conversation_documents cd
                    WHERE cd.conversation_id = conversations.id
                    ORDER BY cd.added_at ASC
                    LIMIT 1
                ),
                ''
            ),
            updated_at = CURRENT_TIMESTAMP
            WHERE document_name = ?
            """,
            (document_name,)
        )

        connection.commit()

        return cursor.rowcount

    finally:
        connection.close()

