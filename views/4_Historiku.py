"""Employee page: the user's own question/answer history."""
import streamlit as st

from modules import history, ui

user = ui.current_user()
st.subheader("🕘 Historiku im")

rows = history.recent(user["username"], limit=100)
if not rows:
    st.info("Ende pa pyetje.")
    st.stop()

MODE_LABEL = {"rag": "Pyetje (RAG)", "no_rag": "Pa RAG", "summary": "Përmbledhje"}

for r in rows:
    mode = MODE_LABEL.get(r["mode"], r["mode"])
    with st.expander(f"{r['question'][:80]}  ·  {mode}  ·  {r['created_at']}"):
        st.write(r["answer"])
        if r["response_time"] is not None:
            st.caption(f"⏱️ {r['response_time']}s")
