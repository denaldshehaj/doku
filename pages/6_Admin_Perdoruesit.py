"""Admin page: create users and manage their active status."""
import streamlit as st

from modules import audit, auth, ui

user = ui.require_admin()
st.subheader("👥 Menaxhimi i Përdoruesve")

with st.expander("➕ Krijo përdorues të ri", expanded=False):
    c1, c2 = st.columns(2)
    username = c1.text_input("Përdoruesi")
    full_name = c2.text_input("Emri i plotë")
    c3, c4 = st.columns(2)
    password = c3.text_input("Fjalëkalimi", type="password")
    role = c4.selectbox("Roli", [auth.PUNONJES, auth.ADMIN],
                        format_func=lambda r: ui.ROLE_LABELS[r])
    if st.button("Krijo", type="primary"):
        try:
            auth.create_user(username, password, full_name, role, must_change=True)
            audit.log(user["id"], user["username"], "create_user", f"{username} ({role})")
            st.success(f"U krijua '{username}'. Do të ndryshojë fjalëkalimin në hyrjen e parë.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))

st.markdown("##### Përdoruesit")
for u in auth.list_users():
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        status = "🟢 aktiv" if u["is_active"] else "⚪ joaktiv"
        c1.markdown(f"**{u['username']}** · {u['full_name'] or '—'} · "
                    f"{ui.ROLE_LABELS.get(u['role'], u['role'])} · {status}")
        c1.caption(f"Krijuar: {u['created_at']}")
        # Don't let admin deactivate themselves.
        if u["username"] != user["username"]:
            if u["is_active"]:
                if c2.button("Çaktivizo", key=f"da{u['id']}"):
                    auth.set_active(u["username"], False); st.rerun()
            else:
                if c2.button("Aktivizo", key=f"ac{u['id']}"):
                    auth.set_active(u["username"], True); st.rerun()
