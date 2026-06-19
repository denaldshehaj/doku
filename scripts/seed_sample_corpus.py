"""Generate a small Albanian institutional sample corpus (PDFs with full metadata)
and index it, so the system is demoable out of the box. Idempotent.

Run:  .venv\\Scripts\\python.exe scripts\\seed_sample_corpus.py
"""
import os
import sys
import tempfile
from pathlib import Path

import fitz  # PyMuPDF

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import auth, database, document_processor as dp, documents  # noqa: E402

CORPUS = [
    {
        "filename": "ligj_tatimor_2023.pdf",
        "title": "Ligji për Procedurat Tatimore",
        "institution": "Ministria e Financave", "document_type": "Ligj", "year": 2023,
        "description": "Procedurat e deklarimit dhe pagesës së detyrimeve tatimore.",
        "paragraphs": [
            "Neni 1. Çdo tatimpagues është i detyruar të paraqesë deklaratën tatimore "
            "vjetore brenda datës 31 mars të vitit pasardhës.",
            "Neni 2. Mospagimi i detyrimeve tatimore brenda afatit ligjor sjell gjoba "
            "administrative si dhe kamatëvonesa të llogaritura mbi shumën e papaguar.",
            "Neni 3. Tatimpaguesi ka të drejtë të ankohet pranë Drejtorisë së Apelimit "
            "Tatimor brenda 30 ditëve nga njoftimi i vlerësimit.",
        ],
    },
    {
        "filename": "rregullore_punes_2022.pdf",
        "title": "Rregullore për Marrëdhëniet e Punës",
        "institution": "Ministria e Ekonomisë", "document_type": "Rregullore", "year": 2022,
        "description": "Rregulla për oraret, pushimet dhe kontratat e punës.",
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
        "institution": "AKSHI", "document_type": "Strategji", "year": 2021,
        "description": "Objektivat kombëtare për dixhitalizimin e shërbimeve publike.",
        "paragraphs": [
            "Strategjia synon ofrimin e të paktën 90 për qind të shërbimeve publike "
            "online deri në vitin 2030.",
            "Objektiv kryesor është reduktimi i barrës administrative për qytetarët dhe "
            "bizneset përmes dixhitalizimit të procedurave.",
            "Investimet do të përqendrohen në infrastrukturën e të dhënave, sigurinë "
            "kibernetike dhe aftësimin dixhital të nëpunësve publikë.",
        ],
    },
    {
        "filename": "vkm_paga_minimale_2024.pdf",
        "title": "VKM për Pagën Minimale Mujore",
        "institution": "Këshilli i Ministrave", "document_type": "VKM", "year": 2024,
        "description": "Përcaktimi i pagës minimale mujore në shkallë vendi.",
        "paragraphs": [
            "Paga minimale mujore në shkallë vendi caktohet në vlerën 40000 lekë, e "
            "vlefshme nga data 1 prill 2024.",
            "Paga minimale zbatohet për të gjithë punonjësit me kohë të plotë pune prej "
            "174 orësh në muaj.",
            "Subjektet private dhe institucionet publike janë të detyruara të zbatojnë "
            "pagën minimale; mospërmbushja ndëshkohet me gjobë.",
        ],
    },
    {
        "filename": "ligj_arsimi_parauniversitar_2021.pdf",
        "title": "Ligji për Arsimin Parauniversitar",
        "institution": "Ministria e Arsimit dhe Sportit", "document_type": "Ligj", "year": 2021,
        "description": "Organizimi i arsimit parauniversitar dhe detyrimi shkollor.",
        "paragraphs": [
            "Arsimi i detyrueshëm përfshin arsimin fillor dhe atë të mesëm të ulët dhe "
            "është i detyrueshëm deri në moshën 16 vjeç.",
            "Viti shkollor fillon në muajin shtator dhe përmban jo më pak se 175 ditë "
            "mësimore.",
            "Mësimi në institucionet publike të arsimit parauniversitar është falas për "
            "të gjithë nxënësit.",
        ],
    },
    {
        "filename": "udhezim_prokurimi_publik_2022.pdf",
        "title": "Udhëzim për Procedurat e Prokurimit Publik",
        "institution": "Agjencia e Prokurimit Publik", "document_type": "Udhëzim", "year": 2022,
        "description": "Rregulla për procedurat dhe pragjet e prokurimit publik.",
        "paragraphs": [
            "Prokurimet me vlerë mbi pragun prej 1.2 milionë lekësh realizohen përmes "
            "procedurës së hapur dhe publikohen në sistemin elektronik të prokurimeve.",
            "Operatorët ekonomikë kanë të drejtë të paraqesin ankesë pranë autoritetit "
            "kontraktor brenda 7 ditëve nga njoftimi i fituesit.",
            "Çdo procedurë prokurimi duhet të respektojë parimet e transparencës, "
            "barazisë dhe mosdiskriminimit të operatorëve.",
        ],
    },
    {
        "filename": "strategjia_siguria_kombetare_2030.pdf",
        "title": "Strategjia e Sigurisë Kombëtare",
        "institution": "Ministria e Mbrojtjes", "document_type": "Strategji", "year": 2022,
        "description": "Objektivat strategjikë për sigurinë dhe mbrojtjen kombëtare.",
        "paragraphs": [
            "Strategjia synon forcimin e kapaciteteve mbrojtëse dhe ndërveprimin me "
            "aleatët e NATO-s deri në vitin 2030.",
            "Prioritet i veçantë i jepet sigurisë kibernetike dhe mbrojtjes së "
            "infrastrukturës kritike kombëtare.",
            "Buxheti i mbrojtjes synohet të mbahet në nivelin prej 2 për qind të "
            "Prodhimit të Brendshëm Bruto.",
        ],
    },
    {
        "filename": "rregullore_mbrojtja_civile_2020.pdf",
        "title": "Rregullore për Mbrojtjen Civile dhe Emergjencat",
        "institution": "Ministria e Mbrojtjes", "document_type": "Rregullore", "year": 2020,
        "description": "Masat dhe procedurat në rast emergjencash civile.",
        "paragraphs": [
            "Në rast fatkeqësie natyrore, organet vendore aktivizojnë planin e "
            "emergjencës civile brenda 24 orëve.",
            "Evakuimi i popullatës nga zonat e rrezikuara koordinohet nga komiteti i "
            "emergjencave civile në bashkëpunim me Forcat e Armatosura.",
            "Çdo institucion publik është i detyruar të hartojë planin e vet të "
            "vazhdimësisë së punës në situata emergjence.",
        ],
    },
    {
        "filename": "ligj_sherbimi_ushtarak_2018.pdf",
        "title": "Ligji për Shërbimin në Forcat e Armatosura",
        "institution": "Ministria e Mbrojtjes", "document_type": "Ligj", "year": 2018,
        "description": "Kushtet e shërbimit në Forcat e Armatosura.",
        "paragraphs": [
            "Në shërbimin aktiv ushtarak pranohen shtetas shqiptarë të moshës 18 deri "
            "në 30 vjeç që plotësojnë kriteret shëndetësore dhe arsimore.",
            "Kontrata e parë e shërbimit ushtarak aktiv lidhet për një periudhë prej 4 "
            "vjetësh, me mundësi rinovimi.",
            "Ushtaraku ka të drejtën e trajnimit profesional, pagës mujore dhe lejes "
            "vjetore sipas legjislacionit ushtarak.",
        ],
    },
    {
        "filename": "raport_buxheti_vjetor_2022.pdf",
        "title": "Raporti Vjetor i Zbatimit të Buxhetit",
        "institution": "Ministria e Financave", "document_type": "Raport", "year": 2023,
        "description": "Pasqyra e të ardhurave dhe shpenzimeve buxhetore për vitin 2022.",
        "paragraphs": [
            "Të ardhurat totale buxhetore për vitin 2022 arritën në 580 miliardë lekë, "
            "ose 98 për qind të planit vjetor.",
            "Shpenzimet kapitale për investime publike përbënë 22 për qind të "
            "shpenzimeve totale të buxhetit.",
            "Deficiti buxhetor u mbajt brenda nivelit të planifikuar prej 3.5 për qind "
            "të Prodhimit të Brendshëm Bruto.",
        ],
    },
    {
        "filename": "vkm_transport_publik_2023.pdf",
        "title": "VKM për Transportin Publik Rrugor",
        "institution": "Ministria e Infrastrukturës", "document_type": "VKM", "year": 2023,
        "description": "Rregulla për licencimin dhe tarifat e transportit publik.",
        "paragraphs": [
            "Licenca për transport publik rrugor të udhëtarëve lëshohet për një afat prej "
            "5 vjetësh dhe rinovohet me kërkesë të operatorit.",
            "Tarifat e transportit publik miratohen nga njësia e vetëqeverisjes vendore "
            "dhe afishohen në çdo mjet transporti.",
            "Operatorët janë të detyruar të sigurojnë akses për personat me aftësi të "
            "kufizuara në mjetet e transportit publik.",
        ],
    },
    {
        "filename": "udhezim_nenshkrimi_elektronik_2024.pdf",
        "title": "Udhëzim për Nënshkrimin Elektronik",
        "institution": "AKSHI", "document_type": "Udhëzim", "year": 2024,
        "description": "Përdorimi dhe vlefshmëria e nënshkrimit elektronik.",
        "paragraphs": [
            "Nënshkrimi elektronik i kualifikuar ka të njëjtën vlerë ligjore si "
            "nënshkrimi i shkruar me dorë.",
            "Dokumentet zyrtare të institucioneve publike mund të nënshkruhen "
            "elektronikisht dhe ruhen në format dixhital.",
            "Certifikata e nënshkrimit elektronik ka një afat vlefshmërie prej 3 vjetësh "
            "dhe duhet rinovuar para skadimit.",
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
    database.init_schema()
    auth.ensure_default_admin()
    tmp = Path(tempfile.gettempdir())
    added = 0
    for item in CORPUS:
        if documents.get_document_by_filename(documents.safe_filename(item["filename"])):
            print(f"  (ekziston) {item['filename']}")
            continue
        pdf = tmp / item["filename"]
        make_pdf(pdf, item["title"], item["paragraphs"])
        try:
            _, n = documents.add_document(
                pdf, item["filename"], title=item["title"],
                institution=item["institution"], document_type=item["document_type"],
                year=item["year"], description=item["description"], uploaded_by="admin")
            print(f"  + {item['filename']} ({n} copëza)")
            added += 1
        except (dp.NoExtractableTextError, ValueError) as e:
            print(f"  ! {item['filename']}: {e}")
    print(f"Përfundoi. U shtuan {added} dokumente.")


if __name__ == "__main__":
    main()
