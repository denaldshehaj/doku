"""Admin page: the audit log of all important actions."""
import streamlit as st

from modules import audit, ui

ui.require_admin()
st.subheader("📋 Audit Log")

rows = audit.recent(limit=500)
if not rows:
    st.info("Ende pa veprime të regjistruara.")
    st.stop()

st.dataframe(
    [{"Koha": r["created_at"], "Përdoruesi": r["username"],
      "Veprimi": r["action"], "Detaje": r["details"]} for r in rows],
    use_container_width=True, hide_index=True,
)
