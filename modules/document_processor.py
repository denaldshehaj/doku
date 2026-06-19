"""PDF processing: extract text per page (PyMuPDF), validate the PDF actually has
selectable text (no OCR in the base version), and split into overlapping chunks
carrying the source page number."""
from dataclasses import dataclass

import fitz  # PyMuPDF

import config


@dataclass
class Chunk:
    text: str
    page_number: int   # 1-based
    chunk_index: int


class NoExtractableTextError(Exception):
    """Raised when a PDF has (almost) no selectable text — likely a scan."""


def extract_pages(pdf_path) -> list[str]:
    pages = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            pages.append(page.get_text("text"))
    return pages


def validate_has_text(pages: list[str], min_chars: int = 100) -> None:
    if sum(len(p.strip()) for p in pages) < min_chars:
        raise NoExtractableTextError(
            "Ky PDF nuk përmban tekst të lexueshëm (ndoshta është i skanuar). "
            "Versioni bazë nuk mbështet OCR."
        )


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Character-window chunking with overlap, breaking near whitespace."""
    text = text.strip()
    if not text:
        return []
    chunks, start, n = [], 0, len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:
            ws = text.rfind(" ", start + overlap, end)
            if ws != -1 and ws > start:
                end = ws
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def process_pdf(pdf_path) -> tuple[list[Chunk], int]:
    """Extract, validate, and chunk a PDF. Returns (chunks, n_pages).
    Raises NoExtractableTextError if the PDF has no usable text."""
    pages = extract_pages(pdf_path)
    validate_has_text(pages)
    chunks, idx = [], 0
    for page_no, page_text in enumerate(pages, start=1):
        for piece in chunk_text(page_text, config.CHUNK_SIZE, config.CHUNK_OVERLAP):
            chunks.append(Chunk(text=piece, page_number=page_no, chunk_index=idx))
            idx += 1
    if not chunks:
        raise NoExtractableTextError("Nuk u nxor asnjë tekst nga dokumenti.")
    return chunks, len(pages)
