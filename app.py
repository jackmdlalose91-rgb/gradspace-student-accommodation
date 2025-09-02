
import streamlit as st
import traceback
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from datetime import date, datetime

# =============================
# Global Setup
# =============================
st.set_page_config(page_title="Gradspace", layout="wide")

def get_sb() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)

def toast(msg, icon="✅"):
    st.toast(f"{icon} {msg}", icon=icon)

# Simple helpers
def q_table(sb: Client, table: str, select:str="*", **filters):
    q = sb.table(table).select(select)
    for k, v in filters.items():
        q = q.eq(k, v)
    return q.execute().data

def upsert(sb: Client, table: str, row: Dict[str, Any]):
    return sb.table(table).upsert(row, returning="representation").execute().data

def insert(sb: Client, table: str, row: Dict[str, Any]):
    return sb.table(table).insert(row, returning="representation").execute().data

def delete(sb: Client, table: str, match: Dict[str, Any]):
    return sb.table(table).delete().match(match).execute().data

# =============================
# Login
# =============================
def authenticate(sb: Client, username: str, password: str) -> Optional[Dict[str, Any]]:
    # NOTE: Demo check – replace with bcrypt hash verification later
    # Admin: Admin@123, Student: Student@123, Staff: Staff@123
    res = sb.table("users").select("*").or_(f"username.eq.{username},email.eq.{username},id.eq.{username}").execute()
    if not res.data:
        return None
    u = res.data[0]
    role = u.get("role", "student")
    valid = (role == "admin" and password == "Admin@123") or \
            (role == "student" and password == "Student@123") or \
            (role == "staff" and password == "Staff@123")
    return u if valid else None

# =============================
# UI Sections
# =============================
def header(user: Optional[Dict[str, Any]]):
    st.markdown("<h1 style='text-align:center;'>🏠 Gradspace Student Accommodation</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:gray;'>Installable web app • Admin, Staff & Student portals</p>", unsafe_allow_html=True)
    st.markdown("---")
    if user:
        st.success(f"Signed in as **{user['username']}** ({user['role']})")

def login_view(sb: Client):
    st.markdown("### 🔑 Gradspace Login")
    with st.form("login_form"):
        username = st.text_input("Username / Email / Student ID")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            user = authenticate(sb, username, password)
            if user:
                st.session_state.user = user
                toast("Logged in")
                st.rerun()
            else:
                st.error("Invalid login.")

    st.markdown("---")
    st.markdown("#### 📌 Navigation")
    st.markdown("- 👥 Students")
    st.markdown("- 🏢 Rooms")
    st.markdown("- 📄 Invoices")
    st.markdown("- 🛠 Maintenance")
    st.markdown("- 👷 Staff")
    st.markdown("- 🔄 Resets")
    st.markdown("- 💾 Backups")

# ---------- Pages ----------
def page_students(sb: Client):
    st.subheader("👥 Students")
    col1, col2 = st.columns([1.2, 2])
    with col1:
        st.markdown("##### Add / Update Student")
        sid = st.text_input("Student ID")
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        room = st.text_input("Room Number")
        join_date = st.date_input("Join Date", value=date.today())
        if st.button("Save Student"):
            if not sid or not name:
                st.warning("Student ID and Name are required")
            else:
                row = {
                    "id": sid, "name": name, "email": email or None,
                    "phone": phone or None, "room": room or None,
                    "join_date": str(join_date)
                }
                upsert(sb, "students", row)
                toast("Student saved")
                st.rerun()
        if st.button("Delete Student", type="secondary"):
            if not sid:
                st.warning("Enter Student ID to delete")
            else:
                delete(sb, "students", {"id": sid})
                toast("Student deleted", "🗑️")
                st.rerun()

    with col2:
        st.markdown("##### Current Students")
        data = q_table(sb, "students", "*")
        if data:
            import pandas as pd
            st.dataframe(pd.DataFrame(data))
        else:
            st.info("No students yet. Add the first student on the left.")

def page_rooms(sb: Client):
    st.subheader("🏢 Rooms")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("##### Add / Update Room")
        room_no = st.text_input("Room Number")
        capacity = st.number_input("Capacity", 1, 6, 1)
        status = st.selectbox("Status", ["available", "occupied", "maintenance"])
        if st.button("Save Room"):
            if not room_no:
                st.warning("Room number is required")
            else:
                upsert(sb, "rooms", {"room_no": room_no, "capacity": int(capacity), "status": status})
                toast("Room saved")
                st.rerun()
        if st.button("Delete Room", type="secondary"):
            if not room_no:
                st.warning("Enter Room Number to delete")
            else:
                delete(sb, "rooms", {"room_no": room_no})
                toast("Room deleted", "🗑️")
                st.rerun()

    with col2:
        st.markdown("##### Rooms List")
        data = q_table(sb, "rooms", "*")
        if data:
            import pandas as pd
            st.dataframe(pd.DataFrame(data))
        else:
            st.info("No rooms yet. Add the first room on the left.")

