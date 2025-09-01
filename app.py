
import streamlit as st
import pandas as pd
from datetime import date, datetime
import io
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

st.set_page_config(page_title="Gradspace Manager", page_icon="🏠", layout="wide")

# ------------------------------
# Auth & Secrets
# ------------------------------
DEFAULT_USERS = {
    "admin": {"password": "admin123", "role": "admin", "name": "Admin"},
    "manager": {"password": "manager123", "role": "manager", "name": "Manager"},
}

def get_users():
    users = {}
    try:
        # Expected format in secrets: 
        # [users]
        # admin = "admin123|admin|Admin Name"
        # manager = "manager123|manager|Manager Name"
        for k, v in st.secrets["users"].items():
            pwd, role, name = v.split("|")
            users[k] = {"password": pwd, "role": role, "name": name}
    except Exception:
        users = DEFAULT_USERS
    return users

USERS = get_users()

# ------------------------------
# Session State
# ------------------------------
def init_state():
    ss = st.session_state
    ss.setdefault("auth", {"logged_in": False, "username": None, "role": None, "name": None})
    ss.setdefault("students", [])   # list of dicts
    ss.setdefault("maintenance", [])# list of dicts
    ss.setdefault("staff", [])      # list of dicts
    ss.setdefault("suites", ["Gradspace Suite 1", "Gradspace Suite 2"])
    ss.setdefault("rooms", {})      # {suite: set(room_numbers)}
    ss.setdefault("uploads", {})    # {upload_id: {"name":..., "bytes":...}}
    ss.setdefault("invoices", [])

init_state()

# ------------------------------
# Helpers
# ------------------------------
def money(n):
    try:
        return f"${float(n):,.2f}"
    except Exception:
        return str(n)

def store_upload(file):
    if not file:
        return None
    key = f"{datetime.utcnow().timestamp()}_{file.name}"
    st.session_state["uploads"][key] = {
        "name": file.name,
        "bytes": file.getvalue(),
        "mime": file.type,
    }
    return key

def render_upload(key, width=150):
    if not key:
        return
    item = st.session_state["uploads"].get(key)
    if not item:
        return
    if item["mime"] and item["mime"].startswith("image/"):
        st.image(item["bytes"], width=width)
    else:
        st.download_button("Download file", item["bytes"], file_name=item["name"])

def send_email_smtp(to_email, subject, body):
    """
    Optional email via SMTP if secrets are present.
    Add to Secrets:
      SMTP_SERVER="smtp.gmail.com"
      SMTP_PORT=587
      EMAIL_USER="you@example.com"
      EMAIL_PASS="your-app-password"
    """
    try:
        smtp_server = st.secrets["email"]["SMTP_SERVER"]
        smtp_port = int(st.secrets["email"]["SMTP_PORT"])
        email_user = st.secrets["email"]["EMAIL_USER"]
        email_pass = st.secrets["email"]["EMAIL_PASS"]
    except Exception:
        st.warning("Email secrets not configured. Skipping send.")
        return False, "Email secrets missing"

    try:
        msg = MIMEMultipart()
        msg["From"] = email_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_user, email_pass)
            server.send_message(msg)
        return True, "Email sent"
    except Exception as e:
        return False, str(e)

def whatsapp_link(phone_e164, message):
    # phone should be in international format without "+" e.g., "64211234567"
    from urllib.parse import quote
    return f"https://wa.me/{phone_e164}?text={quote(message)}"

def mailto_link(email, subject, body):
    from urllib.parse import quote
    return f"mailto:{email}?subject={quote(subject)}&body={quote(body)}"

def invoice_text(student, amount, due_date):
    lines = [
        f"Invoice for {student.get('Name','')}",
        f"Suite: {student.get('Suite','')} Room: {student.get('Room','')}",
        f"Amount Due: {money(amount)}",
        f"Due Date: {due_date.isoformat() if isinstance(due_date, date) else due_date}",
        "",
        "Thank you,",
        "Gradspace Management"
    ]
    return "\n".join(lines)

def download_df_button(df, filename="export.csv", label="⬇️ Download CSV"):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label, csv, filename, "text/csv")

