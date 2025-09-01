import os
import json
import time
import secrets
import string
from datetime import datetime, timedelta
from email.message import EmailMessage

import streamlit as st
import pandas as pd
import numpy as np
import bcrypt
from email_validator import validate_email, EmailNotValidError

# ---------- Constants & Paths ----------
APP_TITLE = "🏠 Gradspace Student Accommodation Tracker"
APP_SUBTITLE = "Gradspace Manager"
USERS_FILE = "users.json"
DATA_DIR = "data"
UPLOADS_DIR = "uploads"
RESET_FILE = os.path.join(DATA_DIR, "reset_tokens.json")

# Ensure folders exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# ---------- PWA injection (manifest + service worker) ----------
st.markdown(
    """
    <link rel="manifest" href="/manifest.json" />
    <script>
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/service-worker.js').catch(console.error);
    }
    </script>
    """,
    unsafe_allow_html=True
)

# ---------- Utility helpers ----------
def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return default
    return default

def save_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)

def password_hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def password_matches(pw: str, pw_hash: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), pw_hash.encode("utf-8"))
    except Exception:
        return False

def random_code(n=6):
    return ''.join(secrets.choice(string.digits) for _ in range(n))

def random_temp_pass(n=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(n))

def send_email_via_smtp(to_email: str, subject: str, body: str) -> bool:
    """Send email using Streamlit Secrets if configured. Returns True if sent."""
    try:
        email_secrets = st.secrets.get("email", {})
        SMTP_SERVER = email_secrets.get("SMTP_SERVER", "smtp.gmail.com")
        SMTP_PORT = int(email_secrets.get("SMTP_PORT", "587"))
        EMAIL_USER = email_secrets.get("EMAIL_USER")
        EMAIL_PASS = email_secrets.get("EMAIL_PASS")
        if not EMAIL_USER or not EMAIL_PASS:
            return False

        import smtplib
        msg = EmailMessage()
        msg["From"] = EMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        st.warning(f"Email send failed: {e}")
        return False

# ---------- Load users & data ----------
users = load_json(USERS_FILE, {})
students = load_json(os.path.join(DATA_DIR, "students.json"), [])
maintenance = load_json(os.path.join(DATA_DIR, "maintenance.json"), [])
staff = load_json(os.path.join(DATA_DIR, "staff.json"), [])
invoices = load_json(os.path.join(DATA_DIR, "invoices.json"), [])
reset_tokens = load_json(RESET_FILE, {})  # {username: {"code": "...", "exp": "ISO", "temp": "pass"}}

# ---------- Header UI ----------
st.markdown("<h1 style='text-align:center; color:#2E86C1;'>" + APP_TITLE + "</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align:center; color:#117A65;'>" + APP_SUBTITLE + "</h2>", unsafe_allow_html=True)
st.markdown("<hr style='margin:20px 0;'>", unsafe_allow_html=True)

# ---------- Authentication ----------
def show_login():
    st.sidebar.header("🔑 Login")
    username = st.sidebar.text_input("Username", key="login_user")
    password = st.sidebar.text_input("Password", type="password", key="login_pass")
    login_clicked = st.sidebar.button("Login", use_container_width=True)

    with st.sidebar.expander("Forgot password?"):
        fp_user = st.text_input("Your username", key="fp_user")
        fp_email = st.text_input("Registered email", key="fp_email")
        if st.button("Send reset code", key="send_reset_code"):
            if fp_user in users:
                # validate email
                user_email = users[fp_user].get("email", "")
                try:
                    validate_email(fp_email)
                    if fp_email.strip().lower() != user_email.strip().lower():
                        st.error("Email does not match our records.")
                    else:
                        code = random_code(6)
                        temp_pass = random_temp_pass(10)
                        exp = (datetime.utcnow() + timedelta(minutes=20)).isoformat()
                        reset_tokens[fp_user] = {"code": code, "exp": exp, "temp": temp_pass}
                        save_json(RESET_FILE, reset_tokens)

                        sent = send_email_via_smtp(
                            to_email=fp_email,
                            subject="Gradspace password reset",
                            body=(
                                f"Here is your password reset code: {code}\n\n"
                                f"Temporary password: {temp_pass}\n"
                                f"This code expires in 20 minutes.\n\n"
                                f"Return to the app, open 'Forgot password?' → 'I have a reset code', "
                                f"enter your code, and set a new password."
                            )
                        )
                        if sent:
                            st.success("Reset code sent to your email.")
                        else:
                            st.info("Email isn't configured; copy this code and temp password manually.")
                            st.code(f"Code: {code}\nTemp password: {temp_pass}")
                except EmailNotValidError as e:
                    st.error(f"Invalid email: {e}")
            else:
                st.error("Unknown username.")

        with st.expander("I have a reset code"):
            rc_user = st.text_input("Username", key="rc_user")
            rc_code = st.text_input("Reset code", key="rc_code")
            new_pw = st.text_input("New password", type="password", key="rc_newpw")
            if st.button("Confirm reset", key="rc_confirm"):
                tok = reset_tokens.get(rc_user)
                if not tok:
                    st.error("No reset request found.")
                else:
                    try:
                        if datetime.utcnow() > datetime.fromisoformat(tok["exp"]):
                            st.error("Reset code expired.")
                        elif rc_code.strip() != tok["code"]:
                            st.error("Incorrect code.")
                        else:
                            # user must log in with temp password first OR we directly set
                            users[rc_user]["password_hash"] = password_hash(new_pw)
                            save_json(USERS_FILE, users)
                            reset_tokens.pop(rc_user, None)
                            save_json(RESET_FILE, reset_tokens)
                            st.success("Password updated. You can now log in with your new password.")
                    except Exception as e:
                        st.error(f"Reset failed: {e}")

    if login_clicked:
        if username in users and password_matches(password, users[username]["password_hash"]):
            st.session_state["auth"] = True
            st.session_state["user"] = username
            st.session_state["role"] = users[username].get("role", "student")
            st.session_state["name"] = users[username].get("name", username)
            st.experimental_rerun()
        else:
            st.error("❌ Invalid username or password")

