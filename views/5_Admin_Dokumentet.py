"""Admin page: upload, edit metadata, activate/deactivate, delete, reindex one
or the whole corpus."""
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

import config
from modules import audit, document_processor as dp, documents, ui

user = ui.require_admin()
st.subheader("📄 Menaxhimi i Dokumenteve")

# --- Ngarkim ---
with st.expander("➕ Ngarko dokument të ri", expanded=False):
    uploaded = st.file_uploader("Skedar (PDF ose Word)", type=config.UPLOAD_TYPES)
    c1, c2 = st.columns(2)
    title = c1.text_input("Titulli")
    institution = c2.selectbox("Institucioni burimor", config.INSTITUTIONS)
    c3, c4 = st.columns(2)
    document_type = c3.selectbox("Tipi i dokumentit", config.DOCUMENT_TYPES)
    year_date = c4.date_input("Viti", value=date(date.today().year, 1, 1),
                              min_value=date(1990, 1, 1), max_value=date(2100, 12, 31),
                              format="YYYY-MM-DD")
    year = year_date.year
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
            inst_opts = (config.INSTITUTIONS if (not d["institution"] or
                         d["institution"] in config.INSTITUTIONS)
                         else [d["institution"]] + config.INSTITUTIONS)
            ni = st.selectbox("Institucioni", inst_opts, key=f"i{d['id']}",
                              index=inst_opts.index(d["institution"])
                              if d["institution"] in inst_opts else 0)
            ntype = st.selectbox("Tipi", config.DOCUMENT_TYPES, key=f"ty{d['id']}",
                                 index=config.DOCUMENT_TYPES.index(d["document_type"])
                                 if d["document_type"] in config.DOCUMENT_TYPES else 0)
            cur_year = int(d["year"]) if d["year"] else date.today().year
            ny_date = st.date_input("Viti", value=date(cur_year, 1, 1),
                                    min_value=date(1990, 1, 1), max_value=date(2100, 12, 31),
                                    format="YYYY-MM-DD", key=f"y{d['id']}")
            ny = ny_date.year
            nd = st.text_area("Përshkrim", value=d["description"] or "", key=f"d{d['id']}")
            if st.button("Ruaj", key=f"save{d['id']}"):
                documents.update_metadata(d["id"], title=nt, institution=ni,
                                          document_type=ntype, year=(ny or None),
                                          description=nd)
                audit.log(user["id"], user["username"], "update_document_metadata",
                          d["filename"])
                st.success("U ruajt."); st.rerun()

        with st.expander("👁️ Parapamje / Shkarko"):
            path = Path(d["stored_path"]) if d["stored_path"] else None
            if not path or not path.exists():
                st.warning("Skedari mungon në disk.")
            else:
                is_pdf = d["filename"].lower().endswith(".pdf")
                mime = ("application/pdf" if is_pdf else
                        "application/vnd.openxmlformats-officedocument."
                        "wordprocessingml.document")
                with open(path, "rb") as fh:
                    st.download_button("⬇️ Shkarko dokumentin", fh.read(),
                                       file_name=d["filename"], mime=mime,
                                       key=f"dl{d['id']}")
                if is_pdf:
                    # Render at a higher zoom for sharpness, but show the page
                    # in a narrower centered column so it reads like a page on
                    # screen instead of being stretched/zoomed across the panel.
                    imgs = dp.render_pdf_images(path, max_pages=10, zoom=2.0)
                    for img in imgs:
                        mid = st.columns([1, 2, 1])[1]
                        mid.image(img, use_container_width=True)
                    if d["num_pages"] > 10:
                        st.caption("Parapamje e kufizuar te 10 faqet e para. "
                                   "Shkarko skedarin për pamjen e plotë.")
                else:
                    st.caption("Word — parapamje teksti:")
                    st.text(dp.extract_text(path)[:4000])
