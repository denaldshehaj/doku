"""Admin page: RAG vs no-RAG experiment. Runs sample questions both ways,
measures timing/chunks/sources, lets you score accuracy & hallucination manually,
and exports the comparison table to CSV for the thesis Results chapter."""
import threading
import time

import streamlit as st

from modules import audit, experiments, ui


def run_threaded(fn, est_seconds, on_tick, tick_every=0.4):
    """Run a blocking call in a worker thread while the main thread animates a
    progress estimate. on_tick(frac, elapsed) is called repeatedly (frac is the
    estimated 0..1 completion) and once more at 1.0 on finish. Re-raises any
    error from the worker."""
    out, err = {}, {}

    def worker():
        try:
            out["v"] = fn()
        except Exception as exc:   # noqa: BLE001 - surfaced to the caller
            err["e"] = exc

    th = threading.Thread(target=worker, daemon=True)
    t0 = time.perf_counter()
    th.start()
    while th.is_alive():
        elapsed = time.perf_counter() - t0
        frac = min(0.95, elapsed / est_seconds) if est_seconds > 0 else 0.0
        on_tick(frac, elapsed)
        time.sleep(tick_every)
    th.join()
    on_tick(1.0, time.perf_counter() - t0)
    if "e" in err:
        raise err["e"]
    return out.get("v")


user = ui.require_admin()
st.subheader("🧪 Eksperimente: RAG kundrejt pa-RAG")
st.caption("Krahaso përgjigjet me dhe pa RAG, mat kohën/citimet, vlerëso manualisht "
           "saktësinë e halucinacionin, dhe eksporto në CSV.")

sample = experiments.load_sample_questions()
st.markdown(f"**Pyetje testuese të disponueshme:** {len(sample)} "
            f"(nga `tests/sample_questions.csv`)")

def _fmt(s: float) -> str:
    s = int(round(s))
    return f"{s//60}m {s%60}s" if s >= 60 else f"{s}s"


c1, c2 = st.columns(2)
if c1.button("▶️ Ekzekuto të gjitha pyetjet testuese", type="primary"):
    if not sample:
        st.warning("Nuk u gjetën pyetje në sample_questions.csv.")
    else:
        est = experiments.avg_run_seconds()
        n = len(sample)
        st.caption(f"Vlerësim fillestar: ~{_fmt(est * n)} për {n} pyetje "
                   f"(~{_fmt(est)}/pyetje).")
        bar = st.progress(0.0)
        status = st.empty()
        t_batch = time.perf_counter()
        done, failed = 0, []
        for i, q in enumerate(sample):
            def tick(frac, _elapsed, i=i, q=q):
                overall = (i + frac) / n
                total_el = time.perf_counter() - t_batch
                eta = max(0.0, (n - i - frac) * est)
                bar.progress(overall)
                status.markdown(
                    f"**Pyetja {i+1}/{n}** · e kaluar {_fmt(total_el)} · "
                    f"mbetur ~{_fmt(eta)}  \n_{q[:70]}_")
            try:
                run_threaded(lambda q=q: experiments.run_one(q), est, tick)
                done += 1
            except Exception as e:  # noqa: BLE001
                failed.append((q, str(e)))
        bar.progress(1.0)
        status.empty()
        audit.log(user["id"], user["username"], "run_experiment", f"{done} pyetje")
        st.success(f"U ekzekutuan {done}/{n} pyetje në {_fmt(time.perf_counter()-t_batch)}.")
        if failed:
            st.warning(f"{len(failed)} pyetje dështuan (kontrollo Ollama-n). "
                       f"Shembull: {failed[0][1][:120]}")
        if done:
            st.rerun()

custom_q = c2.text_input("Ose shto një pyetje të vetme")
if c2.button("▶️ Ekzekuto pyetjen") and custom_q.strip():
    est = experiments.avg_run_seconds()
    st.caption(f"Vlerësim: ~{_fmt(est)}.")
    bar = st.progress(0.0)
    status = st.empty()
    def tick(frac, elapsed):
        bar.progress(frac)
        status.markdown(f"Duke ekzekutuar… e kaluar {_fmt(elapsed)} / "
                        f"vlerësim ~{_fmt(est)}")
    try:
        run_threaded(lambda: experiments.run_one(custom_q.strip()), est, tick)
        status.empty()
        audit.log(user["id"], user["username"], "run_experiment", custom_q.strip()[:80])
        st.success("U ekzekutua."); st.rerun()
    except Exception as e:
        st.error(f"Gabim (kontrollo Ollama-n): {e}")

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
