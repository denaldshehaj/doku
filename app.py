"""DOKU — Streamlit UI (Albanian). Role-gated: admin manages the corpus;
employees query/summarize/experiment read-only.

Run:  .venv\\Scripts\\streamlit run app.py
"""
import tempfile
from pathlib import Path

import streamlit as st

import doku  # noqa: F401  (sets sys.path)
import config
from doku import (audit, auth, db, documents, experiment, export, history,
                  ingestion, llm, rag)

st.set_page_config(page_title="DOKU", page_icon="📄", layout="wide")
db.init_db()


# --------------------------------------------------------------------------- #
# Authentication
# --------------------------------------------------------------------------- #
def login_view():
    st.title("📄 DOKU — Analizë Inteligjente e Dokumenteve")
    st.caption("Sistem lokal me RAG dhe model gjuhësor — pa shërbime cloud.")
    with st.form("login"):
        username = st.text_input("Përdoruesi")
        password = st.text_input("Fjalëkalimi", type="password")
        if st.form_submit_button("Hyr"):
            user = auth.authenticate(username, password)
            if user is None:
                audit.log(username or "?", "login_failed")
                st.error("Kredenciale të pasakta.")
            else:
                st.session_state.user = {"username": user["username"], "role": user["role"]}
                audit.log(user["username"], "login")
                st.rerun()


def current_user():
    return st.session_state.get("user")


def change_password_view():
    """Forced on first login when the account is flagged must_change_password."""
    user = current_user()
    st.title("🔐 Vendos një fjalëkalim të ri")
    st.info("Për arsye sigurie, duhet të ndryshosh fjalëkalimin e parazgjedhur "
            "para se të vazhdosh.")
    with st.form("chpw"):
        p1 = st.text_input("Fjalëkalimi i ri (min. 6 karaktere)", type="password")
        p2 = st.text_input("Përsërit fjalëkalimin", type="password")
        if st.form_submit_button("Ruaj"):
            if p1 != p2:
                st.error("Fjalëkalimet nuk përputhen.")
            else:
                try:
                    auth.set_password(user["username"], p1)
                    audit.log(user["username"], "password_change")
                    st.success("Fjalëkalimi u ndryshua. Po vazhdojmë...")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))


def require_admin() -> bool:
    """Server-side role guard (defense in depth, not just hidden UI)."""
    user = current_user()
    if not user or user["role"] != auth.ADMIN:
        st.error("Nuk keni leje për këtë veprim (vetëm administratori).")
        return False
    return True


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
def sidebar():
    user = current_user()
    st.sidebar.markdown(f"**Përdoruesi:** {user['username']}")
    st.sidebar.markdown(f"**Roli:** {user['role']}")
    st.sidebar.divider()

    online = llm.is_available()
    st.sidebar.markdown(f"**Modeli lokal:** {'🟢 aktiv' if online else '🔴 jo aktiv'}")
    if online:
        available = llm.list_models() or [config.LLM_MODEL]
        default = llm.get_active_model()
        idx = available.index(default) if default in available else 0
        chosen = st.sidebar.selectbox("Modeli i gjuhës", available, index=idx)
        llm.set_active_model(chosen)
    else:
        st.sidebar.warning("Ollama nuk po përgjigjet. Nis Ollama dhe shkarko modelin.")

    pages = ["Pyetje", "Përmbledhje", "Eksperimente", "Historiku im"]
    if user["role"] == auth.ADMIN:
        pages = ["Pyetje", "Përmbledhje", "Dokumentet", "Eksperimente",
                 "Përdoruesit", "Regjistri (audit)"]
    choice = st.sidebar.radio("Menyja", pages)
    st.sidebar.divider()
    if st.sidebar.button("Dil"):
        audit.log(user["username"], "logout")
        st.session_state.pop("user", None)
        st.rerun()
    return choice


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #
def render_answer(ans: rag.Answer):
    if ans.refused:
        st.warning(ans.text)
        if ans.retrieved:
            st.caption(f"Ngjashmëria më e lartë: {ans.top_score:.3f} "
                       f"(nën pragun {config.MIN_SIMILARITY}) → refuzim.")
        return
    st.success(ans.text)
    if ans.citations:
        with st.expander(f"Burimet e cituara ({len(ans.citations)})"):
            for c, chunk in zip(ans.citations, ans.retrieved):
                st.markdown(
                    f"**[{c['n']}]** {c['title']} — faqe {c['page']} "
                    f"· ngjashmëria {c['score']}"
                )
                st.caption(chunk.text)
                st.divider()


