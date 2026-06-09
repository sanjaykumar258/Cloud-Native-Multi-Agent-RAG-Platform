"""
brain/ingest.py — End-to-end ingestion pipeline.

Usage (CLI):
    python -m brain.ingest --folder "D:/my_docs"

Usage (Python):
    from backend.brain.ingest import ingest_folder
    for event in ingest_folder("D:/my_docs"):
        print(event)   # dict with 'type', 'message', 'progress'
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
from typing import Generator
import concurrent.futures

logger = logging.getLogger(__name__)


# ─── Public API ───────────────────────────────────────────────────────────────

def ingest_folder(
    folder_path: str | Path,
    force: bool = False,
    enable_vision: bool = True,
    enable_tables: bool = True,
    enable_graph: bool = False,
) -> Generator[dict, None, None]:
    """
    Ingest all supported files in folder_path into ChromaDB.

    Yields progress event dicts:
      { type: 'start'|'file'|'progress'|'done'|'error', message: str, progress: float }
    """
    from backend.brain.loader import load_document
    from backend.brain.chunker import chunk_elements
    from backend.brain.vectorstore import VectorStore
    from backend.config import SUPPORTED_EXTENSIONS

    folder = Path(folder_path)
    if not folder.exists():
        yield _event("error", f"Folder not found: {folder}", 0.0)
        return

    # Collect files
    files = [
        f for f in folder.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if not files:
        yield _event("error", f"No supported files found in {folder}", 0.0)
        return

    total = len(files)
    vs = VectorStore()

    # ── Incremental Indexing ──────────────────────────────────────────────
    # Instead of clearing everything and rebuilding, we:
    #   1. Compute file hashes for all current files
    #   2. Compare against stored hashes from last run
    #   3. Only process new/changed files
    #   4. Remove stale files that no longer exist

    from backend.brain.cache import cache, get_file_hash
    HASH_CACHE_KEY = "file_hashes"
    old_hashes: dict = cache.get(HASH_CACHE_KEY) or {}
    new_hashes: dict = {}

    files_to_process = []
    skipped = 0
    
    kg = None
    if enable_graph:
        from backend.brain.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        if force:
            kg.clear()

    yield _event("progress", "Checking for changes...", 0.0)

    for f in files:
        fhash = get_file_hash(f)
        fkey = str(f.resolve())
        new_hashes[fkey] = fhash

        if force or old_hashes.get(fkey) != fhash:
            files_to_process.append(f)
        else:
            skipped += 1

    # Remove stale sources (files that were deleted from the folder)
    current_keys = set(new_hashes.keys())
    stale_keys = set(old_hashes.keys()) - current_keys
    for stale_key in stale_keys:
        stale_name = Path(stale_key).name
        vs.clear_by_source(stale_name)
        logger.info("Removed stale source: %s", stale_name)

    if not files_to_process:
        # Save hashes and finish immediately
        cache.set(HASH_CACHE_KEY, new_hashes)
        final_count = vs.count()
        yield _event("done", f"No changes detected. {skipped} files unchanged. {final_count} chunks in index.", 1.0)
        return

    yield _event("progress", f"Processing {len(files_to_process)} changed files ({skipped} unchanged, skipped)...", 0.05)

    def _process_file(file: Path):
        try:
            # Clear old chunks for this specific file first
            vs.clear_by_source(file.name)
            # Load → chunk → store
            elements = load_document(file, enable_vision=enable_vision, enable_tables=enable_tables)
            if not elements:
                return {"type": "progress", "message": f"  Skipped (no content): {file.name}"}

            chunks = chunk_elements(elements)
            vs.add_chunks(chunks)
            
            extraction = None
            if enable_graph:
                from backend.brain.entity_extractor import extract_entities
                full_text = "\n".join([c["text"] for c in chunks])[:10000]
                extraction = extract_entities(full_text, file.name)
                
            return {"type": "file", "message": f"Loaded: {file.name}", "extraction": extraction, "file_name": file.name}
        except Exception as exc:
            logger.error("Ingestion failed for %s: %s", file, exc)
            return {"type": "error", "message": f"  ✗ {file.name}: {exc}"}

    processed_count = 0
    process_total = len(files_to_process)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_file = {executor.submit(_process_file, f): f for f in files_to_process}
        for future in concurrent.futures.as_completed(future_to_file):
            processed_count += 1
            res = future.result()
            
            if enable_graph and res.get("extraction") and kg is not None:
                kg.add_entities_and_relations(res["file_name"], res["extraction"])
                
            progress = 0.05 + (processed_count / process_total) * 0.95
            yield _event(res["type"], res["message"], progress)

    # Save new hashes
    cache.set(HASH_CACHE_KEY, new_hashes)

    final_count = vs.count()
    yield _event("done", f"Ingestion complete. {process_total} files processed, {skipped} skipped -> {final_count} chunks in index.", 1.0)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _event(type_: str, message: str, progress: float) -> dict:
    return {"type": type_, "message": message, "progress": progress}


# ─── CLI ─────────────────────────────────────────────────────────────────────

def _main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    parser = argparse.ArgumentParser(description="Ingest documents into the Brain vector store.")
    parser.add_argument("--folder", required=True, help="Path to the document folder")
    parser.add_argument("--force", action="store_true", help="Force re-index even if unchanged")
    args = parser.parse_args()

    for event in ingest_folder(args.folder, force=args.force):
        print(f"[{event['type'].upper():8}] {event['message']}")

    print("Done.")


if __name__ == "__main__":
    _main()
