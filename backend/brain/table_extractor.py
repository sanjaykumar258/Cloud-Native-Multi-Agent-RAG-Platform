"""
brain/table_extractor.py — Advanced table extraction.

Uses Camelot for digital PDFs and PaddleOCR for scanned documents/images.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class TableExtractor:
    """
    Extracts tabular data from documents with high precision.
    """
    _ocr_instance = None

    @classmethod
    def _get_ocr(cls):
        if cls._ocr_instance is None:
            try:
                from paddleocr import PaddleOCR
                cls._ocr_instance = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
                logger.info("PaddleOCR initialized (Singleton)")
            except Exception as e:
                logger.error("Failed to initialize PaddleOCR: %s", e)
        return cls._ocr_instance

    def extract_from_pdf(self, path: str | Path, pages: str = "all") -> str:
        """
        Attempt digital extraction (Camelot), fallback to OCR if needed.
        """
        path_str = str(path)
        tables_text = []

        # 1. Try Camelot (Digital)
        try:
            import camelot
            import pandas as pd
            logger.info("Extracting tables via Camelot from pages %s: %s", pages, path_str)
            tables = camelot.read_pdf(path_str, pages=pages, flavor='lattice')
            if tables.n == 0:
                tables = camelot.read_pdf(path_str, pages=pages, flavor='stream')
            
            if tables.n > 0:
                for i, table in enumerate(tables):
                    df = table.df
                    df = df.replace('', pd.NA).dropna(how='all', axis=0).dropna(how='all', axis=1)
                    tables_text.append(f"### Table {i+1} (extracted from digital PDF)\n" + df.to_markdown(index=False))
                return "\n\n".join(tables_text)
        except Exception as e:
            logger.debug("Camelot failed: %s", e)

        # 2. Try PaddleOCR (Scanned/Image fallback)
        try:
            ocr = self._get_ocr()
            if not ocr: return ""
            logger.info("Extracting tables via PaddleOCR: %s", path_str)
            # PaddleOCR doesn't easily support page ranges the same way as Camelot
            # but usually it's used for short documents or specific images anyway.
            result = ocr.ocr(path_str, cls=True)
            # result is a list of [box, [text, confidence]]
            
            # Simple text-to-table heuristic: group by Y coordinate
            lines = []
            for page in result:
                if not page: continue
                # Sort by Y coord then X coord
                sorted_page = sorted(page, key=lambda x: (x[0][0][1], x[0][0][0]))
                
                current_y = -1
                current_line = []
                threshold = 10 # pixel threshold for same row
                
                for res in sorted_page:
                    box, (text, score) = res
                    y = box[0][1]
                    if current_y == -1 or abs(y - current_y) < threshold:
                        current_line.append(text)
                        current_y = y
                    else:
                        lines.append(" | ".join(current_line))
                        current_line = [text]
                        current_y = y
                if current_line:
                    lines.append(" | ".join(current_line))

            return "### Extracted Table Data (OCR)\n" + "\n".join(lines)
        except Exception as e:
            logger.warning("All table extraction methods failed for %s: %s", path_str, e)
            return ""

    def run(self, path: str | Path, pages: str = "all") -> str:
        """Process file and return markdown representation of tables."""
        path = Path(path)
        if not path.exists():
            return ""

        if path.suffix.lower() == ".pdf":
            return self.extract_from_pdf(path, pages=pages)
        elif path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            return self.extract_from_image(path)
        return ""
