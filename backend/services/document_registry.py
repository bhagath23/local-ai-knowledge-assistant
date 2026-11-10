
import hashlib
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
REGISTRY_FILE = BASE_DIR / "document_registry.json"


def calculate_file_hash(file_path):
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def load_registry():
    if not REGISTRY_FILE.exists():
        return {}

    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as file:
            registry = json.load(file)

        if not isinstance(registry, dict):
            raise RuntimeError("Invalid document registry format.")

        return registry

    except (json.JSONDecodeError, OSError):
        raise RuntimeError("Document registry could not be read.")


def save_registry(registry):
    temp_file = REGISTRY_FILE.with_suffix(".tmp")

    try:
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(registry, file, indent=4)

        temp_file.replace(REGISTRY_FILE)

    except OSError:
        if temp_file.exists():
            temp_file.unlink()
        raise RuntimeError("Document registry could not be saved.")


def find_document(file_hash):
    registry = load_registry()
    return registry.get(file_hash)


def register_document(file_hash, filename):
    registry = load_registry()

    registry[file_hash] = {
        "filename": filename,
        "hash": file_hash
    }

    save_registry(registry)
    return True


def unregister_document(file_hash):
    """
    Remove one exact document entry using its SHA-256 hash.
    Returns the removed entry, or None if it does not exist.
    """
    registry = load_registry()

    removed_entry = registry.pop(file_hash, None)

    if removed_entry is not None:
        save_registry(registry)

    return removed_entry


def unregister_documents_by_filename(filename):
    """
    Remove registry entries matching the exact original filename.
    Returns the removed entries, keyed by their hashes.
    """
    registry = load_registry()

    removed_entries = {
        file_hash: entry
        for file_hash, entry in registry.items()
        if entry.get("filename") == filename
    }

    if removed_entries:
        for file_hash in removed_entries:
            registry.pop(file_hash)

        save_registry(registry)

    return removed_entries
