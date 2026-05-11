from __future__ import annotations

import streamlit as st

from app.services.api_client import APIClientError
from app.services.auth_client import login, register
from app.utils.session import (
    get_auth_error,
    initialize_session_state,
    is_authenticated,
    redirect_to_dashboard,
    set_auth_error,
)


st.set_page_config(
    page_title="Sign In | LeadFlow AI",
    layout="centered",
)

initialize_session_state()

if is_authenticated():
    redirect_to_dashboard()

st.title("LeadFlow AI")
st.caption("Sign in to manage leads, follow-up drafts, and ready-to-send exports.")

auth_error = get_auth_error()
if auth_error:
    st.error(auth_error)

login_tab, register_tab = st.tabs(["Login", "Register"])

with login_tab:
    with st.form("login_form", clear_on_submit=False):
        st.subheader("Login")
        email = st.text_input("Email address", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Log in", use_container_width=True)

    if submitted:
        set_auth_error(None)
        if not email.strip() or not password:
            st.error("Enter your email address and password.")
        else:
            try:
                login(email.strip(), password)
            except APIClientError as exc:
                st.error(exc.message)
            else:
                st.success("Login successful.")
                redirect_to_dashboard()

with register_tab:
    with st.form("register_form", clear_on_submit=False):
        st.subheader("Create Account")
        new_email = st.text_input("Work email address", key="register_email")
        new_password = st.text_input("Password", type="password", key="register_password")
        confirm_password = st.text_input("Confirm password", type="password", key="confirm_password")
        registered = st.form_submit_button("Create account", use_container_width=True)

    if registered:
        set_auth_error(None)
        if not new_email.strip() or not new_password:
            st.error("Enter an email address and password.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        elif len(new_password) < 8:
            st.error("Use a password with at least 8 characters.")
        else:
            try:
                register(new_email.strip(), new_password)
            except APIClientError as exc:
                st.error(exc.message)
            else:
                st.success("Account created.")
                redirect_to_dashboard()