def ensure_auth():
    if not st.session_state.get("auth"):
        show_login()
        st.stop()

# ---------- Sidebar ----------
if st.session_state.get("auth"):
    st.sidebar.success(f"Signed in as {st.session_state.get('name')} ({st.session_state.get('role')})")
    if st.sidebar.button("Sign out"):
        for k in ["auth","user","role","name"]:
            st.session_state.pop(k, None)
        st.experimental_rerun()

# ---------- Pages ----------
def page_students():
    st.subheader("👩🏽‍🎓 Students")
    global students

    with st.form("add_student"):
        cols = st.columns(2)
        with cols[0]:
            name = st.text_input("Full name")
            phone = st.text_input("Phone (WhatsApp)")
            email = st.text_input("Email")
            suite = st.text_input("Suite / Room")
            rent = st.number_input("Rent", min_value=0.0, step=50.0)
            utilities = st.number_input("Utilities", min_value=0.0, step=10.0)
        with cols[1]:
            kin = st.text_input("Next of kin")
            kin_phone = st.text_input("Kin phone")
            address = st.text_area("Home address")
            photo = st.file_uploader("Profile photo", type=["png","jpg","jpeg"])
        submitted = st.form_submit_button("Add / Update")
        if submitted:
            photo_path = ""
            if photo:
                photo_path = os.path.join(UPLOADS_DIR, f"student_{int(time.time())}_{photo.name}")
                with open(photo_path, "wb") as f:
                    f.write(photo.read())
            student = {
                "name": name, "phone": phone, "email": email,
                "suite": suite, "rent": rent, "utilities": utilities,
                "kin": kin, "kin_phone": kin_phone, "address": address,
                "photo": photo_path, "created": datetime.utcnow().isoformat()
            }
            # upsert by name+suite
            idx = next((i for i,s in enumerate(students) if s["name"]==name and s["suite"]==suite), None)
            if idx is None:
                students.append(student)
            else:
                students[idx] = student
            save_json(os.path.join(DATA_DIR, "students.json"), students)
            st.success("Student saved.")

    if students:
        df = pd.DataFrame(students)
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "students.csv", "text/csv")
    else:
        st.info("No students yet.")

def page_maintenance():
    st.subheader("🛠 Maintenance")
    global maintenance

    with st.form("add_job"):
        cols = st.columns(2)
        with cols[0]:
            title = st.text_input("Job title")
            desc = st.text_area("Description")
            assignee = st.text_input("Assignee")
        with cols[1]:
            cost = st.number_input("Estimated cost", min_value=0.0, step=10.0)
            status = st.selectbox("Status", ["Open","In Progress","Closed"])
            evidence = st.file_uploader("Photo evidence", type=["png","jpg","jpeg"])
        submitted = st.form_submit_button("Add job")
        if submitted:
            photo_path = ""
            if evidence:
                photo_path = os.path.join(UPLOADS_DIR, f"job_{int(time.time())}_{evidence.name}")
                with open(photo_path, "wb") as f:
                    f.write(evidence.read())
            job = {
                "title": title, "desc": desc, "assignee": assignee,
                "cost": cost, "status": status, "photo": photo_path,
                "created": datetime.utcnow().isoformat()
            }
            maintenance.append(job)
            save_json(os.path.join(DATA_DIR, "maintenance.json"), maintenance)
            st.success("Job added.")

    if maintenance:
        df = pd.DataFrame(maintenance)
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "maintenance.csv", "text/csv")
    else:
        st.info("No maintenance jobs yet.")

