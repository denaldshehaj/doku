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
    is_self = u["username"] == user["username"]
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        status = "🟢 aktiv" if u["is_active"] else "⚪ joaktiv"
        c1.markdown(f"**{u['username']}** · {u['full_name'] or '—'} · "
                    f"{ui.ROLE_LABELS.get(u['role'], u['role'])} · {status}")
        c1.caption(f"Krijuar: {u['created_at']}")
        # Don't let admin deactivate themselves.
        if not is_self:
            if u["is_active"]:
                if c2.button("Çaktivizo", key=f"da{u['id']}"):
                    auth.set_active(u["username"], False); st.rerun()
            else:
                if c2.button("Aktivizo", key=f"ac{u['id']}"):
                    auth.set_active(u["username"], True); st.rerun()

        # Change role — not on yourself, to avoid self-lockout.
        with st.expander("🛡️ Ndrysho rolin"):
            if is_self:
                st.caption("Nuk mund të ndryshoni rolin tuaj.")
            else:
                roles = [auth.PUNONJES, auth.ADMIN]
                new_role = st.selectbox(
                    "Roli", roles, index=roles.index(u["role"]),
                    format_func=lambda r: ui.ROLE_LABELS[r], key=f"role{u['id']}")
                if st.button("Ruaj rolin", key=f"saverole{u['id']}",
                             disabled=new_role == u["role"]):
                    auth.set_role(u["username"], new_role)
                    audit.log(user["id"], user["username"], "set_role",
                              f"{u['username']} -> {new_role}")
                    st.success("Roli u përditësua."); st.rerun()

        # Set a specific new password.
        with st.expander("🔑 Ndrysho fjalëkalimin"):
            np = st.text_input("Fjalëkalimi i ri", type="password",
                               key=f"np{u['id']}")
            force = st.checkbox("Detyro ndryshimin në hyrjen e parë",
                                value=True, key=f"force{u['id']}")
            if st.button("Ruaj fjalëkalimin", key=f"savepw{u['id']}"):
                try:
                    auth.set_password(u["username"], np, must_change=force)
                    audit.log(user["id"], user["username"], "set_password",
                              u["username"])
                    st.success("Fjalëkalimi u ndryshua."); st.rerun()
                except ValueError as e:
                    st.error(str(e))

        # Reset to a random temporary password.
        with st.expander("♻️ Reseto fjalëkalimin"):
            st.caption("Krijon një fjalëkalim të përkohshëm; përdoruesi do ta "
                       "ndryshojë në hyrjen e parë.")
            if st.button("Reseto", key=f"reset{u['id']}"):
                temp = auth.reset_password(u["username"])
                audit.log(user["id"], user["username"], "reset_password",
                          u["username"])
                st.success(f"Fjalëkalimi i përkohshëm: `{temp}`")
