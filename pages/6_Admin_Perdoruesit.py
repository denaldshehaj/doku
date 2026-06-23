"""Admin page: create users, edit them in a paginated table (full name, role,
active status), and manage passwords."""
import math

import streamlit as st

from modules import audit, auth, ui

PER_PAGE = 10

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

# --- Users table with pagination -------------------------------------------
users = auth.list_users()
total = len(users)
total_pages = max(1, math.ceil(total / PER_PAGE))

st.markdown(f"##### Përdoruesit ({total})")

# Keep the current page in session and clamp it to the valid range.
page = st.session_state.get("users_page", 1)
page = min(max(1, page), total_pages)

if total > PER_PAGE:
    pcols = st.columns([1, 1, 3, 1, 1])
    if pcols[0].button("⬅️", disabled=page <= 1, key="users_prev"):
        st.session_state.users_page = page - 1; st.rerun()
    pcols[2].markdown(f"<p style='text-align:center'>Faqja <b>{page}</b> nga "
                      f"<b>{total_pages}</b></p>", unsafe_allow_html=True)
    if pcols[4].button("➡️", disabled=page >= total_pages, key="users_next"):
        st.session_state.users_page = page + 1; st.rerun()

start = (page - 1) * PER_PAGE
page_users = users[start:start + PER_PAGE]

rows = [{
    "Përdoruesi": u["username"],
    "Emri i plotë": u["full_name"] or "",
    "Roli": ui.ROLE_LABELS.get(u["role"], u["role"]),
    "Statusi": "Aktiv" if u["is_active"] else "Joaktiv",
    "Krijuar": (u["created_at"] or "")[:10],
} for u in page_users]

# Read-only paginated view; editing happens in the dropdown form below.
st.dataframe(rows, hide_index=True, use_container_width=True)

# --- Edit a user via dropdowns ---------------------------------------------
st.divider()
st.markdown("##### ✏️ Ndrysho një përdorues")
by_name = {u["username"]: u for u in users}
sel = st.selectbox("Përdoruesi", list(by_name.keys()), key="edit_user")
cur = by_name[sel]
is_self = sel == user["username"]

e1, e2 = st.columns(2)
new_name = e1.text_input("Emri i plotë", value=cur["full_name"] or "", key="edit_name")
roles = [auth.PUNONJES, auth.ADMIN]
new_role = e2.selectbox(
    "Roli", roles, index=roles.index(cur["role"]),
    format_func=lambda r: ui.ROLE_LABELS[r], key="edit_role",
    disabled=is_self, help="Nuk mund të ndryshoni rolin tuaj." if is_self else None)
statuses = [True, False]
new_active = st.selectbox(
    "Statusi", statuses, index=0 if cur["is_active"] else 1,
    format_func=lambda a: "Aktiv" if a else "Joaktiv", key="edit_status",
    disabled=is_self, help="Nuk mund të çaktivizoni veten." if is_self else None)

if st.button("💾 Ruaj ndryshimet", type="primary"):
    changed = 0
    if (new_name or "").strip() != (cur["full_name"] or ""):
        auth.set_full_name(sel, new_name); changed += 1
    if not is_self and new_role != cur["role"]:
        auth.set_role(sel, new_role)
        audit.log(user["id"], user["username"], "set_role", f"{sel} -> {new_role}")
        changed += 1
    if not is_self and bool(new_active) != bool(cur["is_active"]):
        auth.set_active(sel, new_active)
        audit.log(user["id"], user["username"], "set_active", f"{sel}={new_active}")
        changed += 1
    if changed:
        st.success(f"U ruajtën ndryshimet për '{sel}'."); st.rerun()
    else:
        st.info("Nuk ka ndryshime për të ruajtur.")

# --- Password management ----------------------------------------------------
st.divider()
st.markdown("##### 🔑 Menaxhimi i fjalëkalimit")
sel = st.selectbox("Zgjidh përdoruesin", [u["username"] for u in users],
                   key="pw_user")
pc1, pc2 = st.columns(2)
with pc1:
    np = st.text_input("Fjalëkalimi i ri", type="password", key="pw_new")
    force = st.checkbox("Detyro ndryshimin në hyrje", value=True, key="pw_force")
    if st.button("Ndrysho fjalëkalimin"):
        try:
            auth.set_password(sel, np, must_change=force)
            audit.log(user["id"], user["username"], "set_password", sel)
            st.success(f"Fjalëkalimi i '{sel}' u ndryshua.")
        except ValueError as e:
            st.error(str(e))
with pc2:
    st.caption("Reseto në një fjalëkalim të përkohshëm (ndryshohet në hyrje).")
    if st.button("♻️ Reseto fjalëkalimin"):
        temp = auth.reset_password(sel)
        audit.log(user["id"], user["username"], "reset_password", sel)
        st.success(f"Fjalëkalimi i përkohshëm për '{sel}': `{temp}`")
