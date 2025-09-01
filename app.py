
import os, json, time, secrets, string
from datetime import datetime, timedelta, date
from email.message import EmailMessage

import streamlit as st
import pandas as pd
import bcrypt
from email_validator import validate_email, EmailNotValidError

SUPABASE_URL = st.secrets.get("supabase", {}).get("url")
SUPABASE_KEY = st.secrets.get("supabase", {}).get("anon_key")
SUPA = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        SUPA = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.warning(f"Supabase client init failed: {e}")

APP_TITLE = "🏠 Gradspace Student Accommodation Tracker"
APP_SUBTITLE = "Gradspace Manager"
DATA_DIR = "data"
UPLOADS_DIR = "uploads"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# PWA
st.markdown("""
<link rel="manifest" href="/manifest.json" />
<script>if('serviceWorker' in navigator){navigator.serviceWorker.register('/service-worker.js').catch(console.error)}</script>
""", unsafe_allow_html=True)

def load_json(path, default):
    if os.path.exists(path):
        try:
            return json.load(open(path))
        except: return default
    return default
def save_json(path, obj): json.dump(obj, open(path,"w"), indent=2)

USERS_FILE = "users.json"
local_settings = load_json(os.path.join(DATA_DIR,"settings.json"), {
    "branding":{"title":"Gradspace","primary":"#2E86C1"},
    "billing":{"currency":"ZAR","default_rent":0,"default_utilities":0},
    "notify":{"email_invoices":True,"email_overdue":True,"cc_manager":False,
              "template_invoice":"Hello {name}, your invoice {note} is {amount} {currency}, due {due_date}.",
              "template_overdue":"Hi {name}, your invoice is overdue: {amount} {currency}. Please pay."}
})

