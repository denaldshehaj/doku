"""Generate a small Albanian institutional sample corpus (PDFs) and ingest it,
so the system is demoable out of the box. Idempotent: skips already-indexed files.

Run:  .venv\\Scripts\\python.exe scripts\\make_sample_corpus.py
"""
import os
import sys
import tempfile
from pathlib import Path

import fitz  # PyMuPDF

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from doku import db, documents, ingestion  # noqa: E402

CORPUS = [
    {
        "filename": "ligj_tatimor_2023.pdf",
        "title": "Ligji për Procedurat Tatimore",
        "doc_type": "ligj", "institution": "Ministria e Financave", "year": 2023,
        "paragraphs": [
            "Neni 1. Çdo tatimpagues është i detyruar të paraqesë deklaratën tatimore "
            "vjetore brenda datës 31 mars të vitit pasardhës.",
            "Neni 2. Mospagimi i detyrimeve tatimore brenda afatit ligjor sjell gjoba "
            "administrative si dhe kamatëvonesa të llogaritura mbi shumën e papaguar.",
            "Neni 3. Tatimpaguesi ka të drejtë të ankohet pranë Drejtorisë së "
            "Apelimit Tatimor brenda 30 ditëve nga njoftimi i vlerësimit.",
        ],
    },
    {
        "filename": "rregullore_punes_2022.pdf",
        "title": "Rregullore për Marrëdhëniet e Punës",
        "doc_type": "rregullore", "institution": "Ministria e Ekonomisë", "year": 2022,
        "paragraphs": [
            "Punonjësi ka të drejtën e pushimit vjetor të paguar prej të paktën 28 "
            "ditësh kalendarike në vit.",
            "Orari normal i punës është 40 orë në javë. Puna jashtë orarit paguhet me "
            "shtesë mbi pagën bazë sipas legjislacionit në fuqi.",
            "Kontrata e punës mund të zgjidhet me njoftim paraprak prej të paktën 30 "
            "ditësh nga secila palë.",
        ],
    },
    {
        "filename": "strategjia_dixhitale_2030.pdf",
        "title": "Strategjia Kombëtare e Dixhitalizimit 2030",
        "doc_type": "strategji", "institution": "Agjencia Kombëtare e Shoqërisë së "
        "Informacionit", "year": 2021,
        "paragraphs": [
            "Strategjia synon ofrimin e të paktën 90 për qind të shërbimeve publike "
            "online deri në vitin 2030.",
            "Objektiv kryesor është reduktimi i barrës administrative për qytetarët dhe "
            "bizneset përmes dixhitalizimit të procedurave.",
            "Investimet do të përqendrohen në infrastrukturën e të dhënave, sigurinë "
            "kibernetike dhe aftësimin dixhital të nëpunësve publikë.",
        ],
    },
]


def make_pdf(path: Path, title: str, paragraphs: list[str]) -> None:
    doc = fitz.open()
    page = doc.new_page()
    body = title + "\n\n" + "\n\n".join(paragraphs)
    page.insert_textbox(fitz.Rect(50, 50, 545, 800), body, fontsize=12, fontname="helv")
    doc.save(str(path))
    doc.close()


def main():
    db.init_db()
    tmpdir = Path(tempfile.gettempdir())
    added = 0
    for item in CORPUS:
        if any(d["filename"] == item["filename"] for d in documents.list_documents()):
            print(f"  (anashkaluar, ekziston) {item['filename']}")
            continue
        pdf_path = tmpdir / item["filename"]
        make_pdf(pdf_path, item["title"], item["paragraphs"])
        try:
            _, n = documents.add_document(
                pdf_path, item["filename"], title=item["title"],
                doc_type=item["doc_type"], institution=item["institution"],
                year=item["year"])
            print(f"  + {item['filename']} ({n} copëza)")
            added += 1
        except (ingestion.NoExtractableTextError, ValueError) as e:
            print(f"  ! {item['filename']}: {e}")
    print(f"Përfundoi. U shtuan {added} dokumente.")


if __name__ == "__main__":
    main()