# ------------------------------
# Auth UI
# ------------------------------
def login_ui():
    st.markdown("### 🔐 Sign in")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign in")
    if submit:
        user = USERS.get(username)
        if user and user["password"] == password:
            st.session_state["auth"] = {
                "logged_in": True,
                "username": username,
                "role": user["role"],
                "name": user["name"],
            }
            st.success(f"Welcome {user['name']} ({user['role']})")
            st.rerun()
        else:
            st.error("Invalid username or password")

def topbar():
    col1, col2, col3 = st.columns([6,2,2])
    with col1:
        st.markdown("## 🏠 Gradspace Manager")
    with col2:
        st.caption(f"Signed in as **{st.session_state['auth']['name']}** ({st.session_state['auth']['role']})")
    with col3:
        if st.button("Sign out", use_container_width=True):
            st.session_state["auth"] = {"logged_in": False, "username": None, "role": None, "name": None}
            st.rerun()

# ------------------------------
# Pages
# ------------------------------
def page_students():
    st.markdown("### 👨‍🎓 Students")
    with st.expander("➕ Add / Update Student", expanded=True):
        with st.form("add_student"):
            name = st.text_input("Student Name *")
            suite = st.selectbox("Suite", st.session_state["suites"])
            room = st.text_input("Room Number (no limit) *")
            phone = st.text_input("Phone (for WhatsApp, use international without +)")
            email = st.text_input("Email")
            address = st.text_area("Home Address")
            next_kin = st.text_input("Next of Kin Name")
            kin_phone = st.text_input("Next of Kin Phone")
            entry_date = st.date_input("Entry Date", value=date.today())
            exit_date = st.date_input("Exit Date", value=date.today())
            rent = st.number_input("Monthly Rent", min_value=0.0, step=50.0)
            rent_paid = st.selectbox("Rent Paid", ["No", "Yes"])
            profile_photo = st.file_uploader("Profile Photo (optional)", type=["png","jpg","jpeg"])
            photo_key = store_upload(profile_photo) if profile_photo else None

            electricity = st.number_input("Electricity Bill", min_value=0.0, step=10.0)
            water = st.number_input("Water Bill", min_value=0.0, step=10.0)
            internet = st.number_input("Internet Bill", min_value=0.0, step=10.0)
            other = st.number_input("Other Utilities", min_value=0.0, step=10.0)

            submitted = st.form_submit_button("Save Student")
            if submitted:
                if not name or not room:
                    st.error("Name and Room are required")
                else:
                    total_due = (0 if rent_paid == "Yes" else rent) + electricity + water + internet + other
                    rec = {
                        "Name": name, "Suite": suite, "Room": room,
                        "Phone": phone, "Email": email, "Address": address,
                        "Next of Kin": next_kin, "Kin Phone": kin_phone,
                        "Entry Date": entry_date, "Exit Date": exit_date,
                        "Monthly Rent": rent, "Rent Paid": rent_paid,
                        "Electricity": electricity, "Water": water, "Internet": internet, "Other": other,
                        "Total Due": total_due, "Photo": photo_key,
                    }
                    # Replace if same (suite+room) exists, else add
                    idx = None
                    for i, s in enumerate(st.session_state["students"]):
                        if s["Suite"] == suite and s["Room"] == room:
                            idx = i; break
                    if idx is not None:
                        st.session_state["students"][idx] = rec
                        st.success(f"Updated {name} in {suite} / {room}")
                    else:
                        st.session_state["students"].append(rec)
                        st.success(f"Added {name} to {suite} / {room}")

    if st.session_state["students"]:
        df = pd.DataFrame(st.session_state["students"])
        st.dataframe(df, use_container_width=True)
        download_df_button(df, "students.csv", "⬇️ Download Students CSV")

        st.markdown("#### Actions")
        colA, colB, colC = st.columns(3)
        with colA:
            with st.form("delete_student"):
                del_suite = st.selectbox("Suite", st.session_state["suites"], key="del_suite")
                rooms = [s["Room"] for s in st.session_state["students"] if s["Suite"] == del_suite]
                del_room = st.selectbox("Room", sorted(set(rooms)), key="del_room")
                if st.form_submit_button("🗑️ Delete Student"):
                    st.session_state["students"] = [s for s in st.session_state["students"] if not (s["Suite"] == del_suite and s["Room"] == del_room)]
                    st.success("Student deleted")
        with colB:
            with st.form("invoice_student"):
                inv_suite = st.selectbox("Suite", st.session_state["suites"], key="inv_suite")
                rooms2 = [s["Room"] for s in st.session_state["students"] if s["Suite"] == inv_suite]
                inv_room = st.selectbox("Room", sorted(set(rooms2)), key="inv_room")
                due_date = st.date_input("Due date", value=date.today())
                if st.form_submit_button("📄 Create Invoice"):
                    stu = next((s for s in st.session_state["students"] if s["Suite"] == inv_suite and s["Room"] == inv_room), None)
                    if stu:
                        amount = stu.get("Total Due", 0.0)
                        text = invoice_text(stu, amount, due_date)
                        st.code(text)
                        # WhatsApp & Email Links
                        if stu.get("Phone"):
                            st.link_button("Send via WhatsApp", whatsapp_link(stu["Phone"], text))
                        if stu.get("Email"):
                            st.link_button("Send via Email (open mail app)", mailto_link(stu["Email"], "Rent Invoice", text))
                        st.session_state["invoices"].append({"Suite": inv_suite, "Room": inv_room, "Name": stu.get("Name",""), "Amount": amount, "Due": str(due_date), "Created": datetime.now().isoformat(timespec="seconds")})
                        st.success("Invoice prepared")
        with colC:
            st.markdown("Upload Preview")
            # Show selected student's photo
            try:
                sel = st.session_state.get("del_room") or st.session_state.get("inv_room")
                if sel:
                    stu = next((s for s in st.session_state["students"] if s["Room"] == sel), None)
                    if stu and stu.get("Photo"):
                        render_upload(stu["Photo"], width=180)
            except Exception:
                pass
    else:
        st.info("No students yet. Use the form above.")

