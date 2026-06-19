"""DOKU — entrypoint. Login, session, forced password change, and role-based
navigation (Streamlit multipage via st.navigation). Run from repo root:

    .venv\\Scripts\\streamlit run app.py
"""
import streamlit as st

import config
from modules import audit, auth, database, llm_client

st.set_page_config(page_title="DOKU", page_icon="📄", layout="wide")

# --- Bootstrap: auto-create folders, DB, and default admin if missing ---
database.init_schema()
auth.ensure_default_admin()

ROLE_LABELS = {auth.ADMIN: "Administrator", auth.PUNONJES: "Punonjës"}

# Fsheh plotësisht panelin anësor (dhe shigjetën e hapjes) derisa login-i të
# përfundojë me sukses. `position="hidden"` fsheh vetëm menynë e faqeve, jo vetë
# shtyllën bosh — kjo CSS e heq tërësisht.
_HIDE_SIDEBAR_CSS = """
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] { display: none !important; }
</style>
"""


def current_user():
    return st.session_state.get("user")


def login_screen():
    st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.markdown("<h1 style='text-align:center;margin-bottom:0'>📄 DOKU</h1>",
                    unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#8b94a3'>Sistem Inteligjent "
                    "Lokal për Analizë Dokumentesh Institucionale</p>",
                    unsafe_allow_html=True)
        with st.form("login"):
            username = st.text_input("Përdoruesi")
            password = st.text_input("Fjalëkalimi", type="password")
            if st.form_submit_button("Hyr", type="primary", use_container_width=True):
                user = auth.authenticate(username, password)
                if user is None:
                    audit.log(None, username or "?", "login_failed")
                    st.error("Kredenciale të pasakta ose llogari joaktive.")
                else:
                    st.session_state.user = {
                        "id": user["id"], "username": user["username"],
                        "role": user["role"], "full_name": user["full_name"] or "",
                    }
                    audit.log(user["id"], user["username"], "login_success")
                    st.rerun()


def change_password_screen():
    user = current_user()
    st.title("🔐 Vendos një fjalëkalim të ri")
    st.warning("Fjalëkalimi i parazgjedhur duhet ndryshuar para se të vazhdosh.")
    with st.form("chpw"):
        p1 = st.text_input("Fjalëkalimi i ri (min. 6 karaktere)", type="password")
        p2 = st.text_input("Përsërit fjalëkalimin", type="password")
        if st.form_submit_button("Ruaj", type="primary"):
            if p1 != p2:
                st.error("Fjalëkalimet nuk përputhen.")
            else:
                try:
                    auth.set_password(user["username"], p1)
                    audit.log(user["id"], user["username"], "password_change")
                    st.success("Fjalëkalimi u ndryshua.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))


def sidebar(user):
    with st.sidebar:
        st.markdown("## 📄 DOKU")
        name = user["full_name"] or user["username"]
        st.markdown(f"👤 **{name}**  \n_{ROLE_LABELS.get(user['role'], user['role'])}_")
        online = llm_client.is_available()
        st.caption(f"Modeli lokal: {'🟢 aktiv' if online else '🔴 jo aktiv'}")
        if online:
            models = llm_client.list_models() or [config.OLLAMA_MODEL]
            cur = llm_client.get_active_model()
            idx = models.index(cur) if cur in models else 0
            llm_client.set_active_model(st.selectbox("Modeli i gjuhës", models, index=idx))
        else:
            st.warning("Ollama nuk po përgjigjet.")
        st.divider()
        if st.button("🚪 Dil", use_container_width=True):
            audit.log(user["id"], user["username"], "logout")
            st.session_state.pop("user", None)
            st.rerun()


def main():
    user = current_user()
    if not user:
        # Hidden navigation so no page menu shows on the login screen, and the
        # pages cannot be opened until the user has logged in.
        st.markdown(_HIDE_SIDEBAR_CSS, unsafe_allow_html=True)
        st.navigation([st.Page(login_screen, title="Hyr")], position="hidden").run()
        return
    if auth.needs_password_change(user["username"]):
        # Login-i nuk konsiderohet i përfunduar derisa fjalëkalimi i parazgjedhur
        # të ndryshohet — mbaje panelin anësor të fshehur edhe këtu.
        st.markdown(_HIDE_SIDEBAR_CSS, unsafe_allow_html=True)
        st.navigation([st.Page(change_password_screen, title="Ndrysho fjalëkalimin")],
                      position="hidden").run()
        return

    employee_pages = [
        st.Page("pages/1_Dashboard.py", title="Paneli", icon="🏠", default=True),
        st.Page("pages/2_Pyet_Dokumentet.py", title="Pyet Dokumentet", icon="❓"),
        st.Page("pages/3_Permbledhje_Dokumenti.py", title="Përmbledhje", icon="📝"),
        st.Page("pages/4_Historiku.py", title="Historiku im", icon="🕘"),
    ]
    admin_pages = [
        st.Page("pages/5_Admin_Dokumentet.py", title="Dokumentet", icon="📄"),
        st.Page("pages/6_Admin_Perdoruesit.py", title="Përdoruesit", icon="👥"),
        st.Page("pages/7_Admin_Audit_Log.py", title="Audit Log", icon="📋"),
        st.Page("pages/8_Eksperimente.py", title="Eksperimente", icon="🧪"),
    ]
    pages = employee_pages + (admin_pages if user["role"] == auth.ADMIN else [])
    nav = st.navigation(pages)
    sidebar(user)
    nav.run()


main()
