
import streamlit as st
import pandas as pd
from datetime import date
import urllib.parse
import smtplib
from email.mime.text import MIMEText
try:
    from email_validator import validate_email, EmailNotValidError
    HAS_EMAIL_VALIDATOR = True
except Exception:
    HAS_EMAIL_VALIDATOR = False

st.set_page_config(page_title="Gradspace Accommodation", page_icon="🏠", layout="wide")

# -----------------------------
# Helpers
# -----------------------------
def get_csv_download(df: pd.DataFrame, filename: str, label: str):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label, csv, filename, "text/csv")

def send_email_via_smtp(to_email: str, subject: str, body: str) -> str:
    """Send email using SMTP credentials stored in Streamlit secrets.
    Secrets to add in Streamlit Cloud → App → Settings → Secrets:
    EMAIL_HOST="smtp.gmail.com"
    EMAIL_PORT=587
    EMAIL_USER="you@example.com"
    EMAIL_PASS="your_app_password"
    EMAIL_FROM="Gradspace <you@example.com>"
    """
    try:
        if HAS_EMAIL_VALIDATOR:
            validate_email(to_email)

        host = st.secrets.get("EMAIL_HOST", "smtp.gmail.com")
        port = int(st.secrets.get("EMAIL_PORT", 587))
        user = st.secrets["EMAIL_USER"]
        password = st.secrets["EMAIL_PASS"]
        from_addr = st.secrets.get("EMAIL_FROM", user)

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_email

        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, [to_email], msg.as_string())
        return "OK"
    except Exception as e:
        return f"ERROR: {e}"

def money(n):
    try:
        return f"${float(n):,.2f}"
    except Exception:
        return str(n)

# -----------------------------
# In-memory storage (demo)
# -----------------------------
if "users" not in st.session_state:
    st.session_state["users"] = {
        "admin": {"password": "admin123", "role": "Admin"},
        "manager": {"password": "manager123", "role": "Manager"},
        "staff": {"password": "staff123", "role": "Staff"},
    }
if "students" not in st.session_state:
    st.session_state["students"] = []  # list[dict]
if "tasks" not in st.session_state:
    st.session_state["tasks"] = []     # list[dict]
if "role" not in st.session_state:
    st.session_state["role"] = None
if "who" not in st.session_state:
    st.session_state["who"] = None

# -----------------------------
# Login
# -----------------------------
st.title("🔐 Gradspace Login")
c1, c2, c3 = st.columns([1,1,1])
with c1:
    username = st.text_input("Username")
with c2:
    password = st.text_input("Password", type="password")
with c3:
    if st.button("Login", type="primary"):
        users = st.session_state["users"]
        if username in users and users[username]["password"] == password:
            st.session_state["role"] = users[username]["role"]
            st.session_state["who"] = username
            st.success(f"✅ Logged in as {st.session_state['role']} ({username})")
        else:
            st.error("❌ Invalid username or password")
logout_col = st.columns(1)[0]
if st.session_state.get("role"):
    if logout_col.button("Logout"):
        for k in ["role", "who"]:
            st.session_state.pop(k, None)
        st.info("You have been logged out.")

st.divider()

if not st.session_state.get("role"):
    st.info("Log in to continue.")
    st.stop()

role = st.session_state["role"]

# ==================================================
# Admin Dashboard
# ==================================================
if role == "Admin":
    st.header("👑 Admin Dashboard")
    tabs = st.tabs(["Users", "Students (Delete)", "Maintenance (Delete)"])

    # --- Users ---
    with tabs[0]:
        st.subheader("Manage Users")
        users = st.session_state["users"]
        df_users = pd.DataFrame([{"Username": u, "Role": users[u]["role"]} for u in users])
        st.dataframe(df_users, use_container_width=True)

        st.markdown("**Add New User**")
        with st.form("add_user"):
            new_u = st.text_input("Username (lowercase, no spaces)")
            new_p = st.text_input("Password", type="password")
            new_r = st.selectbox("Role", ["Admin", "Manager", "Staff"])
            add_user_btn = st.form_submit_button("Add User")
            if add_user_btn:
                if not new_u or not new_p:
                    st.error("Username and password are required.")
                elif new_u in users:
                    st.error("Username already exists.")
                else:
                    users[new_u] = {"password": new_p, "role": new_r}
                    st.success(f"✅ Added user: {new_u} ({new_r})")

        st.markdown("**Delete User**")
        del_u = st.selectbox("Select user to delete", list(users.keys()))
        if st.button("Delete Selected User"):
            if del_u == st.session_state.get("who"):
                st.error("You cannot delete the account you're logged in with.")
            else:
                users.pop(del_u, None)
                st.success(f"🗑 Deleted user: {del_u}")

    # --- Delete Students ---
    with tabs[1]:
        st.subheader("Delete Student Records")
        if st.session_state["students"]:
            df = pd.DataFrame(st.session_state["students"]).copy()
            if "Photo" in df.columns:
                df = df.drop(columns=["Photo"])
            st.dataframe(df, use_container_width=True)
            pick = st.selectbox("Select student to delete", [s["Name"] for s in st.session_state["students"]])
            if st.button("Delete Student Record"):
                st.session_state["students"] = [s for s in st.session_state["students"] if s["Name"] != pick]
                st.success(f"🗑 Deleted record for {pick}")
        else:
            st.info("No student records.")

    # --- Delete Maintenance ---
    with tabs[2]:
        st.subheader("Delete Maintenance Tasks")
        if st.session_state["tasks"]:
            df = pd.DataFrame(st.session_state["tasks"]).copy()
            if "Before" in df.columns:
                df["Before"] = df["Before"].apply(lambda x: "Yes" if x else "No")
            if "After" in df.columns:
                df["After"] = df["After"].apply(lambda x: "Yes" if x else "No")
            st.dataframe(df, use_container_width=True)
            pick_t = st.selectbox("Select task to delete", [t["Title"] for t in st.session_state["tasks"]])
            if st.button("Delete Task Record"):
                st.session_state["tasks"] = [t for t in st.session_state["tasks"] if t["Title"] != pick_t]
                st.success(f"🗑 Deleted task: {pick_t}")
        else:
            st.info("No maintenance tasks.")