def page_maintenance():
    st.markdown("### 🛠️ Maintenance & Grounds")
    with st.expander("➕ Log Maintenance Job", expanded=True):
        with st.form("add_job"):
            suite = st.selectbox("Suite", st.session_state["suites"], key="m_suite")
            room = st.text_input("Room (optional)", key="m_room")
            title = st.text_input("Job Title *")
            desc = st.text_area("Description")
            worker = st.text_input("Assigned To / Worker")
            cost = st.number_input("Cost", min_value=0.0, step=10.0)
            status = st.selectbox("Status", ["Open", "In Progress", "Done"])
            photo = st.file_uploader("Photo evidence (optional)", type=["png","jpg","jpeg"], key="m_photo")
            photo_key = store_upload(photo) if photo else None
            submit = st.form_submit_button("Save Job")
            if submit:
                if not title:
                    st.error("Job Title is required")
                else:
                    st.session_state["maintenance"].append({
                        "Suite": suite, "Room": room, "Title": title, "Desc": desc,
                        "Worker": worker, "Cost": cost, "Status": status, "Photo": photo_key,
                        "Logged": datetime.now().isoformat(timespec="seconds")
                    })
                    st.success("Job saved")

    if st.session_state["maintenance"]:
        df = pd.DataFrame(st.session_state["maintenance"])
        st.dataframe(df, use_container_width=True)
        download_df_button(df, "maintenance.csv", "⬇️ Download Jobs CSV")

        # Delete
        with st.form("del_job"):
            idx = st.number_input("Delete by row index", min_value=0, max_value=len(st.session_state["maintenance"])-1, step=1)
            if st.form_submit_button("🗑️ Delete Job"):
                st.session_state["maintenance"].pop(int(idx))
                st.success("Deleted job")
    else:
        st.info("No maintenance jobs yet.")

