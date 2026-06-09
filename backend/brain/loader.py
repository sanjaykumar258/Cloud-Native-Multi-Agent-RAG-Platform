"""
brain/loader.py — Intelligent document loader.

Uses the `unstructured` library to detect element types inside PDFs,
Markdown, and plain text. Elements can be text or images (with AI descriptions).
Each element is returned as a dict with:
  - text:         the raw content or image description
  - metadata:     source, page_number, element_type, heading (if any), image_path (optional)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)

# ─── Public API ───────────────────────────────────────────────────────────────

def load_document(file_path: str | Path, enable_vision: bool = True, enable_tables: bool = True) -> list[dict]:
    """
    Load a single file and return a list of element dicts.
    Supported: .pdf, .md, .markdown, .txt, .text
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _load_pdf(path, enable_vision=enable_vision, enable_tables=enable_tables)
    elif suffix in (".md", ".markdown"):
        return _load_markdown(path)
    elif suffix in (".txt", ".text"):
        return _load_text(path)
    else:
        logger.warning("Unsupported file type: %s — skipping.", suffix)
        return []


def load_folder(folder_path: str | Path) -> Generator[dict, None, None]:
    """
    Recursively scan a folder and yield element dicts from every supported file.
    """
    from backend.config import SUPPORTED_EXTENSIONS

    folder = Path(folder_path)
    files = [
        f for f in folder.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    logger.info("Found %d supported files in %s", len(files), folder)

    for file in files:
        try:
            elements = load_document(file)
            logger.debug("  %s → %d elements", file.name, len(elements))
            yield from elements
        except Exception as exc:
            logger.error("Failed to load %s: %s", file, exc)


def count_files(folder_path: str | Path) -> int:
    from backend.config import SUPPORTED_EXTENSIONS
    folder = Path(folder_path)
    return sum(
        1 for f in folder.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )


# Singletons for heavy model-based tools
_table_extractor = None
_vision_agent = None

def _get_table_extractor():
    global _table_extractor
    if _table_extractor is None:
        from backend.brain.table_extractor import TableExtractor
        _table_extractor = TableExtractor()
    return _table_extractor

def _get_vision_agent():
    global _vision_agent
    if _vision_agent is None:
        from backend.agents.vision_agent import VisionAgent
        from backend.config import VISION_MODEL
        _vision_agent = VisionAgent(model=VISION_MODEL)
    return _vision_agent

def _load_pdf(path: Path, enable_vision: bool = True, enable_tables: bool = True) -> list[dict]:
    """Extremely fast parallelized PDF loader."""
    results = []
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        
        # 1. Immediate Text Extraction (Very Fast)
        #    Use layout mode to preserve table column alignment
        doc_text_by_page = []
        full_text = ""
        for page_num, page in enumerate(reader.pages, start=1):
            # Try layout mode first (preserves table columns)
            try:
                text = page.extract_text(extraction_mode="layout") or ""
            except Exception:
                text = page.extract_text() or ""
            doc_text_by_page.append((page_num, text))
            full_text += text + "\n"
            if text.strip():
                results.append({
                    "text": text.strip(),
                    "metadata": {
                        "source": path.name,
                        "source_path": str(path),
                        "page_number": page_num,
                        "element_type": "NarrativeText",
                        "heading": None,
                    },
                })

        # 2. Parallelize Global Document Tasks (Images + Tables)
        import concurrent.futures
        tasks = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # A. Vision Tasks (Images)
            if enable_vision:
                from backend.brain.cache import cache, get_file_hash
                temp_img_dir = Path("temp_images")
                temp_img_dir.mkdir(exist_ok=True)
                vagent = _get_vision_agent()
                
                def _process_image(image_data, name, p_num):
                    img_path = temp_img_dir / name
                    with open(img_path, "wb") as fp:
                        fp.write(image_data)
                    
                    # Cache Check
                    img_hash = get_file_hash(img_path)
                    cache_key = f"vision_{img_hash}"
                    cached_desc = cache.get(cache_key)
                    
                    if cached_desc:
                        logger.info("Vision: Cache hit for %s", name)
                        desc = cached_desc
                    else:
                        logger.info("Vision: Describing %s", name)
                        desc = vagent.describe_image(img_path, prompt="Describe this document image in detail.")
                        cache.set(cache_key, desc)

                    return {
                        "text": f"[IMAGE DESCRIPTION: {name}]\n{desc}",
                        "metadata": {
                            "source": path.name,
                            "source_path": str(path),
                            "page_number": p_num,
                            "element_type": "Image",
                            "image_path": str(img_path),
                        },
                    }

                for page_num, page in enumerate(reader.pages, start=1):
                    # pypdf image extraction
                    for count, image_file in enumerate(page.images):
                        img_name = f"{path.stem}_p{page_num}_img{count}.{image_file.name.split('.')[-1]}"
                        tasks.append(executor.submit(_process_image, image_file.data, img_name, page_num))

            # B. Table Tasks (Smarter targeting)
            if enable_tables:
                from backend.brain.cache import cache, get_file_hash
                te = _get_table_extractor()
                # Check for table keywords per page to target Camelot specifically
                target_pages = []
                table_keywords = ["Table", "Total", "|", "Qty", "Amount", "Price", "Date", "Description"]
                for p_num, p_text in doc_text_by_page:
                    if any(kw.lower() in p_text.lower() for kw in table_keywords):
                        target_pages.append(str(p_num))
                
                if target_pages:
                    pages_str = ",".join(target_pages)
                    
                    def _extract_tables(p_str):
                        # Cache Check for tables
                        file_hash = get_file_hash(path)
                        cache_key = f"tables_{file_hash}_{p_str}"
                        cached_md = cache.get(cache_key)
                        
                        if cached_md:
                            logger.info("Tables: Cache hit for %s (pages %s)", path.name, p_str)
                            markdown = cached_md
                        else:
                            logger.info("Tables: Extracting from pages %s in %s", p_str, path.name)
                            markdown = te.run(path, pages=p_str)
                            cache.set(cache_key, markdown)

                        if markdown:
                            return {
                                "text": markdown,
                                "metadata": {
                                    "source": path.name,
                                    "source_path": str(path),
                                    "page_number": 0,
                                    "element_type": "Table",
                                },
                            }
                        return None
                    tasks.append(executor.submit(_extract_tables, pages_str))

            # Collect results
            for future in concurrent.futures.as_completed(tasks):
                try:
                    res = future.result()
                    if res:
                        # Put table data at the FRONT so LLM sees it first
                        if res.get("metadata", {}).get("element_type") == "Table":
                            results.insert(0, res)
                        else:
                            results.append(res)
                except Exception as task_exc:
                    logger.debug("Background document task failed: %s", task_exc)

    except Exception as e:
        logger.error("Global PDF loading failed for %s: %s", path.name, e)
        if not results:
            return []

    return results


# ─── Markdown loader ──────────────────────────────────────────────────────────

def _load_markdown(path: Path) -> list[dict]:
    return _load_text(path)


# ─── Plain text loader ────────────────────────────────────────────────────────

def _load_text(path: Path) -> list[dict]:
    """Read a text file natively without heavy parser tools."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            return []
        return [{
            "text": text,
            "metadata": {
                "source": path.name,
                "source_path": str(path),
                "page_number": 1,
                "element_type": "NarrativeText",
                "heading": None,
            },
        }]
    except Exception as exc:
        logger.error("Text load failed for %s: %s", path.name, exc)
        return []