# ==================================================
# Manager Dashboard
# ==================================================
elif role == "Manager":
    st.header("📋 Manager Dashboard")
    tabs = st.tabs(["Add Student", "Student Records", "Invoices & Reminders"])

    # --- Add Student ---
    with tabs[0]:
        st.subheader("➕ Add Student Record")
        with st.form("add_student"):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Student Full Name")
                suite = st.selectbox("Suite", ["Gradspace Suite 1", "Gradspace Suite 2"])
                room = st.text_input("Room Number (no limit)")
                entry_date = st.date_input("Entry Date", value=date.today())
                exit_date = st.date_input("Exit Date", value=date.today())
                home_address = st.text_area("Home Address")
            with c2:
                rent = st.number_input("Monthly Rent", min_value=0, step=50)
                rent_paid = st.selectbox("Rent Paid", ["No", "Yes"])
                electricity = st.number_input("Electricity Bill", min_value=0, step=10)
                water = st.number_input("Water Bill", min_value=0, step=10)
                internet = st.number_input("Internet Bill", min_value=0, step=10)
                other = st.number_input("Other Utilities", min_value=0, step=10)
                phone = st.text_input("Phone (+countrycode, e.g., +64...)")
                email = st.text_input("Email")

            st.markdown("**Next of Kin**")
            nk1, nk2 = st.columns(2)
            with nk1:
                nok_name = st.text_input("Next of Kin Name")
                nok_relationship = st.text_input("Relationship (Parent, Sibling, etc.)")
            with nk2:
                nok_contact = st.text_input("Next of Kin Contact (phone/email)")
                photo = st.file_uploader("Upload Profile Photo", type=["jpg", "jpeg", "png"])

            submitted = st.form_submit_button("Add Record")
            if submitted and name:
                total_due = 0 if rent_paid == "Yes" else rent
                total_due += electricity + water + internet + other
                st.session_state["students"].append({
                    "Name": name,
                    "Suite": suite,
                    "Room": room,
                    "Entry Date": entry_date,
                    "Exit Date": exit_date,
                    "Monthly Rent": rent,
                    "Rent Paid": rent_paid,
                    "Electricity": electricity,
                    "Water": water,
                    "Internet": internet,
                    "Other": other,
                    "Total Due": total_due,
                    "Phone": phone,
                    "Email": email,
                    "Home Address": home_address,
                    "Next of Kin": nok_name,
                    "Relationship": nok_relationship,
                    "NOK Contact": nok_contact,
                    "Photo": photo.read() if photo else None,
                })
                st.success(f"✅ Record added for {name}")

    # --- Student Records ---
    with tabs[1]:
        st.subheader("📋 Student Records")
        if st.session_state["students"]:
            df = pd.DataFrame(st.session_state["students"]).copy()
            if "Photo" in df.columns:
                df = df.drop(columns=["Photo"])
            def highlight_due(row):
                return ["background-color: #ffcccc"]*len(row) if row["Rent Paid"]=="No" else ["background-color: #ccffcc"]*len(row)
            st.dataframe(df.style.apply(highlight_due, axis=1), use_container_width=True)
            get_csv_download(df, "student_records.csv", "⬇️ Download CSV")

            # Delete
            del_name = st.selectbox("Select student to delete", [s["Name"] for s in st.session_state["students"]])
            if st.button("Delete Record"):
                st.session_state["students"] = [s for s in st.session_state["students"] if s["Name"] != del_name]
                st.success(f"🗑 Deleted record for {del_name}")

            # Show photo
            st.markdown("**Profile Photo Preview**")
            view_n = st.selectbox("View photo for", [s["Name"] for s in st.session_state["students"]])
            s = next(x for x in st.session_state["students"] if x["Name"] == view_n)
            if s.get("Photo"):
                st.image(s["Photo"], caption=view_n, use_container_width=True)
            else:
                st.info("No photo uploaded for this student.")

        else:
            st.info("No records yet.")

    # --- Invoices & Reminders ---
    with tabs[2]:
        st.subheader("💬 Send Invoice / Reminder (WhatsApp + Email)")
        if st.session_state["students"]:
            pick = st.selectbox("Select student", [s["Name"] for s in st.session_state["students"]])
            s = next(x for x in st.session_state["students"] if x["Name"] == pick)

            msg = f"""Hello {pick},
This is a rent reminder from Gradspace.
Suite: {s.get('Suite','')}  Room: {s.get('Room','')}
Total Due: {money(s.get('Total Due', 0))}

Please arrange payment as soon as possible. Thank you."""
            txt = st.text_area("Message", value=msg, height=140)

            # WhatsApp (pre-filled)
            phone = s.get("Phone")
            if phone:
                encoded = urllib.parse.quote(txt)
                wa_url = f"https://wa.me/{phone}?text={encoded}"
                st.markdown(f"[📲 Open WhatsApp Message]({wa_url})")
            else:
                st.warning("Student has no phone number saved.")

            # Email
            email_to = s.get("Email")
            if st.button("📧 Send Email Now"):
                if email_to:
                    status = send_email_via_smtp(email_to, "Gradspace Rent Invoice", txt)
                    if status == "OK":
                        st.success("✅ Email sent successfully")
                    else:
                        st.error(status + " — make sure EMAIL_* secrets are set in Streamlit Cloud.")
                else:
                    st.warning("Student has no email saved.")

        st.divider()
        st.subheader("⏰ Overdue Summary")
        dues = [x for x in st.session_state["students"] if x.get("Rent Paid") == "No"]
        if dues:
            for x in dues:
                st.warning(f"⚠️ {x['Name']} — {x['Suite']} / {x['Room']} — Owes {money(x['Total Due'])}")
        else:
            st.info("🎉 No overdue students.")