def pw_hash(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def pw_ok(p,h):
    try: return bcrypt.checkpw(p.encode(), h.encode())
    except: return False
def send_email(to_email, subject, body):
    try:
        email_secrets = st.secrets.get("email", {})
        SMTP_SERVER = email_secrets.get("SMTP_SERVER", "smtp.gmail.com")
        SMTP_PORT = int(email_secrets.get("SMTP_PORT", "587"))
        EMAIL_USER = email_secrets.get("EMAIL_USER")
        EMAIL_PASS = email_secrets.get("EMAIL_PASS")
        if not EMAIL_USER or not EMAIL_PASS: return False
        import smtplib
        msg = EmailMessage(); msg["From"] = EMAIL_USER; msg["To"] = to_email; msg["Subject"] = subject; msg.set_content(body)
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
            s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(msg)
        return True
    except Exception as e:
        st.warning(f"Email send failed: {e}"); return False

# --------- Header ---------
st.markdown(f"<h1 style='text-align:center; color:#2E86C1;'>{APP_TITLE}</h1>", unsafe_allow_html=True)
st.markdown(f"<h2 style='text-align:center; color:#117A65;'>{APP_SUBTITLE}</h2>", unsafe_allow_html=True)
st.markdown("<hr style='margin:20px 0;'>", unsafe_allow_html=True)

# --------- Auth ---------
def signup_form():
    st.subheader("Create an account")
    with st.form("signup"):
        email = st.text_input("Email"); full_name = st.text_input("Full name")
        role = st.selectbox("Role", ["student","manager","admin"])
        pw1 = st.text_input("Password", type="password"); pw2 = st.text_input("Confirm", type="password")
        ok = st.form_submit_button("Sign up")
        if ok:
            if not email or pw1!=pw2: st.error("Check email and matching passwords"); return
            if SUPA:
                SUPA.table("users").insert({"email":email,"full_name":full_name,"role":role,"password_hash":pw_hash(pw1),"must_change_password":True,"active":True}).execute()
                st.success("Account created.")
            else:
                users = load_json(USERS_FILE, {})
                if email in users: st.error("Account exists."); return
                users[email] = {"full_name":full_name,"role":role,"password_hash":pw_hash(pw1),"must_change_password":True,"active":True}
                save_json(USERS_FILE, users); st.success("Account created (local).")

def login_form():
    st.sidebar.header("🔑 Login")
    email = st.sidebar.text_input("Email", key="login_email")
    pw = st.sidebar.text_input("Password", type="password", key="login_pw")
    if st.sidebar.button("Login"):
        if SUPA:
            res = SUPA.table("users").select("*").eq("email", email).eq("active", True).execute().data
            if not res: st.sidebar.error("No user or inactive."); return
            u = res[0]
            if pw_ok(pw, u["password_hash"]):
                st.session_state.update(auth=True, user_email=u["email"], role=u["role"], full_name=u.get("full_name") or u["email"], must_change_password=bool(u.get("must_change_password", False)))
                st.experimental_rerun()
            else: st.sidebar.error("Incorrect password")
        else:
            users = load_json(USERS_FILE, {}); u = users.get(email)
            if not u or not u.get("active", True): st.sidebar.error("No user or inactive."); return
            if pw_ok(pw, u["password_hash"]):
                st.session_state.update(auth=True, user_email=email, role=u["role"], full_name=u.get("full_name") or email, must_change_password=bool(u.get("must_change_password", False)))
                st.experimental_rerun()
            else: st.sidebar.error("Incorrect password")

    with st.sidebar.expander("Forgot password?"):
        fp_email = st.text_input("Your account email")
        if st.button("Send reset code"):
            code = ''.join(secrets.choice(string.digits) for _ in range(6))
            st.session_state.setdefault("reset_codes", {})[fp_email] = {"code": code, "exp": time.time()+1200}
            sent = send_email(fp_email, "Gradspace reset code", f"Your reset code: {code}\nExpires in 20 minutes.")
            st.success("Code sent." if sent else "Email not configured; copy code below.")
            if not sent: st.code(code)

    with st.sidebar.expander("I have a reset code"):
        rc_email = st.text_input("Email for reset")
        rc_code = st.text_input("Reset code"); new_pw = st.text_input("New password", type="password")
        if st.button("Confirm reset"):
            rec = (st.session_state.get("reset_codes") or {}).get(rc_email)
            if not rec or time.time()>rec["exp"] or rc_code!=rec["code"]: st.error("Invalid/expired code."); return
            h = pw_hash(new_pw)
            if SUPA: SUPA.table("users").update({"password_hash":h,"must_change_password":False}).eq("email", rc_email).execute()
            else:
                users = load_json(USERS_FILE, {}); 
                if rc_email in users: users[rc_email]["password_hash"]=h; users[rc_email]["must_change_password"]=False; save_json(USERS_FILE, users)
            st.success("Password updated.")

def force_change_password_gate():
    st.warning("You must change your password before continuing.")
    new1 = st.text_input("New password", type="password"); new2 = st.text_input("Confirm new password", type="password")
    if st.button("Update password"):
        if new1 and new1==new2:
            h = pw_hash(new1)
            if SUPA: SUPA.table("users").update({"password_hash":h,"must_change_password":False}).eq("email", st.session_state["user_email"]).execute()
            else:
                users = load_json(USERS_FILE, {}); users[st.session_state["user_email"]]["password_hash"]=h; users[st.session_state["user_email"]]["must_change_password"]=False; save_json(USERS_FILE, users)
            st.session_state["must_change_password"]=False; st.success("Password updated."); st.experimental_rerun()
        else: st.error("Passwords must match.")

# --------- Student Face Page ---------
def student_face_page():
    st.subheader("🎓 My Dashboard")
    email = st.session_state["user_email"]
    # Load student/invoices/payments
    inv=bls=pays=[]; srec=None
    if SUPA:
        u = SUPA.table("users").select("id,full_name").eq("email", email).execute().data
        uid = u and u[0]["id"]
        s = SUPA.table("students").select("*").eq("user_id", uid).execute().data
        srec = s and s[0]
        sid = srec and srec["id"]
        inv = SUPA.table("invoices").select("*").eq("student_id", sid).execute().data if sid else []
        bls = SUPA.table("bills").select("*").eq("student_id", sid).execute().data if sid else []
        pays = SUPA.table("payments").select("*").eq("student_id", sid).execute().data if sid else []
        cmts = SUPA.table("comments").select("*").eq("student_id", sid).order("created_at", desc=True).execute().data if sid else []
    else:
        st.info("Local mode: student page needs local data seeded.")

    col1, col2 = st.columns([2,1])
    with col1:
        st.markdown("**Profile**")
        st.json(srec or {})
    with col2:
        total_due = sum(float(i.get("amount",0)) for i in inv) + sum(float(b.get("amount",0)) for b in bls) - sum(float(p.get("amount",0)) for p in pays)
        st.metric("Current Balance", f"{total_due:.2f} {local_settings['billing']['currency']}")

    st.markdown("### 📑 Bills & Invoices")
    st.dataframe(pd.DataFrame(inv+bls), use_container_width=True) if (inv or bls) else st.info("No invoices/bills.")
    st.markdown("### 💳 Payments")
    st.dataframe(pd.DataFrame(pays), use_container_width=True) if pays else st.info("No payments.")

    st.markdown("### 💬 Comments to Management")
    msg = st.text_area("Write a message")
    if st.button("Send message"):
        if SUPA and srec:
            SUPA.table("comments").insert({"student_id": srec["id"], "sender":"student", "message": msg}).execute()
            st.success("Message sent.")

# --------- Admin/Manager Pages ---------
def page_students():
    st.subheader("👩🏽‍🎓 Students")
    data = SUPA.table("students").select("*").execute().data if SUPA else []
    st.dataframe(pd.DataFrame(data), use_container_width=True)
    with st.expander("➕ Add / Update student"):
        email = st.text_input("User Email"); suite = st.text_input("Suite/Room")
        rent = st.number_input("Rent", value=float(local_settings["billing"]["default_rent"]), step=50.0)
        utilities = st.number_input("Utilities", value=float(local_settings["billing"]["default_utilities"]), step=10.0)
        kin = st.text_input("Next of kin"); kin_phone = st.text_input("Kin phone"); address = st.text_area("Address")
        if st.button("Save student") and SUPA:
            uid = (SUPA.table("users").select("id").eq("email", email).execute().data or [{}])[0].get("id")
            SUPA.table("students").insert({"user_id": uid, "suite": suite, "rent": rent, "utilities": utilities, "next_of_kin": kin, "kin_phone": kin_phone, "address": address}).execute()
            st.success("Saved.")

def page_invoices():
    st.subheader("📄 Invoices & Payments")
    inv = SUPA.table("invoices").select("*").order("created_at", desc=True).execute().data if SUPA else []
    pays = SUPA.table("payments").select("*").order("paid_at", desc=True).execute().data if SUPA else []
    st.write("**Invoices**"); st.dataframe(pd.DataFrame(inv), use_container_width=True)
    st.write("**Payments**"); st.dataframe(pd.DataFrame(pays), use_container_width=True)

def page_maintenance():
    st.subheader("🛠 Maintenance")
    jobs = SUPA.table("maintenance").select("*").execute().data if SUPA else []
    st.dataframe(pd.DataFrame(jobs), use_container_width=True)

def page_messages():
    st.subheader("💬 Student Messages")
    msgs = SUPA.table("comments").select("*").order("created_at", desc=True).execute().data if SUPA else []
    st.dataframe(pd.DataFrame(msgs), use_container_width=True) if msgs else st.info("No messages.")

def page_settings():
    st.subheader("⚙️ Settings")
    st.markdown("**Branding**")
    title = st.text_input("App title", value=local_settings["branding"]["title"])
    primary = st.text_input("Primary color", value=local_settings["branding"]["primary"])
    if st.button("Save branding"):
        local_settings["branding"] = {"title": title, "primary": primary}; save_json(os.path.join(DATA_DIR,"settings.json"), local_settings); st.success("Saved (local). Store in Supabase.settings for cloud persistence.")

    st.markdown("---")
    st.markdown("**Billing defaults**")
    currency = st.text_input("Currency", value=local_settings["billing"]["currency"])
    def_rent = st.number_input("Default rent", value=float(local_settings["billing"]["default_rent"]), step=50.0)
    def_util = st.number_input("Default utilities", value=float(local_settings["billing"]["default_utilities"]), step=10.0)
    if st.button("Save billing"):
        local_settings["billing"] = {"currency": currency, "default_rent": def_rent, "default_utilities": def_util}
        save_json(os.path.join(DATA_DIR,"settings.json"), local_settings); st.success("Saved.")

    st.markdown("---")
    st.markdown("**Notifications**")
    email_inv = st.checkbox("Email new invoices", value=local_settings["notify"]["email_invoices"])
    email_od = st.checkbox("Email overdue invoices", value=local_settings["notify"]["email_overdue"])
    cc_mgr = st.checkbox("CC managers on reminders", value=local_settings["notify"]["cc_manager"])
    tmpl_i = st.text_area("Invoice email template", value=local_settings["notify"]["template_invoice"])
    tmpl_o = st.text_area("Overdue email template", value=local_settings["notify"]["template_overdue"])
    if st.button("Save notifications"):
        local_settings["notify"] = {"email_invoices": email_inv, "email_overdue": email_od, "cc_manager": cc_mgr,
                                    "template_invoice": tmpl_i, "template_overdue": tmpl_o}
        save_json(os.path.join(DATA_DIR,"settings.json"), local_settings); st.success("Saved.")

    st.markdown("---")
    st.markdown("**Admin: Create user**")
    um_email = st.text_input("Email"); um_name = st.text_input("Full name")
    um_role = st.selectbox("Role", ["student","manager","admin"])
    if st.button("Create user"):
        if SUPA:
            SUPA.table("users").insert({"email": um_email, "full_name": um_name, "role": um_role, "password_hash": pw_hash(secrets.token_urlsafe(8)), "must_change_password": True, "active": True}).execute()
            st.success("User created; must change password on first login.")

# --------- Router ---------
def main_router():
    role = st.session_state.get("role","student")
    st.sidebar.success(f"Signed in as {st.session_state.get('full_name')} ({role})")
    if st.sidebar.button("Sign out"):
        for k in ["auth","user_email","role","full_name","must_change_password"]: st.session_state.pop(k, None)
        st.experimental_rerun()

    if st.session_state.get("must_change_password"):
        force_change_password_gate(); st.stop()

    tabs = ["Student"] if role=="student" else ["Students","Invoices","Maintenance","Messages","Settings"] if role=="admin" else ["Students","Invoices","Maintenance","Messages"]
    choice = st.sidebar.radio("Navigate", tabs)
    if choice=="Student": student_face_page()
    elif choice=="Students": page_students()
    elif choice=="Invoices": page_invoices()
    elif choice=="Maintenance": page_maintenance()
    elif choice=="Messages": page_messages()
    else: page_settings()

if not st.session_state.get("auth"):
    colA, colB = st.columns(2)
    with colA: login_form()
    with colB: signup_form()
else:
    main_router()