def page_invoices(sb: Client):
    st.subheader("📄 Invoices")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("##### Create Invoice")
        student_id = st.text_input("Student ID")
        amount = st.number_input("Amount", min_value=0.0, step=10.0)
        due = st.date_input("Due Date", value=date.today())
        status = st.selectbox("Status", ["unpaid", "paid", "overdue"], index=0)
        if st.button("Save Invoice"):
            if not student_id or amount <= 0:
                st.warning("Student ID and positive amount are required")
            else:
                insert(sb, "invoices", {
                    "student_id": student_id,
                    "amount": float(amount),
                    "due_date": str(due),
                    "status": status
                })
                toast("Invoice saved")
                st.rerun()

    with col2:
        st.markdown("##### All Invoices")
        data = q_table(sb, "invoices", "*")
        if data:
            import pandas as pd
            st.dataframe(pd.DataFrame(data))
        else:
            st.info("No invoices yet.")

def page_maintenance(sb: Client):
    st.subheader("🛠 Maintenance")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("##### Log Issue")
        student_id = st.text_input("Student ID (optional)")
        issue = st.text_area("Issue")
        status = st.selectbox("Status", ["open", "in_progress", "resolved"], index=0)
        if st.button("Save Issue"):
            if not issue.strip():
                st.warning("Issue is required")
            else:
                insert(sb, "maintenance", {
                    "student_id": student_id or None,
                    "issue": issue.strip(),
                    "status": status
                })
                toast("Issue logged")
                st.rerun()

    with col2:
        st.markdown("##### Maintenance Log")
        data = q_table(sb, "maintenance", "*")
        if data:
            import pandas as pd
            st.dataframe(pd.DataFrame(data))
        else:
            st.info("No maintenance items yet.")

def page_staff(sb: Client):
    st.subheader("👷 Staff")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("##### Add / Update Staff")
        uid = st.text_input("User ID")
        username = st.text_input("Username")
        email = st.text_input("Email")
        role = st.selectbox("Role", ["staff", "admin", "student"], index=0)
        first_login = st.checkbox("Require password change on first login", value=True)
        if st.button("Save Staff"):
            if not uid or not username or not email:
                st.warning("ID, username and email required")
            else:
                # default demo password rule by role
                pwd = "Staff@123" if role == "staff" else ("Admin@123" if role == "admin" else "Student@123")
                upsert(sb, "users", {
                    "id": uid, "username": username, "email": email,
                    "role": role, "password_hash": pwd, "first_login": first_login
                })
                toast("Staff saved")
                st.rerun()
        if st.button("Delete Staff", type="secondary"):
            if not uid:
                st.warning("Enter User ID to delete")
            else:
                delete(sb, "users", {"id": uid})
                toast("Staff deleted", "🗑️")
                st.rerun()

    with col2:
        st.markdown("##### Staff List")
        data = q_table(sb, "users", "*")
        if data:
            import pandas as pd
            st.dataframe(pd.DataFrame(data))
        else:
            st.info("No users yet.")

def page_resets(sb: Client):
    st.subheader("🔄 Resets")
    st.info("Password reset flow will email a temporary code and force update on next login (to be enabled when SMTP is configured).")

def page_backups(sb: Client):
    st.subheader("💾 Backups")
    st.info("Export CSV/JSON of students, rooms, invoices, and maintenance (coming soon).")

# =============================
# Main
# =============================
def main():
    try:
        sb = get_sb()
        user = st.session_state.get("user")
        header(user)

        if not user:
            login_view(sb)
            return

        # Sidebar navigation
        menu = st.sidebar.radio(
            "📌 Navigation",
            ["Students", "Rooms", "Invoices", "Maintenance", "Staff", "Resets", "Backups"]
        )

        if menu == "Students":
            page_students(sb)
        elif menu == "Rooms":
            page_rooms(sb)
        elif menu == "Invoices":
            page_invoices(sb)
        elif menu == "Maintenance":
            page_maintenance(sb)
        elif menu == "Staff":
            page_staff(sb)
        elif menu == "Resets":
            page_resets(sb)
        elif menu == "Backups":
            page_backups(sb)

        st.sidebar.markdown("---")
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.rerun()

    except Exception:
        st.error("🚨 An error occurred in the app")
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
