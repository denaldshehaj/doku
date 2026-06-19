"""DOKU — Streamlit UI (Albanian). Registration + role-gated app: admin manages
the corpus; employees query/summarize/experiment read-only.

Run:  .venv\\Scripts\\streamlit run app.py
"""
import tempfile
from pathlib import Path

import streamlit as st

import doku  # noqa: F401  (sets sys.path)
import config
from doku import (audit, auth, db, documents, experiment, export, history,
                  ingestion, llm, rag, vectorstore)

st.set_page_config(page_title="DOKU", page_icon="📄", layout="wide")
db.init_db()

ROLE_LABELS = {auth.ADMIN: "Administrator", auth.EMPLOYEE: "Punonjës"}


def inject_css():
    # Theme-neutral styling only: no hardcoded colors, so Streamlit's built-in
    # Light/Dark theme switcher (☰ → Settings → Theme) keeps working.
    st.markdown(
        """
        <style>
          .stButton>button, .stDownloadButton>button {border-radius: 8px;}
          div[data-testid="stMetric"] {
              border: 1px solid rgba(128,128,128,0.25);
              border-radius: 12px; padding: 14px 16px;
          }
          .doku-badge {
              border: 1px solid rgba(128,128,128,0.30);
              border-radius: 10px; padding: 10px 12px; font-size: 0.9rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def current_user():
    return st.session_state.get("user")


# --------------------------------------------------------------------------- #
# Authentication (login + registration)
# --------------------------------------------------------------------------- #
def _login_form():
    with st.form("login"):
        username = st.text_input("Përdoruesi")
        password = st.text_input("Fjalëkalimi", type="password")
        if st.form_submit_button("Hyr", type="primary", use_container_width=True):
            user = auth.authenticate(username, password)
            if user is None:
                audit.log(username or "?", "login_failed")
                st.error("Kredenciale të pasakta.")
            else:
                st.session_state.user = {"username": user["username"], "role": user["role"]}
                audit.log(user["username"], "login")
                st.rerun()


def _register_form():
    with st.form("register"):
        username = st.text_input("Përdoruesi i ri", help="3–32 karaktere: shkronja, numra, '_' ose '.'")
        p1 = st.text_input("Fjalëkalimi", type="password", help="Të paktën 6 karaktere.")
        p2 = st.text_input("Përsërit fjalëkalimin", type="password")
        if st.form_submit_button("Regjistrohu", type="primary", use_container_width=True):
            try:
                role = auth.register(username, p1, p2)
                audit.log(username.strip(), "register", f"role={role}")
                st.session_state.user = {"username": username.strip(), "role": role}
                st.success(f"Llogaria u krijua si {ROLE_LABELS[role]}. Po hyjmë...")
                st.rerun()
            except ValueError as e:
                st.error(str(e))


def auth_view():
    st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.markdown("<h1 style='text-align:center;margin-bottom:0'>📄 DOKU</h1>",
                    unsafe_allow_html=True)
        st.markdown(
            "<p style='text-align:center;color:#8b94a3'>Analizë inteligjente e "
            "dokumenteve — RAG lokal, pa shërbime cloud.</p>",
            unsafe_allow_html=True,
        )
        if not auth.has_admin():
            st.info("👋 Mirë se erdhe! Nuk ka ende llogari. **Regjistrimi i parë "
                    "krijon administratorin** e sistemit.")
        tab_login, tab_register = st.tabs(["🔑 Hyr", "📝 Regjistrohu"])
        with tab_login:
            _login_form()
        with tab_register:
            _register_form()


def change_password_view():
    """Forced when an account is flagged must_change_password."""
    user = current_user()
    st.title("🔐 Vendos një fjalëkalim të ri")
    st.info("Për arsye sigurie, duhet të ndryshosh fjalëkalimin para se të vazhdosh.")
    with st.form("chpw"):
        p1 = st.text_input("Fjalëkalimi i ri (min. 6 karaktere)", type="password")
        p2 = st.text_input("Përsërit fjalëkalimin", type="password")
        if st.form_submit_button("Ruaj", type="primary"):
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
# Sidebar / navigation
# --------------------------------------------------------------------------- #
NAV_EMPLOYEE = ["🏠 Paneli", "❓ Pyetje", "📝 Përmbledhje", "🧪 Eksperimente", "🕘 Historiku im"]
NAV_ADMIN = ["🏠 Paneli", "❓ Pyetje", "📝 Përmbledhje", "📄 Dokumentet",
             "🧪 Eksperimente", "👥 Përdoruesit", "📋 Regjistri (audit)"]


def sidebar():
    user = current_user()
    st.sidebar.markdown("## 📄 DOKU")
    st.sidebar.markdown(
        f"<div class='doku-badge'>👤 <b>{user['username']}</b><br>"
        f"<span style='color:#8b94a3'>{ROLE_LABELS.get(user['role'], user['role'])}</span></div>",
        unsafe_allow_html=True,
    )
    st.sidebar.write("")

    online = llm.is_available()
    st.sidebar.caption(f"Modeli lokal: {'🟢 aktiv' if online else '🔴 jo aktiv'}")
    if online:
        available = llm.list_models() or [config.LLM_MODEL]
        default = llm.get_active_model()
        idx = available.index(default) if default in available else 0
        llm.set_active_model(st.sidebar.selectbox("Modeli i gjuhës", available, index=idx))
    else:
        st.sidebar.warning("Ollama nuk po përgjigjet.")

    st.sidebar.divider()
    nav = NAV_ADMIN if user["role"] == auth.ADMIN else NAV_EMPLOYEE
    choice = st.sidebar.radio("Menyja", nav, label_visibility="collapsed")
    st.sidebar.divider()
    if st.sidebar.button("🚪 Dil", use_container_width=True):
        audit.log(user["username"], "logout")
        st.session_state.pop("user", None)
        st.rerun()
    return choice


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #
def render_answer(ans: rag.Answer):
    if ans.refused:
        st.warning(f"🛑 {ans.text}")
        if ans.retrieved:
            st.caption(f"Ngjashmëria më e lartë: {ans.top_score:.3f} "
                       f"(nën pragun {config.MIN_SIMILARITY}) → refuzim.")
        return
    st.success(ans.text)
    if ans.citations:
        with st.expander(f"📚 Burimet e cituara ({len(ans.citations)})"):
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


def _docx_download(label, title, body, citations=None, fname="dokument.docx"):
    data = export.build_docx(title, body, citations)
    st.download_button(
        label, data, file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def page_dashboard():
    user = current_user()
    st.subheader(f"Mirë se erdhe, {user['username']} 👋")
    docs = documents.list_documents()
    my_q = len(history.recent(user["username"], limit=100000))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📄 Dokumente", len(docs))
    c2.metric("🧩 Copëza (indeks)", vectorstore.count())
    c3.metric("❓ Pyetjet e mia", my_q)
    if user["role"] == auth.ADMIN:
        c4.metric("👥 Përdorues", auth.user_count())
    else:
        c4.metric("🤖 Modeli", llm.get_active_model())

    st.divider()
    st.markdown("#### Çfarë mund të bësh")
    a, b, c = st.columns(3)
    a.markdown("**❓ Pyetje**\n\nBëj pyetje mbi korpusin; përgjigje me citime ose refuzim.")
    b.markdown("**📝 Përmbledhje**\n\nPërmbledh një dokument në formate të ndryshme.")
    c.markdown("**🧪 Eksperimente**\n\nKrahaso RAG-un me modelin pa dokumente.")

    if not docs and user["role"] == auth.ADMIN:
        st.warning("Nuk ka ende dokumente. Shko te **📄 Dokumentet** për të ngarkuar PDF.")


def page_pyetje():
    st.subheader("❓ Pyetje mbi dokumentet")
    if not documents.list_documents():
        st.info("Nuk ka dokumente të indeksuara ende.")
        return
    where = doc_filter_widget()

    st.caption("Shembuj të shpejtë:")
    examples = [
        "Sa ditë pushim vjetor ka punonjësi?",
        "Kur duhet të dorëzohet deklarata tatimore?",
        "Cili është objektivi i strategjisë dixhitale?",
    ]
    ex_cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        if ex_cols[i].button(ex, key=f"ex{i}", use_container_width=True):
            st.session_state["pyetje_input"] = ex

    question = st.text_area("Shkruaj pyetjen tënde", key="pyetje_input", height=100)

    q = (question or "").strip()
    if q and "?" not in q and len(q.split()) <= 6:
        st.info("💡 Kjo duket si titull/temë. Provo një pyetje konkrete ose përdor "
                "skedën **📝 Përmbledhje** për tërë dokumentin.")

    if st.button("Kërko përgjigje", type="primary") and q:
        user = current_user()
        with st.spinner("Duke kërkuar dhe analizuar..."):
            ans = rag.answer_question(q, where=where)
        history.save(user["username"], q, ans.text, ans.refused, ans.citations)
        audit.log(user["username"], "query", q[:120])
        render_answer(ans)
        if not ans.refused:
            _docx_download("⬇️ Shkarko si Word", f"Pyetje: {q[:60]}", ans.text,
                           ans.citations, "pergjigje.docx")


def page_permbledhje():
    st.subheader("📝 Përmbledhje dokumenti")
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
        _docx_download("⬇️ Shkarko si Word", f"Përmbledhje: {doc['title']}", summary,
                       None, "permbledhje.docx")


def page_dokumentet():
    if not require_admin():
        return
    st.subheader("📄 Menaxhimi i dokumenteve")

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
                    _, n = documents.add_document(
                        tmp, uploaded.name, title=title, doc_type=doc_type,
                        institution=institution, year=(year or None))
                audit.log(current_user()["username"], "doc_add", f"{uploaded.name} ({n} copë)")
                st.success(f"U indeksua '{uploaded.name}' me {n} copëza.")
                st.rerun()
            except (ingestion.NoExtractableTextError, ValueError) as e:
                st.error(str(e))

    st.markdown("##### Dokumentet ekzistuese")
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
    st.subheader("🧪 Eksperiment: RAG kundrejt LLM pa dokumente")
    st.caption("Krahaso përgjigjen e bazuar te dokumentet me përgjigjen e modelit pa "
               "qasje në dokumente.")
    question = st.text_area("Pyetja", height=80)
    if st.button("Krahaso", type="primary") and question.strip():
        with st.spinner("Duke ekzekutuar të dy variantet..."):
            res = experiment.run(current_user()["username"], question)
        audit.log(current_user()["username"], "experiment", question[:120])
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### 🟢 RAG (me dokumente)")
            (st.warning if res.rag_refused else st.success)(res.rag_answer)
            if res.citations:
                st.caption("Burime: " + ", ".join(
                    f"[{c['n']}] {c['title']} f.{c['page']}" for c in res.citations))
        with col2:
            st.markdown("##### 🔴 LLM (pa dokumente)")
            st.info(res.norag_answer)
        st.caption("Vëre: RAG-u refuzon ose citon; modeli pa dokumente mund të halucinojë.")


def page_historiku_im():
    st.subheader("🕘 Historiku im i pyetjeve")
    rows = history.recent(current_user()["username"], limit=50)
    if not rows:
        st.info("Ende pa pyetje.")
        return
    for r in rows:
        icon = "🛑" if r["refused"] else "✅"
        with st.expander(f"{icon} {r['question'][:80]} — {r['ts']}"):
            st.write(r["answer"])


def page_perdoruesit():
    if not require_admin():
        return
    st.subheader("👥 Menaxhimi i përdoruesve")
    with st.expander("➕ Krijo përdorues të ri"):
        u = st.text_input("Përdoruesi i ri")
        p = st.text_input("Fjalëkalimi", type="password")
        r = st.selectbox("Roli", [auth.EMPLOYEE, auth.ADMIN],
                         format_func=lambda x: ROLE_LABELS[x])
        if st.button("Krijo"):
            try:
                auth.create_user(u, p, r, must_change=True)
                audit.log(current_user()["username"], "user_create", f"{u} ({r})")
                st.success(f"U krijua '{u}'. Do të ndryshojë fjalëkalimin në hyrjen e parë.")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    st.markdown("##### Përdoruesit")
    for row in auth.list_users():
        st.markdown(f"- **{row['username']}** · {ROLE_LABELS.get(row['role'], row['role'])} "
                    f"· {row['created_at']}")


def page_audit():
    if not require_admin():
        return
    st.subheader("📋 Regjistri i veprimeve (audit)")
    rows = audit.recent(limit=300)
    st.dataframe(
        [{"Koha": r["ts"], "Përdoruesi": r["username"],
          "Veprimi": r["action"], "Detaje": r["detail"]} for r in rows],
        use_container_width=True,
    )


PAGES = {
    "🏠 Paneli": page_dashboard,
    "❓ Pyetje": page_pyetje,
    "📝 Përmbledhje": page_permbledhje,
    "📄 Dokumentet": page_dokumentet,
    "🧪 Eksperimente": page_eksperimente,
    "👥 Përdoruesit": page_perdoruesit,
    "📋 Regjistri (audit)": page_audit,
    "🕘 Historiku im": page_historiku_im,
}


def main():
    inject_css()
    if current_user() is None:
        auth_view()
        return
    if auth.needs_password_change(current_user()["username"]):
        change_password_view()
        return
    choice = sidebar()
    PAGES[choice]()


main()
