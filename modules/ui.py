"""Shared UI helpers for pages: session guards and labels."""
import streamlit as st

from modules import auth

ROLE_LABELS = {auth.ADMIN: "Administrator", auth.PUNONJES: "Punonjës"}


def current_user():
    user = st.session_state.get("user")
    if not user:
        st.error("Ju lutem hyni në sistem.")
        st.stop()
    return user


def require_admin():
    user = current_user()
    if user["role"] != auth.ADMIN:
        st.error("Nuk keni leje për këtë faqe (vetëm administratori).")
        st.stop()
    return user
