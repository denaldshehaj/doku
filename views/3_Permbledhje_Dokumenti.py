"""Employee page: generate a structured Albanian summary of a chosen document,
with a verification note and Word export."""
from pathlib import Path

import streamlit as st

from modules import (audit, document_processor as dp, documents, export_docx,
                     history, llm_client, rag_pipeline as rag, ui)

user = ui.current_user()
st.subheader("📝 Përmbledhje Dokumenti")

active = documents.list_documents(active_only=True)
if not active:
    st.info("Nuk ka dokumente aktive për t'u përmbledhur.")
    st.stop()

options = {f"{d['title']} ({d['filename']})": d for d in active}
label = st.selectbox("Zgjidh dokumentin", list(options.keys()))
fmt = st.selectbox("Formati", list(rag.SUMMARY_FORMATS.keys()))

if st.button("Gjenero përmbledhjen", type="primary"):
    doc = options[label]
    pdf = Path(doc["stored_path"])
    if not pdf.exists():
        st.error("Skedari PDF mungon në disk.")
        st.stop()
    try:
        with st.spinner("Duke përmbledhur..."):
            text = dp.extract_text(pdf)
            summary = rag.summarize(text, fmt=fmt)
    except llm_client.OllamaUnavailableError as e:
        st.error(str(e))
        st.stop()

    history.save(user["id"], user["username"], f"[Përmbledhje: {doc['title']}]",
                 summary, mode="summary", selected_document_id=doc["id"])
    audit.log(user["id"], user["username"], "generate_summary", doc["filename"])

    meta = {k: doc[k] for k in ("id", "title", "filename", "institution",
                                "document_type", "year")}
    path = export_docx.export_summary_to_docx(meta, summary, fmt)
    with open(path, "rb") as fh:
        docx_bytes = fh.read()
    st.session_state["last_summary"] = {
        "title": doc["title"], "fmt": fmt, "summary": summary,
        "docx_bytes": docx_bytes, "docx_name": path.replace("\\", "/").split("/")[-1],
        "filename": doc["filename"],
    }

s = st.session_state.get("last_summary")
if s:
    st.divider()
    st.markdown(f"**{s['title']}** — _{s['fmt']}_")
    st.success(s["summary"])
    st.info("⚠️ Kjo përmbledhje është gjeneruar automatikisht dhe duhet verifikuar "
            "me dokumentin origjinal.")
    if st.download_button("📄 Shkarko përmbledhjen në Word", s["docx_bytes"],
                          file_name=s["docx_name"],
                          mime="application/vnd.openxmlformats-officedocument."
                          "wordprocessingml.document"):
        audit.log(user["id"], user["username"], "export_summary_docx", s["filename"])