def page_staff():
    st.markdown("### 👷 Staff & Managers")
    with st.expander("➕ Add Staff", expanded=True):
        with st.form("add_staff"):
            name = st.text_input("Name *", key="st_name")
            role = st.selectbox("Role", ["manager", "maintenance", "grounds"])
            phone = st.text_input("Phone")
            email = st.text_input("Email")
            notes = st.text_area("Notes")
            if st.form_submit_button("Save Staff"):
                if not name:
                    st.error("Name is required")
                else:
                    st.session_state["staff"].append({
                        "Name": name, "Role": role, "Phone": phone, "Email": email, "Notes": notes
                    })
                    st.success("Staff saved")

    if st.session_state["staff"]:
        df = pd.DataFrame(st.session_state["staff"])
        st.dataframe(df, use_container_width=True)
        download_df_button(df, "staff.csv", "⬇️ Download Staff CSV")

        with st.form("del_staff"):
            idx = st.number_input("Delete by row index", min_value=0, max_value=len(st.session_state["staff"])-1, step=1, key="st_del")
            if st.form_submit_button("🗑️ Delete Staff"):
                st.session_state["staff"].pop(int(idx))
                st.success("Deleted staff")
    else:
        st.info("No staff yet.")

def page_invoices():
    st.markdown("### 💳 Invoices & Reminders")
    if st.session_state["students"]:
        with st.form("bulk_invoice"):
            target_suite = st.selectbox("Suite (optional)", ["All"] + st.session_state["suites"])
            due_date = st.date_input("Due date", value=date.today())
            note = st.text_area("Note (optional)", value="Rent due")
            if st.form_submit_button("Generate Invoices"):
                targets = st.session_state["students"]
                if target_suite != "All":
                    targets = [s for s in targets if s["Suite"] == target_suite]
                created = 0
                for s in targets:
                    amount = s.get("Total Due", 0.0)
                    text = invoice_text(s, amount, due_date) + ("\n\n" + note if note else "")
                    st.session_state["invoices"].append({
                        "Suite": s["Suite"], "Room": s["Room"], "Name": s.get("Name",""),
                        "Amount": amount, "Due": str(due_date),
                        "Created": datetime.now().isoformat(timespec="seconds")
                    })
                    # Show links
                    cols = st.columns([3,1,1])
                    with cols[0]:
                        st.code(text, language="text")
                    with cols[1]:
                        if s.get("Phone"):
                            st.link_button("WhatsApp", whatsapp_link(s["Phone"], text))
                    with cols[2]:
                        if s.get("Email"):
                            st.link_button("Email", mailto_link(s["Email"], "Rent Invoice", text))
                    created += 1
                st.success(f"Prepared {created} invoice(s)")
    else:
        st.info("Add students first.")

    if st.session_state["invoices"]:
        df = pd.DataFrame(st.session_state["invoices"])
        st.dataframe(df, use_container_width=True)
        download_df_button(df, "invoices.csv", "⬇️ Download Invoices CSV")

def page_settings():
    st.markdown("### ⚙️ Settings")
    st.write("**Suites**")
    with st.form("suite_form"):
        new_suite = st.text_input("Add new suite")
        if st.form_submit_button("Add Suite"):
            if new_suite and new_suite not in st.session_state["suites"]:
                st.session_state["suites"].append(new_suite)
                st.success(f"Added suite: {new_suite}")
    st.write("Current suites:", ", ".join(st.session_state["suites"]) or "—")

    st.divider()
    st.write("**Demo Users**")
    st.json(USERS)

    st.info("To configure real users or email, set Streamlit **Secrets** in the Cloud dashboard.")

# ------------------------------
# Main
# ------------------------------
if not st.session_state["auth"]["logged_in"]:
    login_ui()
else:
    colA, colB = st.columns([3,1])
    with colA:
        st.markdown("## 🏠 Gradspace Student Accommodation Tracker")
    with colB:
        topbar()
    with st.sidebar:
        st.markdown("## 📋 Menu")
        page = st.radio("Go to", ["Students", "Maintenance", "Staff", "Invoices", "Settings"], label_visibility="collapsed")
    if page == "Students":
        page_students()
    elif page == "Maintenance":
        page_maintenance()
    elif page == "Staff":
        page_staff()
    elif page == "Invoices":
        page_invoices()
    elif page == "Settings":
        page_settings()
