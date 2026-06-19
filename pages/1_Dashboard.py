"""Dashboard: welcome + key metrics."""
import streamlit as st

from modules import auth, documents, history, ui, vector_store

user = ui.current_user()

st.subheader(f"Mirë se erdhe, {user['full_name'] or user['username']} 👋")
st.caption("DOKU — Sistem Inteligjent Lokal për Analizë Dokumentesh Institucionale")

active_docs = documents.list_documents(active_only=True)
all_docs = documents.list_documents()

c1, c2, c3, c4 = st.columns(4)
c1.metric("📄 Dokumente aktive", len(active_docs))
c2.metric("🗂️ Dokumente gjithsej", len(all_docs))
c3.metric("🧩 Copëza (indeks)", vector_store.count())
if user["role"] == auth.ADMIN:
    c4.metric("👥 Përdorues", auth.user_count())
else:
    c4.metric("❓ Pyetjet e mia", history.count_for_user(user["username"]))

st.divider()
st.markdown("#### Çfarë mund të bësh")
a, b, c = st.columns(3)
a.markdown("**❓ Pyet Dokumentet**\n\nPyetje mbi korpusin me citime ose refuzim.")
b.markdown("**📝 Përmbledhje**\n\nPërmbledh një dokument në formate të ndryshme.")
c.markdown("**🕘 Historiku im**\n\nShiko pyetjet e tua të mëparshme.")

if user["role"] == auth.ADMIN and not all_docs:
    st.warning("Nuk ka ende dokumente. Shko te **📄 Dokumentet** për të ngarkuar PDF.")
