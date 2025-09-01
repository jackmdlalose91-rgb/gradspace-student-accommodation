# (truncated header comment)
import os
import json
import bcrypt
import qrcode
import urllib.parse
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta

import streamlit as st
from supabase import create_client, Client

def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)

SUPPORT_WHATSAPP = os.getenv("SUPPORT_WHATSAPP", "27821234567")
APP_URL = os.getenv("APP_URL", "https://gradspace.streamlit.app")

if "page" not in st.session_state:
    st.session_state.page = "landing"
if "user" not in st.session_state:
    st.session_state.user = None

def authenticate_user(username_or_email: str, password: str):
    try:
        supabase = get_supabase()
        resp = supabase.table("users").select("*").or_(f"username.eq.{username_or_email},email.eq.{username_or_email}").limit(1).execute()
        if not resp.data:
            return None
        user = resp.data[0]
        stored = user.get("password_hash", "").encode("utf-8")
        if stored and bcrypt.checkpw(password.encode("utf-8"), stored):
            return user
        return None
    except Exception as e:
        st.error(f"Auth error: {e}")
        return None

def set_new_password(user_id: str, new_password: str):
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    supabase = get_supabase()
    supabase.table("users").update({"password_hash": hashed, "first_login": False}).eq("id", user_id).execute()

def app_header():
    st.markdown("<h1 style='text-align:center;color:#2E86C1;'>🏠 Gradspace Student Accommodation</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;color:#117A65;'>Gradspace Manager</h3>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:16px 0;'>", unsafe_allow_html=True)

def app_share_tools():
    st.subheader("📲 Share / Install App")
    msg = f"Hi! Check out Gradspace — student accommodation portal: {APP_URL}"
    encoded_msg = urllib.parse.quote(msg)
    whatsapp_link = f"https://wa.me/?text={encoded_msg}"
    st.markdown(f"[💬 Share on WhatsApp]({whatsapp_link})", unsafe_allow_html=True)
    st.markdown("### 📷 Scan to open/install")
    qr = qrcode.make(APP_URL)
    buf = BytesIO(); qr.save(buf, format="PNG")
    st.image(buf.getvalue(), width=200, caption="Scan to open Gradspace App")
    st.download_button("⬇️ Download QR Code", buf.getvalue(), "gradspace_app_qr.png", "image/png")

def landing_page():
    app_header()
    st.info("Welcome to **Gradspace**. Please log in to access private dashboards.")
    app_share_tools()
    st.markdown("<br/>", unsafe_allow_html=True)
    if st.button("🔑 Go to Login"):
        st.session_state.page = "login"

def force_first_login_change(user):
    st.warning("You must set a new password before continuing.")
    new1 = st.text_input("New password", type="password")
    new2 = st.text_input("Confirm new password", type="password")
    if st.button("Update Password"):
        if len(new1) < 8:
            st.error("Password too short (min 8 chars)."); return
        if new1 != new2:
            st.error("Passwords do not match."); return
        set_new_password(user["id"], new1)
        st.success("Password updated. Continue to dashboard.")
        user["first_login"] = False
        st.session_state.user = user
        st.session_state.page = "dashboard"

def login_page():
    app_header()
    st.subheader("🔑 Secure Login")
    params = st.query_params
    invite_code = params.get("invite", "")
    prefill_user = invite_code if invite_code else ""
    username = st.text_input("Username / Email / Student ID", value=prefill_user)
    password = st.text_input("Password", type="password")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login"):
            user = authenticate_user(username, password)
            if user:
                st.session_state.user = user
                if user.get("first_login", True):
                    st.session_state.page = "first_login_change"
                else:
                    st.session_state.page = "dashboard"
            else:
                st.error("Invalid login.")
    with col2:
        if st.button("Forgot Password?"):
            st.session_state.page = "reset_password"
    st.markdown("<br/>", unsafe_allow_html=True)
    st.caption("Tip: If you received an invite QR, your username is prefilled.")

def reset_password_page():
    app_header()
    st.subheader("🔄 Reset Your Password")
    from datetime import datetime, timedelta
    email = st.text_input("Registered email")
    student_id = st.text_input("Student ID (optional, helps us verify)")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Send Reset Link via Email"):
            try:
                supabase = get_supabase()
                token = os.urandom(16).hex()
                supabase.table("reset_tokens").insert({
                    "email": email, "student_id": student_id, "token": token,
                    "valid_until": (datetime.utcnow() + timedelta(hours=2)).isoformat()
                }).execute()
                log_reset_action(student_id or email, "", "self", "email")
                st.success("If this email exists, a reset link will be sent.")
            except Exception as e:
                st.error(f"Error: {e}")
    with col2:
        if st.button("Request Reset via WhatsApp"):
            msg = f"Hello, I need a password reset for my Gradspace account (Student ID: {student_id}, Email: {email})."
            whatsapp_link = f"https://wa.me/{SUPPORT_WHATSAPP}?text={urllib.parse.quote(msg)}"
            st.markdown(f"[💬 Open WhatsApp to Request Reset]({whatsapp_link})", unsafe_allow_html=True)
    st.markdown('---')
    st.caption("Security: We never send passwords via WhatsApp. Management will verify and issue a secure reset link.")

def student_dashboard(user):
    st.subheader(f"👤 Welcome, {user.get('username', 'Student')}")
    st.info("This is your personal dashboard with invoices, payments, reminders, and profile.")
    student_link = f"{APP_URL}/login?user_id={user['id']}"
    st.write("Your quick link:", student_link)
    qr = qrcode.make(student_link); buf = BytesIO(); qr.save(buf, format="PNG")
    st.image(buf.getvalue(), width=160, caption="Scan to open your dashboard")