def page_staff():
    st.subheader("👥 Staff")
    global staff

    with st.form("add_staff"):
        cols = st.columns(3)
        with cols[0]:
            name = st.text_input("Name")
        with cols[1]:
            role = st.selectbox("Role", ["manager","maintenance","grounds","admin"])
        with cols[2]:
            phone = st.text_input("Phone")
        email = st.text_input("Email")
        submitted = st.form_submit_button("Add staff")
        if submitted:
            staff.append({"name":name,"role":role,"phone":phone,"email":email,"created":datetime.utcnow().isoformat()})
            save_json(os.path.join(DATA_DIR, "staff.json"), staff)
            st.success("Staff saved.")

    if staff:
        df = pd.DataFrame(staff)
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "staff.csv", "text/csv")
    else:
        st.info("No staff yet.")

def page_invoices():
    st.subheader("📄 Invoices")
    global invoices, students

    with st.form("gen_invoice"):
        cols = st.columns(2)
        with cols[0]:
            target = st.selectbox("Generate for", ["All students"] + [s["suite"] for s in students])
        with cols[1]:
            note = st.text_input("Note (e.g., September rent)")
        submitted = st.form_submit_button("Generate")
        if submitted:
            targets = students if target=="All students" else [s for s in students if s["suite"]==target]
            created = []
            for s in targets:
                amount = float(s.get("rent", 0)) + float(s.get("utilities", 0))
                inv = {
                    "student": s["name"], "suite": s["suite"], "amount": amount,
                    "note": note, "email": s.get("email",""), "phone": s.get("phone",""),
                    "created": datetime.utcnow().isoformat()
                }
                invoices.append(inv)
                created.append(inv)
            save_json(os.path.join(DATA_DIR, "invoices.json"), invoices)
            st.success(f"Generated {len(created)} invoices.")

    if invoices:
        df = pd.DataFrame(invoices)
        st.dataframe(df, use_container_width=True)

        # Build WhatsApp/Email links for quick copy
        st.markdown("#### Quick send links")
        for inv in invoices[-20:][::-1]:
            msg = f"Hello {inv['student']}, your invoice for {inv['note']} is {inv['amount']:.2f}."
            wa = f"https://wa.me/{inv.get('phone','').replace('+','').replace(' ','')}?text=" + st.secrets.get("urlencode", lambda x:x)(msg) if False else f"https://wa.me/?text={msg}"
            mailto = f"mailto:{inv.get('email','')}?subject=Invoice%20{inv['note']}&body={msg}"
            st.write(f"• **{inv['student']}** — [WhatsApp]({wa}) | [Email]({mailto})")

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "invoices.csv", "text/csv")
    else:
        st.info("No invoices yet.")

def page_settings():
    st.subheader("⚙️ Settings")
    st.write("Manage users, suites, and view demo accounts.")

    st.markdown("**Demo users (from `users.json`)**")
    st.json(users)

    with st.expander("➕ Add / Update user"):
        u = st.text_input("Username", key="set_u")
        nm = st.text_input("Name", key="set_nm")
        em = st.text_input("Email", key="set_em")
        rl = st.selectbox("Role", ["admin","manager","student"], key="set_rl")
        pw = st.text_input("Password (will be hashed)", type="password", key="set_pw")
        if st.button("Save user"):
            if not u:
                st.error("Username required.")
            else:
                users[u] = {
                    "name": nm or u,
                    "email": em,
                    "role": rl,
                    "password_hash": password_hash(pw or random_temp_pass())
                }
                save_json(USERS_FILE, users)
                st.success("User saved.")

    st.markdown("### Email (SMTP)")
    st.write("Configure in Streamlit Secrets → `email` section:")
    st.code(
        """[email]
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = "587"
EMAIL_USER = "you@example.com"
EMAIL_PASS = "your-app-password"
""")

def student_portal():
    st.subheader("🎓 My Account")
    me = st.session_state.get("user")
    my_rec = next((s for s in students if s.get("name")==users[me].get("name")), None)
    st.write("Welcome,", users[me].get("name"))
    if my_rec:
        st.json(my_rec)
    else:
        st.info("No student record linked to your name yet.")

# ---------- Routing by role ----------
def main_app():
    role = st.session_state.get("role", "student")
    if role == "student":
        tabs = ["My Account"]
    elif role == "manager":
        tabs = ["Students","Maintenance","Invoices","Staff"]
    else:  # admin
        tabs = ["Students","Maintenance","Invoices","Staff","Settings"]

    choice = st.sidebar.radio("Navigate", tabs, key="nav")
    if choice == "Students":
        page_students()
    elif choice == "Maintenance":
        page_maintenance()
    elif choice == "Staff":
        page_staff()
    elif choice == "Invoices":
        page_invoices()
    elif choice == "Settings":
        page_settings()
    else:
        student_portal()

# ---------- Entry ----------
if not st.session_state.get("auth"):
    show_login()
else:
    main_app()
