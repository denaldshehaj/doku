"""PDF ingestion: extract text per page (PyMuPDF), validate the PDF actually has
selectable text (no OCR in base version), and chunk into overlapping windows
carrying source metadata. Scanned/empty PDFs are flagged, never silently indexed
(DoD for ingestion)."""
from dataclasses import dataclass

import fitz  # PyMuPDF

import config


@dataclass
class Chunk:
    text: str
    page: int          # 1-based page number
    chunk_index: int   # position within the document


class NoExtractableTextError(Exception):
    """Raised when a PDF has (almost) no selectable text — likely a scan."""


def extract_pages(pdf_path) -> list[str]:
    """Return a list of page texts (index 0 == page 1)."""
    pages = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            pages.append(page.get_text("text"))
    return pages


def validate_has_text(pages: list[str], min_chars: int = 100) -> None:
    total = sum(len(p.strip()) for p in pages)
    if total < min_chars:
        raise NoExtractableTextError(
            "Ky PDF nuk përmban tekst të lexueshëm (ndoshta është i skanuar). "
            "Versioni bazë nuk mbështet OCR."
        )


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Character-window chunking with overlap, breaking near whitespace."""
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:
            # try to break on the last whitespace within the window
            ws = text.rfind(" ", start + overlap, end)
            if ws != -1 and ws > start:
                end = ws
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def build_chunks(pdf_path) -> tuple[list[Chunk], int]:
    """Extract, validate, and chunk a PDF. Returns (chunks, n_pages).

    Raises NoExtractableTextError if the PDF has no usable text.
    """
    pages = extract_pages(pdf_path)
    validate_has_text(pages)
    chunks: list[Chunk] = []
    idx = 0
    for page_no, page_text in enumerate(pages, start=1):
        for piece in chunk_text(page_text, config.CHUNK_SIZE, config.CHUNK_OVERLAP):
            chunks.append(Chunk(text=piece, page=page_no, chunk_index=idx))
            idx += 1
    if not chunks:
        raise NoExtractableTextError("Nuk u nxor asnjë tekst nga dokumenti.")
    return chunks, len(pages)