def admin_backup_section():
    st.subheader("📦 Download Backups")
    try:
        supabase = get_supabase()
        bucket = "backups"
        folders = ["students", "invoices", "staff", "maintenance"]
        for folder in folders:
            try:
                files = supabase.storage.from_(bucket).list(folder)
                if not files:
                    st.info(f"No backups found for {folder}."); continue
                files = sorted(files, key=lambda x: x.get("created_at",""), reverse=True)
                latest = files[0]["name"]
                st.write(f"📂 {folder.capitalize()} — Latest: {latest}")
                signed_url = supabase.storage.from_(bucket).create_signed_url(f"{folder}/{latest}", 300)
                st.markdown(f"[⬇️ Download {folder}]({signed_url['signedURL']})", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"{folder}: {e}")
    except Exception as e:
        st.error(f"Backup fetch error: {e}")

def log_reset_action(student_id, student_name, admin_id, method):
    try:
        supabase = get_supabase()
        supabase.table("reset_logs").insert({
            "student_id": student_id,
            "student_name": student_name,
            "admin_id": admin_id,
            "reset_method": method,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        st.warning(f"Could not log reset action: {e}")

def admin_reset_panel():
    st.subheader("🔑 Password Reset Panel")
    supabase = get_supabase()
    res = supabase.table("students").select("id,name,email").limit(1000).execute()
    students = res.data or []
    search = st.text_input("Search by ID/Name/Email")
    filtered = [s for s in students if search.lower() in (s.get("id","")+s.get("name","")+s.get("email","")).lower()]
    for s in filtered[:50]:
        with st.container(border=True):
            st.write(f"👤 {s.get('name')} — {s.get('id')} — {s.get('email','')}")
            if st.button(f"Generate Reset QR for {s.get('id')}", key=f"qr_{s.get('id')}"):
                reset_url = f"{APP_URL}/reset?invite={s.get('id')}"
                qr = qrcode.make(reset_url); buf = BytesIO(); qr.save(buf, format="PNG")
                st.image(buf.getvalue(), width=160, caption="Scan to Reset Password")
                st.code(reset_url, language="text")
                msg = f"Hello {s.get('name')}, here is your Gradspace reset link: {reset_url}"
                wlink = f"https://wa.me/{SUPPORT_WHATSAPP}?text={urllib.parse.quote(msg)}"
                st.markdown(f"[💬 Share via WhatsApp]({wlink})", unsafe_allow_html=True)
                st.download_button("⬇️ Download QR", buf.getvalue(), f"{s.get('id')}_reset_qr.png", "image/png")
                admin = st.session_state.user or {}
                log_reset_action(s.get('id'), s.get('name'), admin.get('id','admin'), "qr")

def admin_security_logs():
    st.subheader("🔐 Security Logs")
    supabase = get_supabase()
    try:
        logs = supabase.table("reset_logs").select("*").order("timestamp", desc=True).limit(1000).execute().data or []
        import pandas as pd
        df = pd.DataFrame(logs)
        if df.empty:
            st.info("No reset actions yet."); return
        col1, col2 = st.columns(2)
        with col1:
            user_filter = st.text_input("Filter by student_id/admin_id")
        with col2:
            method = st.selectbox("Method", options=["all","email","whatsapp","qr"])
        fdf = df.copy()
        if user_filter:
            fdf = fdf[fdf["student_id"].str.contains(user_filter) | fdf["admin_id"].str.contains(user_filter)]
        if method != "all":
            fdf = fdf[fdf["reset_method"] == method]
        st.dataframe(fdf, use_container_width=True)
        csv = fdf.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Export CSV", csv, "reset_logs.csv", "text/csv")
    except Exception as e:
        st.error(f"Error reading logs: {e}")

def admin_dashboard(user):
    st.subheader(f"👑 Admin Dashboard — {user.get('username')}")
    tab1, tab2, tab3 = st.tabs(["Students", "Resets", "Backups"])
    with tab1:
        st.info("Students management here (add/edit profiles, invoices, maintenance).")
    with tab2:
        admin_reset_panel()
        st.markdown('---')
        admin_security_logs()
    with tab3:
        admin_backup_section()
        app_share_tools()

def manager_dashboard(user):
    st.subheader(f"🧑‍💼 Manager Dashboard — {user.get('username')}")
    st.info("Add students, log maintenance, manage invoices.")
    app_share_tools()

def student_dashboard_router():
    user = st.session_state.user
    role = (user.get("role") or "student").lower()
    if role == "admin":
        admin_dashboard(user)
    elif role == "manager":
        manager_dashboard(user)
    else:
        student_dashboard(user)

def main():
    st.set_page_config(page_title="Gradspace", page_icon="🏠", layout="wide")
    page = st.session_state.page
    if st.session_state.user:
        if page == "first_login_change" and st.session_state.user.get("first_login", True):
            force_first_login_change(st.session_state.user)
        else:
            student_dashboard_router()
            if st.button("Logout"):
                st.session_state.user = None
                st.session_state.page = "landing"
    else:
        if page == "landing":
            landing_page()
        elif page == "login":
            login_page()
        elif page == "reset_password":
            reset_password_page()
        elif page == "first_login_change":
            st.info("Please log in first."); st.session_state.page = "login"; login_page()
        else:
            landing_page()

if __name__ == "__main__":
    main()
