import streamlit as st
from utils.db import create_user, verify_user


def render_auth():
    st.markdown('<div class="hero-title">AI Video Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Transcribe · Summarise · Chat with Videos</div>', unsafe_allow_html=True)
    st.markdown("---")

    _, col2, _ = st.columns([1, 1.2, 1])
    with col2:
        st.markdown(f"""
        <div class="card" style="text-align:center">
            <div style="font-size:2.5rem;margin-bottom:0.5rem">🎬</div>
            <div class="card-title" style="justify-content:center">
                {"Login" if st.session_state.auth_mode == "login" else "Create Account"}
            </div>
        </div>""", unsafe_allow_html=True)

        # FIX 1: .strip() prevents whitespace login issues
        username = st.text_input("Username", placeholder="Enter username").strip()
        password = st.text_input("Password", placeholder="Enter password", type="password")

        if st.session_state.auth_mode == "login":
            if st.button("🔑 Login", use_container_width=True):
                # FIX 2: Empty field check before DB call
                if not username or not password:
                    st.warning("⚠️ Please enter both username and password.")
                else:
                    user = verify_user(username, password)
                    if user:
                        st.session_state.user = user
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password.")

            st.markdown(
                "<div style='text-align:center;margin-top:1rem;font-size:0.8rem;"
                "color:var(--text-muted)'>Don't have an account?</div>",
                unsafe_allow_html=True,
            )
            if st.button("Create Account →", use_container_width=True, type="secondary"):
                st.session_state.auth_mode = "register"
                st.rerun()

        else:
            if st.button("✅ Create Account", use_container_width=True):
                # FIX 2 (register): Empty field check before DB call
                if not username or not password:
                    st.warning("⚠️ Please enter both username and password.")
                elif len(username) < 3:
                    st.error("❌ Username must be at least 3 characters.")
                elif len(password) < 4:
                    st.error("❌ Password must be at least 4 characters.")
                else:
                    success = create_user(username, password)
                    if success:
                        user = verify_user(username, password)
                        st.session_state.user = user
                        st.success("✅ Account created!")
                        st.rerun()
                    else:
                        st.error("❌ Username already exists.")

            st.markdown(
                "<div style='text-align:center;margin-top:1rem;font-size:0.8rem;"
                "color:var(--text-muted)'>Already have an account?</div>",
                unsafe_allow_html=True,
            )
            if st.button("← Back to Login", use_container_width=True, type="secondary"):
                st.session_state.auth_mode = "login"
                st.rerun()