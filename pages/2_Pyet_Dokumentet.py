"""Employee page: ask questions over the active corpus (or one document), with
filtering, grounded citations, refusal, and Word export."""
import streamlit as st

import config
from modules import (audit, documents, export_docx, history, llm_client,
                     rag_pipeline as rag, ui)

user = ui.current_user()
st.subheader("❓ Pyet Dokumentet")

active = documents.list_documents(active_only=True)
if not active:
    st.info("Nuk ka dokumente aktive për t'u pyetur.")
    st.stop()

# --- Filtrim ---
with st.expander("🔎 Filtro dokumentet", expanded=False):
    f1, f2 = st.columns(2)
    f_type = f1.selectbox("Tipi", ["Të gjitha"] + config.DOCUMENT_TYPES)
    f_inst = f2.selectbox("Institucioni", ["Të gjitha"] + documents.distinct_values("institution"))
    f3, f4 = st.columns(2)
    years = documents.distinct_values("year")
    f_year = f3.selectbox("Viti", ["Të gjithë"] + [str(y) for y in years])
    f_kw = f4.text_input("Fjalë kyçe në titull")

filtered = documents.list_documents(
    active_only=True,
    doc_type=None if f_type == "Të gjitha" else f_type,
    institution=None if f_inst == "Të gjitha" else f_inst,
    year=None if f_year == "Të gjithë" else int(f_year),
    title_kw=f_kw or None,
)

# --- Zgjedhja e fushës së kërkimit ---
scope_options = {"Të gjithë dokumentet aktive (të filtruara)": None}
for d in filtered:
    scope_options[f"{d['title']} ({d['filename']})"] = d["id"]
scope_label = st.selectbox("Kërko në", list(scope_options.keys()))
selected_doc_id = scope_options[scope_label]

question = st.text_area("Shkruaj pyetjen tënde në shqip", height=100)

if st.button("Kërko përgjigje", type="primary") and question.strip():
    active_ids = [d["id"] for d in filtered]
    try:
        with st.spinner("Duke kërkuar dhe analizuar..."):
            ans = rag.answer_question(
                question.strip(), mode="rag",
                selected_document_id=selected_doc_id,
                active_doc_ids=None if selected_doc_id else active_ids)
    except llm_client.OllamaUnavailableError as e:
        st.error(str(e))
        st.stop()

    row_id = history.save(
        user["id"], user["username"], question.strip(), ans.text,
        mode="rag", selected_document_id=selected_doc_id, sources=ans.sources,
        response_time=ans.response_time)
    audit.log(user["id"], user["username"], "ask_question", question.strip()[:120])

    # Pre-generate the Word file once (only for non-refused answers).
    docx_bytes, docx_name = None, None
    if not ans.refused:
        path = export_docx.export_answer_to_docx(
            user["id"], user["username"], question.strip(), ans.text,
            ans.sources, ans.response_time)
        docx_name = path.replace("\\", "/").split("/")[-1]
        with open(path, "rb") as fh:
            docx_bytes = fh.read()

    st.session_state["last_qa"] = {
        "row_id": row_id, "question": question.strip(), "answer": ans.text,
        "refused": ans.refused, "sources": ans.sources,
        "response_time": ans.response_time, "top_score": ans.top_score,
        "docx_bytes": docx_bytes, "docx_name": docx_name,
    }

# --- Shfaqja e përgjigjes (persiston mes rerun-eve) ---
qa = st.session_state.get("last_qa")
if qa:
    st.divider()
    if qa["refused"]:
        st.warning(f"🛑 {qa['answer']}")
        st.caption(f"Ngjashmëria më e lartë: {qa['top_score']:.3f} "
                   f"(nën pragun {config.MIN_SIMILARITY}).")
    else:
        st.success(qa["answer"])
        st.caption(f"⏱️ {qa['response_time']}s")
        if qa["sources"]:
            st.markdown("**Burimet:**")
            for s in qa["sources"]:
                st.markdown(f"{s['n']}. `[{s['filename']}, {s['document_type']}, "
                            f"{s['institution']}, faqe {s['page']}]` — {s['fragment']}")
        if qa["docx_bytes"]:
            if st.download_button("📄 Shkarko përgjigjen në Word", qa["docx_bytes"],
                                  file_name=qa["docx_name"],
                                  mime="application/vnd.openxmlformats-officedocument."
                                  "wordprocessingml.document"):
                history.mark_exported(qa["row_id"])
                audit.log(user["id"], user["username"], "export_answer_docx",
                          qa["question"][:80])
