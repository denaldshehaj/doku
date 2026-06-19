"""Admin page: upload, edit metadata, activate/deactivate, delete, reindex one
or the whole corpus."""
import tempfile
from pathlib import Path

import streamlit as st

import config
from modules import audit, document_processor as dp, documents, ui

user = ui.require_admin()
st.subheader("📄 Menaxhimi i Dokumenteve")

# --- Ngarkim ---
with st.expander("➕ Ngarko dokument të ri", expanded=False):
    uploaded = st.file_uploader("Skedar PDF", type=["pdf"])
    c1, c2 = st.columns(2)
    title = c1.text_input("Titulli")
    institution = c2.text_input("Institucioni burimor")
    c3, c4 = st.columns(2)
    document_type = c3.selectbox("Tipi i dokumentit", config.DOCUMENT_TYPES)
    year = c4.number_input("Viti", min_value=0, max_value=2100, value=0, step=1)
    description = st.text_area("Përshkrim i shkurtër", height=70)
    if st.button("Ngarko dhe indekso", type="primary") and uploaded is not None:
        tmp = Path(tempfile.gettempdir()) / uploaded.name
        tmp.write_bytes(uploaded.getbuffer())
        try:
            with st.spinner("Duke nxjerrë tekstin dhe indeksuar..."):
                doc_id, n = documents.add_document(
                    tmp, uploaded.name, title=title, institution=institution,
                    document_type=document_type, year=(year or None),
                    description=description, uploaded_by=user["username"])
            audit.log(user["id"], user["username"], "upload_document",
                      f"{uploaded.name} ({n} copëza)")
            st.success(f"U indeksua '{uploaded.name}' me {n} copëza.")
            st.rerun()
        except dp.NoExtractableTextError as e:
            st.error(str(e))
        except ValueError as e:
            st.error(str(e))

# --- Riindeksim i tërë korpusit ---
col_a, col_b = st.columns([3, 1])
col_a.markdown("##### Dokumentet ekzistuese")
if col_b.button("🔁 Riindekso korpusin"):
    with st.spinner("Duke riindeksuar të gjithë korpusin..."):
        total = documents.reindex_all()
    audit.log(user["id"], user["username"], "reindex_all_documents", f"{total} copëza")
    st.success(f"U riindeksua korpusi ({total} copëza)."); st.rerun()

docs = documents.list_documents()
if not docs:
    st.info("Asnjë dokument.")
    st.stop()

for d in docs:
    with st.container(border=True):
        badge = "🟢 aktiv" if d["status"] == config.STATUS_ACTIVE else "⚪ joaktiv"
        st.markdown(f"**{d['title']}** — `{d['filename']}` · {badge}")
        st.caption(f"Tipi: {d['document_type'] or '—'} · Institucioni: "
                   f"{d['institution'] or '—'} · Viti: {d['year'] or '—'} · "
                   f"{d['total_chunks']} copëza · {d['num_pages']} faqe")
        if d["description"]:
            st.caption(f"📝 {d['description']}")

        c1, c2, c3, c4 = st.columns(4)
        # Aktivizo / çaktivizo
        if d["status"] == config.STATUS_ACTIVE:
            if c1.button("⚪ Çaktivizo", key=f"deact{d['id']}"):
                documents.set_status(d["id"], config.STATUS_INACTIVE)
                audit.log(user["id"], user["username"], "deactivate_document", d["filename"])
                st.rerun()
        else:
            if c1.button("🟢 Aktivizo", key=f"act{d['id']}"):
                documents.set_status(d["id"], config.STATUS_ACTIVE)
                audit.log(user["id"], user["username"], "activate_document", d["filename"])
                st.rerun()
        if c2.button("🔄 Riindekso", key=f"re{d['id']}"):
            n = documents.reindex_document(d["id"])
            audit.log(user["id"], user["username"], "reindex_document", d["filename"])
            st.success(f"Riindeksuar ({n})."); st.rerun()
        if c3.button("🗑️ Fshi", key=f"del{d['id']}"):
            documents.delete_document(d["id"])
            audit.log(user["id"], user["username"], "delete_document", d["filename"])
            st.rerun()
        with c4.popover("✏️ Metadata"):
            nt = st.text_input("Titulli", value=d["title"] or "", key=f"t{d['id']}")
            ni = st.text_input("Institucioni", value=d["institution"] or "", key=f"i{d['id']}")
            ntype = st.selectbox("Tipi", config.DOCUMENT_TYPES, key=f"ty{d['id']}",
                                 index=config.DOCUMENT_TYPES.index(d["document_type"])
                                 if d["document_type"] in config.DOCUMENT_TYPES else 0)
            ny = st.number_input("Viti", value=int(d["year"] or 0), key=f"y{d['id']}")
            nd = st.text_area("Përshkrim", value=d["description"] or "", key=f"d{d['id']}")
            if st.button("Ruaj", key=f"save{d['id']}"):
                documents.update_metadata(d["id"], title=nt, institution=ni,
                                          document_type=ntype, year=(ny or None),
                                          description=nd)
                audit.log(user["id"], user["username"], "update_document_metadata",
                          d["filename"])
                st.success("U ruajt."); st.rerun()
