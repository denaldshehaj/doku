"""Smoke tests for pure logic (no Ollama, no model download required).

Run:  .venv\\Scripts\\python.exe tests\\smoke_test.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import doku  # noqa: F401,E402  (sets sys.path)
import config  # noqa: E402
from doku import auth, ingestion  # noqa: E402


def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    return bool(cond)


def run():
    ok = True

    # Chunking: respects size and produces non-empty pieces with overlap.
    text = "fjalë " * 500
    chunks = ingestion.chunk_text(text, size=200, overlap=40)
    ok &= check("chunk_text prodhon copëza", len(chunks) > 1)
    ok &= check("copëzat nuk e kalojnë shumë madhësinë",
                all(len(c) <= 240 for c in chunks))

    # Text validation: empty/short -> raises; real text -> passes.
    raised = False
    try:
        ingestion.validate_has_text(["", "  "])
    except ingestion.NoExtractableTextError:
        raised = True
    ok &= check("validate_has_text ngre gabim për PDF bosh", raised)

    passed_text = True
    try:
        ingestion.validate_has_text(["x" * 200])
    except ingestion.NoExtractableTextError:
        passed_text = False
    ok &= check("validate_has_text kalon për tekst real", passed_text)

    # Password hashing: never plaintext, verifies correctly.
    h = auth.hash_password("sekret123")
    ok &= check("hash-i nuk është plaintext", h != "sekret123")
    ok &= check("verifikimi i fjalëkalimit punon",
                auth.verify_password("sekret123", h) and not auth.verify_password("gabim", h))

    # Config sanity.
    ok &= check("pragu i refuzimit në [0,1]", 0 < config.MIN_SIMILARITY < 1)

    print(f"\n=== {'TË GJITHA KALUAN' if ok else 'KA DËSHTIME'} ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