# ==================================================
# Staff Dashboard
# ==================================================
elif role == "Staff":
    st.header("🛠 Staff Dashboard")
    tabs = st.tabs(["Log Maintenance", "View / Delete Tasks"])

    with tabs[0]:
        st.subheader("➕ Log Maintenance / Expense")
        with st.form("add_task"):
            c1, c2 = st.columns(2)
            with c1:
                title = st.text_input("Task Title (e.g., Fix plumbing)")
                assigned = st.text_input("Assigned To (worker name)")
                status = st.selectbox("Status", ["Pending", "In Progress", "Completed"])
                when = st.date_input("Date", value=date.today())
            with c2:
                cost = st.number_input("Cost", min_value=0, step=50)
                before = st.file_uploader("Upload BEFORE photo", type=["jpg","jpeg","png"], key="before")
                after = st.file_uploader("Upload AFTER photo", type=["jpg","jpeg","png"], key="after")
            desc = st.text_area("Task Description")
            submit = st.form_submit_button("Add Task")
            if submit and title:
                st.session_state["tasks"].append({
                    "Title": title,
                    "Description": desc,
                    "Cost": cost,
                    "Assigned To": assigned,
                    "Date": when,
                    "Status": status,
                    "Before": before.read() if before else None,
                    "After": after.read() if after else None,
                })
                st.success(f"✅ Task logged: {title}")

    with tabs[1]:
        st.subheader("📋 Maintenance & Expenses")
        if st.session_state["tasks"]:
            df = pd.DataFrame(st.session_state["tasks"]).copy()
            for col in ["Before","After"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda b: "Yes" if b else "No")
            st.dataframe(df, use_container_width=True)
            get_csv_download(df, "maintenance_records.csv", "⬇️ Download CSV")

            pick_t = st.selectbox("Select task to view photos", [t["Title"] for t in st.session_state["tasks"]])
            t = next(x for x in st.session_state["tasks"] if x["Title"] == pick_t)
            c1, c2 = st.columns(2)
            with c1:
                if t.get("Before"):
                    st.image(t["Before"], caption="Before", use_container_width=True)
            with c2:
                if t.get("After"):
                    st.image(t["After"], caption="After", use_container_width=True)

            if st.button("Delete Selected Task"):
                st.session_state["tasks"] = [x for x in st.session_state["tasks"] if x["Title"] != pick_t]
                st.success(f"🗑 Deleted task: {pick_t}")
        else:
            st.info("No tasks logged yet.")