def doc_filter_widget():
    docs = documents.list_documents()
    options = {"Të gjitha dokumentet": None}
    for d in docs:
        options[f"{d['title']} ({d['filename']})"] = d["id"]
    label = st.selectbox("Filtro sipas dokumentit", list(options.keys()))
    doc_id = options[label]
    return {"doc_id": doc_id} if doc_id is not None else None


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def page_pyetje():
    st.header("Pyetje mbi dokumentet")
    if documents.list_documents() == []:
        st.info("Nuk ka dokumente të indeksuara ende.")
        return
    where = doc_filter_widget()
    question = st.text_area("Shkruaj pyetjen tënde", height=100)

    # Heuristikë: nëse hyrja duket si titull/temë e jo si pyetje, sugjero Përmbledhjen.
    q = question.strip()
    if q and "?" not in q and len(q.split()) <= 6:
        st.info("💡 Kjo duket si titull/temë. Për një përgjigje më të plotë, provo një "
                "pyetje konkrete (p.sh. *“Cili është objektivi i ...?”*) ose përdor "
                "skedën **Përmbledhje** për tërë dokumentin.")

    if st.button("Kërko përgjigje", type="primary") and question.strip():
        user = current_user()
        with st.spinner("Duke kërkuar dhe analizuar..."):
            ans = rag.answer_question(question, where=where)
        history.save(user["username"], question, ans.text, ans.refused, ans.citations)
        audit.log(user["username"], "query", question[:120])
        render_answer(ans)
        if not ans.refused:
            data = export.build_docx(f"Pyetje: {question[:60]}", ans.text, ans.citations)
            st.download_button("⬇️ Shkarko si Word", data,
                               file_name="pergjigje.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def page_permbledhje():
    st.header("Përmbledhje dokumenti")
    docs = documents.list_documents()
    if not docs:
        st.info("Nuk ka dokumente për t'u përmbledhur.")
        return
    options = {f"{d['title']} ({d['filename']})": d for d in docs}
    label = st.selectbox("Zgjidh dokumentin", list(options.keys()))
    fmt = st.selectbox("Formati", ["I shkurtër", "Pika kryesore", "Ekzekutive"])
    if st.button("Gjenero përmbledhjen", type="primary"):
        doc = options[label]
        pdf = config.DOCUMENTS_DIR / doc["filename"]
        if not pdf.exists():
            st.error("Skedari PDF mungon në disk.")
            return
        with st.spinner("Duke përmbledhur..."):
            text = "\n".join(ingestion.extract_pages(pdf))
            summary = rag.summarize(text, fmt=fmt)
        st.success(summary)
        audit.log(current_user()["username"], "summarize", doc["filename"])
        data = export.build_docx(f"Përmbledhje: {doc['title']}", summary)
        st.download_button("⬇️ Shkarko si Word", data,
                           file_name="permbledhje.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def page_dokumentet():
    if not require_admin():
        return
    st.header("Menaxhimi i dokumenteve (vetëm admin)")

    with st.expander("➕ Ngarko dokument të ri", expanded=False):
        uploaded = st.file_uploader("Skedar PDF", type=["pdf"])
        col1, col2 = st.columns(2)
        title = col1.text_input("Titulli")
        doc_type = col2.text_input("Lloji (ligj, rregullore, raport...)")
        institution = col1.text_input("Institucioni")
        year = col2.number_input("Viti", min_value=0, max_value=2100, value=0, step=1)
        if st.button("Ngarko dhe indekso", type="primary") and uploaded is not None:
            tmp = Path(tempfile.gettempdir()) / uploaded.name
            tmp.write_bytes(uploaded.getbuffer())
            try:
                with st.spinner("Duke nxjerrë tekstin dhe indeksuar..."):
                    doc_id, n = documents.add_document(
                        tmp, uploaded.name, title=title, doc_type=doc_type,
                        institution=institution, year=(year or None))
                audit.log(current_user()["username"], "doc_add",
                          f"{uploaded.name} ({n} copë)")
                st.success(f"U indeksua '{uploaded.name}' me {n} copëza.")
                st.rerun()
            except ingestion.NoExtractableTextError as e:
                st.error(str(e))
            except ValueError as e:
                st.error(str(e))

    st.subheader("Dokumentet ekzistuese")
    docs = documents.list_documents()
    if not docs:
        st.info("Asnjë dokument.")
        return
    for d in docs:
        with st.container(border=True):
            st.markdown(f"**{d['title']}** — `{d['filename']}`")
            st.caption(f"Lloji: {d['doc_type'] or '—'} · Institucioni: "
                       f"{d['institution'] or '—'} · Viti: {d['year'] or '—'} · "
                       f"{d['n_chunks']} copëza · {d['n_pages']} faqe")
            c1, c2, c3 = st.columns(3)
            if c1.button("🔄 Riindekso", key=f"re{d['id']}"):
                n = documents.reindex_document(d["id"])
                audit.log(current_user()["username"], "doc_reindex", d["filename"])
                st.success(f"U riindeksua ({n} copëza)."); st.rerun()
            if c2.button("🗑️ Fshi", key=f"del{d['id']}"):
                documents.delete_document(d["id"])
                audit.log(current_user()["username"], "doc_delete", d["filename"])
                st.warning("U fshi."); st.rerun()
            with c3.popover("✏️ Metadata"):
                nt = st.text_input("Titulli", value=d["title"] or "", key=f"t{d['id']}")
                ny = st.number_input("Viti", value=int(d["year"] or 0), key=f"y{d['id']}")
                if st.button("Ruaj", key=f"s{d['id']}"):
                    documents.update_metadata(d["id"], title=nt, year=(ny or None))
                    audit.log(current_user()["username"], "doc_meta", d["filename"])
                    st.success("U ruajt."); st.rerun()


def page_eksperimente():
    st.header("Eksperiment: RAG kundrejt LLM pa dokumente")
    st.caption("Krahaso përgjigjen e bazuar te dokumentet me përgjigjen e modelit "
               "pa qasje në dokumente.")
    question = st.text_area("Pyetja", height=80)
    if st.button("Krahaso", type="primary") and question.strip():
        with st.spinner("Duke ekzekutuar të dy variantet..."):
            res = experiment.run(current_user()["username"], question)
        audit.log(current_user()["username"], "experiment", question[:120])
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🟢 RAG (me dokumente)")
            (st.warning if res.rag_refused else st.success)(res.rag_answer)
            if res.citations:
                st.caption("Burime: " + ", ".join(
                    f"[{c['n']}] {c['title']} f.{c['page']}" for c in res.citations))
        with col2:
            st.subheader("🔴 LLM (pa dokumente)")
            st.info(res.norag_answer)
        st.caption("Vëre: RAG-u refuzon ose citon; modeli pa dokumente mund të "
                   "halucinojë.")


def page_historiku_im():
    st.header("Historiku im i pyetjeve")
    rows = history.recent(current_user()["username"], limit=50)
    if not rows:
        st.info("Ende pa pyetje.")
        return
    for r in rows:
        icon = "⛔" if r["refused"] else "✅"
        with st.expander(f"{icon} {r['question'][:80]} — {r['ts']}"):
            st.write(r["answer"])


def page_perdoruesit():
    if not require_admin():
        return
    st.header("Menaxhimi i përdoruesve (vetëm admin)")
    with st.expander("➕ Krijo përdorues të ri"):
        u = st.text_input("Përdoruesi i ri")
        p = st.text_input("Fjalëkalimi", type="password")
        r = st.selectbox("Roli", [auth.EMPLOYEE, auth.ADMIN])
        if st.button("Krijo"):
            try:
                auth.create_user(u, p, r)
                audit.log(current_user()["username"], "user_create", f"{u} ({r})")
                st.success(f"U krijua '{u}'."); st.rerun()
            except Exception as e:
                st.error(str(e))
    st.subheader("Përdoruesit")
    for row in auth.list_users():
        st.markdown(f"- **{row['username']}** · {row['role']} · {row['created_at']}")


def page_audit():
    if not require_admin():
        return
    st.header("Regjistri i veprimeve (audit)")
    rows = audit.recent(limit=300)
    st.dataframe(
        [{"Koha": r["ts"], "Përdoruesi": r["username"],
          "Veprimi": r["action"], "Detaje": r["detail"]} for r in rows],
        use_container_width=True,
    )


PAGES = {
    "Pyetje": page_pyetje,
    "Përmbledhje": page_permbledhje,
    "Dokumentet": page_dokumentet,
    "Eksperimente": page_eksperimente,
    "Përdoruesit": page_perdoruesit,
    "Regjistri (audit)": page_audit,
    "Historiku im": page_historiku_im,
}


def main():
    if current_user() is None:
        login_view()
        return
    if auth.needs_password_change(current_user()["username"]):
        change_password_view()
        return
    choice = sidebar()
    PAGES[choice]()


main()
