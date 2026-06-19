"""Admin page: RAG vs no-RAG experiment. Runs sample questions both ways,
measures timing/chunks/sources, lets you score accuracy & hallucination manually,
and exports the comparison table to CSV for the thesis Results chapter."""
import streamlit as st

from modules import audit, experiments, ui

user = ui.require_admin()
st.subheader("🧪 Eksperimente: RAG kundrejt pa-RAG")
st.caption("Krahaso përgjigjet me dhe pa RAG, mat kohën/citimet, vlerëso manualisht "
           "saktësinë e halucinacionin, dhe eksporto në CSV.")

sample = experiments.load_sample_questions()
st.markdown(f"**Pyetje testuese të disponueshme:** {len(sample)} "
            f"(nga `tests/sample_questions.csv`)")

c1, c2 = st.columns(2)
if c1.button("▶️ Ekzekuto të gjitha pyetjet testuese", type="primary"):
    if not sample:
        st.warning("Nuk u gjetën pyetje në sample_questions.csv.")
    else:
        try:
            with st.spinner(f"Duke ekzekutuar {len(sample)} pyetje me dhe pa RAG..."):
                ids = experiments.run_batch(sample)
            audit.log(user["id"], user["username"], "run_experiment",
                      f"{len(ids)} pyetje")
            st.success(f"U ekzekutuan {len(ids)} pyetje.")
        except Exception as e:
            st.error(f"Gabim gjatë ekzekutimit (kontrollo Ollama-n): {e}")

custom_q = c2.text_input("Ose shto një pyetje të vetme")
if c2.button("▶️ Ekzekuto pyetjen") and custom_q.strip():
    try:
        with st.spinner("Duke ekzekutuar..."):
            experiments.run_one(custom_q.strip())
        audit.log(user["id"], user["username"], "run_experiment", custom_q.strip()[:80])
        st.success("U ekzekutua."); st.rerun()
    except Exception as e:
        st.error(f"Gabim: {e}")

st.divider()
results = experiments.list_results()
if not results:
    st.info("Ende pa rezultate. Ekzekuto pyetjet më sipër.")
    st.stop()

# Editable table for manual evaluation.
rows = [{
    "id": r["id"], "Pyetja": r["question"],
    "Koha pa RAG (s)": r["time_without_rag"], "Koha me RAG (s)": r["time_with_rag"],
    "Copëza": r["chunks_used"], "Citime": "Po" if r["has_sources"] else "Jo",
    "Saktësia pa RAG (1-5)": r["manual_accuracy_without_rag"],
    "Saktësia me RAG (1-5)": r["manual_accuracy_with_rag"],
    "Halucinacion pa RAG": r["hallucination_without_rag"] or "",
    "Halucinacion me RAG": r["hallucination_with_rag"] or "",
    "Shënime": r["notes"] or "",
} for r in results]

edited = st.data_editor(
    rows, use_container_width=True, hide_index=True, key="exp_editor",
    column_config={
        "id": st.column_config.NumberColumn("id", disabled=True),
        "Pyetja": st.column_config.TextColumn("Pyetja", disabled=True, width="large"),
        "Koha pa RAG (s)": st.column_config.NumberColumn(disabled=True),
        "Koha me RAG (s)": st.column_config.NumberColumn(disabled=True),
        "Copëza": st.column_config.NumberColumn(disabled=True),
        "Citime": st.column_config.TextColumn(disabled=True),
        "Saktësia pa RAG (1-5)": st.column_config.NumberColumn(min_value=1, max_value=5),
        "Saktësia me RAG (1-5)": st.column_config.NumberColumn(min_value=1, max_value=5),
        "Halucinacion pa RAG": st.column_config.SelectboxColumn(options=["", "Po", "Jo"]),
        "Halucinacion me RAG": st.column_config.SelectboxColumn(options=["", "Po", "Jo"]),
        "Shënime": st.column_config.TextColumn(width="medium"),
    },
)

cc1, cc2 = st.columns(2)
if cc1.button("💾 Ruaj vlerësimet manuale", type="primary"):
    for row in edited:
        experiments.update_manual_eval(
            row["id"],
            acc_no_rag=row["Saktësia pa RAG (1-5)"],
            acc_rag=row["Saktësia me RAG (1-5)"],
            hall_no_rag=row["Halucinacion pa RAG"] or None,
            hall_rag=row["Halucinacion me RAG"] or None,
            notes=row["Shënime"] or None)
    st.success("Vlerësimet u ruajtën.")

if cc2.button("📊 Eksporto në CSV"):
    path = experiments.export_csv()
    with open(path, "rb") as fh:
        st.download_button("⬇️ Shkarko CSV", fh.read(),
                           file_name=path.replace("\\", "/").split("/")[-1],
                           mime="text/csv")
