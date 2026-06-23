"""Build the DOKU knowledge base from the master corpus of real Albanian laws.

The source-of-truth PDFs live in ``data/corpus/`` (committed to the repo). This
script copies each into ``data/uploads/`` (the working copy the system serves),
extracts + chunks + embeds it, and indexes it in ChromaDB so it is immediately
searchable from the UI.

By default it is idempotent (skips documents already present). Pass ``--reset``
to wipe the existing corpus (SQLite rows + all vectors + working copies) and
rebuild it from scratch — use this when the master corpus changes.

Run:
    .venv\\Scripts\\python.exe scripts\\seed_sample_corpus.py            # add missing
    .venv\\Scripts\\python.exe scripts\\seed_sample_corpus.py --reset    # rebuild
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from modules import auth, database, document_processor as dp, documents  # noqa: E402

# Master knowledge base: 13 real Albanian laws (Kuvendi i Shqipërisë). Each entry
# maps a file in data/corpus/ to the metadata shown in the UI and citations.
CORPUS = [
    {
        "filename": "ligj_152_2013_nenpunesi_civil.pdf",
        "title": "Ligji nr. 152/2013 “Për Nëpunësin Civil”",
        "year": 2013,
        "description": "Rregullon marrëdhënien e shërbimit civil dhe administrimin "
                       "e nëpunësve civilë në bazë të meritës dhe integritetit.",
    },
    {
        "filename": "ligj_44_2015_kodi_procedurave_administrative.pdf",
        "title": "Ligji nr. 44/2015 “Kodi i Procedurave Administrative i RSH”",
        "year": 2015,
        "description": "Rregullat e procesit të rregullt ligjor për nxjerrjen e "
                       "akteve administrative dhe ushtrimin e funksioneve publike.",
    },
    {
        "filename": "ligj_162_2020_prokurimi_publik.pdf",
        "title": "Ligji nr. 162/2020 “Për Prokurimin Publik”",
        "year": 2020,
        "description": "Procedurat e prokurimit nga autoritetet kontraktore për "
                       "kontratat publike dhe konkurset e projektimit.",
    },
    {
        "filename": "ligj_119_2014_e_drejta_e_informimit.pdf",
        "title": "Ligji nr. 119/2014 “Për të Drejtën e Informimit”",
        "year": 2014,
        "description": "E drejta e njohjes me informacionin që prodhohet ose mbahet "
                       "nga autoritetet publike.",
    },
    {
        "filename": "ligj_45_2015_dokumentet_ish_sigurimi.pdf",
        "title": "Ligji nr. 45/2015 “Për të Drejtën e Informimit për Dokumentet e "
                 "ish-Sigurimit të Shtetit”",
        "year": 2015,
        "description": "Procedurat për informimin mbi dokumentet e ish-Sigurimit të "
                       "Shtetit të RPSSH.",
    },
    {
        "filename": "ligj_10_2023_informacioni_klasifikuar.pdf",
        "title": "Ligji nr. 10/2023 “Për Informacionin e Klasifikuar”",
        "year": 2023,
        "description": "Parimet dhe rregullat për krijimin, administrimin dhe "
                       "mbrojtjen e informacionit të klasifikuar.",
    },
    {
        "filename": "ligj_9367_2005_konflikti_interesave.pdf",
        "title": "Ligji nr. 9367/2005 “Për Parandalimin e Konfliktit të "
                 "Interesave në Ushtrimin e Funksioneve Publike”",
        "year": 2005,
        "description": "Identifikimi, deklarimi dhe zgjidhja e konfliktit ndërmjet "
                       "interesave publikë dhe privatë të zyrtarëve.",
    },
    {
        "filename": "ligj_9154_2003_arkivat.pdf",
        "title": "Ligji nr. 9154/2003 “Për Arkivat”",
        "year": 2003,
        "description": "Organizimi i shërbimit arkivor dhe detyrimet për krijimin, "
                       "ruajtjen dhe shfrytëzimin e pasurisë arkivore.",
    },
    {
        "filename": "ligj_8480_1999_organet_kolegjiale.pdf",
        "title": "Ligji nr. 8480/1999 “Për Funksionimin e Organeve Kolegjiale të "
                 "Administratës Shtetërore dhe Enteve Publike”",
        "year": 1999,
        "description": "Rregullat për vendimmarrjen kolegjiale në administratën "
                       "shtetërore dhe entet publike.",
    },
    {
        "filename": "ligj_7514_1991_pafajesia_amnistia_rehabilitimi.pdf",
        "title": "Ligji nr. 7514/1991 “Për Pafajësinë, Amnistinë dhe "
                 "Rehabilitimin e ish të Dënuarve dhe të Përndjekurve Politikë”",
        "year": 1991,
        "description": "Njohja e pafajësisë dhe rehabilitimi i të dënuarve e të "
                       "përndjekurve politikë gjatë regjimit komunist.",
    },
    {
        "filename": "ligj_9936_2008_sistemi_buxhetor.pdf",
        "title": "Ligji nr. 9936/2008 “Për Menaxhimin e Sistemit Buxhetor në "
                 "Republikën e Shqipërisë”",
        "year": 2008,
        "description": "Struktura, parimet dhe bazat e procesit buxhetor dhe "
                       "marrëdhëniet financiare ndërqeveritare.",
    },
    {
        "filename": "ligj_10296_2010_menaxhimi_financiar_kontrolli.pdf",
        "title": "Ligji nr. 10296/2010 “Për Menaxhimin Financiar dhe Kontrollin”",
        "year": 2010,
        "description": "Parimet dhe procedurat e menaxhimit financiar e kontrollit "
                       "në njësitë e sektorit publik.",
    },
    {
        "filename": "ligj_115_2021_buxheti_2022.pdf",
        "title": "Ligji nr. 115/2021 “Për Buxhetin e Vitit 2022”",
        "year": 2021,
        "description": "Të ardhurat, shpenzimet dhe deficiti i buxhetit të shtetit "
                       "për vitin 2022.",
    },
]

INSTITUTION = "Kuvendi i Shqipërisë"
DOCUMENT_TYPE = "Ligj"


def main(reset: bool = False):
    database.init_schema()
    auth.ensure_default_admin()

    if reset:
        removed = documents.purge_all_documents(delete_files=True)
        print(f"  (reset) U hoqën {removed} dokumente ekzistuese.")

    added = 0
    for item in CORPUS:
        src = config.CORPUS_DIR / item["filename"]
        if not src.exists():
            print(f"  ! mungon te corpus/: {item['filename']}")
            continue
        if documents.get_document_by_filename(documents.safe_filename(item["filename"])):
            print(f"  (ekziston) {item['filename']}")
            continue
        try:
            _, n = documents.add_document(
                src, item["filename"], title=item["title"], institution=INSTITUTION,
                document_type=DOCUMENT_TYPE, year=item["year"],
                description=item["description"], uploaded_by="admin")
            print(f"  + {item['filename']} ({n} copëza)")
            added += 1
        except (dp.NoExtractableTextError, ValueError) as e:
            print(f"  ! {item['filename']}: {e}")
    print(f"Përfundoi. U shtuan {added} dokumente.")


if __name__ == "__main__":
    main(reset="--reset" in sys.argv)
