"""Admin page: create users, edit them in a paginated table (full name, role,
active status), and manage passwords."""
import math

import streamlit as st

from modules import audit, auth, ui

PER_PAGE = 10
LABEL_TO_ROLE = {v: k for k, v in ui.ROLE_LABELS.items()}

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
    "Aktiv": bool(u["is_active"]),
    "Krijuar": (u["created_at"] or "")[:10],
} for u in page_users]

edited = st.data_editor(
    rows, hide_index=True, use_container_width=True, key=f"users_editor_{page}",
    column_config={
        "Përdoruesi": st.column_config.TextColumn(disabled=True),
        "Emri i plotë": st.column_config.TextColumn(width="medium"),
        "Roli": st.column_config.SelectboxColumn(
            options=list(ui.ROLE_LABELS.values()), required=True),
        "Aktiv": st.column_config.CheckboxColumn(),
        "Krijuar": st.column_config.TextColumn(disabled=True),
    },
)

if st.button("💾 Ruaj ndryshimet", type="primary"):
    original = {u["username"]: u for u in page_users}
    changed, skipped = 0, []
    for row in edited:
        uname = row["Përdoruesi"]
        orig = original.get(uname)
        if orig is None:
            continue
        is_self = uname == user["username"]
        # Full name
        new_name = (row["Emri i plotë"] or "").strip()
        if new_name != (orig["full_name"] or ""):
            auth.set_full_name(uname, new_name); changed += 1
        # Role (cannot change your own — avoids self-lockout)
        new_role = LABEL_TO_ROLE.get(row["Roli"], orig["role"])
        if new_role != orig["role"]:
            if is_self:
                skipped.append(f"{uname}: rolin tuaj")
            else:
                auth.set_role(uname, new_role)
                audit.log(user["id"], user["username"], "set_role",
                          f"{uname} -> {new_role}"); changed += 1
        # Active (cannot deactivate yourself)
        new_active = bool(row["Aktiv"])
        if new_active != bool(orig["is_active"]):
            if is_self and not new_active:
                skipped.append(f"{uname}: çaktivizimin e vetes")
            else:
                auth.set_active(uname, new_active); changed += 1
    if changed:
        st.success(f"U ruajtën {changed} ndryshime.")
    if skipped:
        st.warning("U anashkaluan: " + "; ".join(skipped))
    if changed:
        st.rerun()

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
