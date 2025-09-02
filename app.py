import streamlit as st
import traceback
from supabase import create_client, Client

# =============================
# Error Wrapper
# =============================
def main():
    try:
        run_app()
    except Exception as e:
        st.error("🚨 An error occurred in the app")
        st.code(traceback.format_exc())

# =============================
# App Core
# =============================
def run_app():
    st.set_page_config(page_title="Gradspace", layout="centered")

    st.title("🔑 Gradspace Login")

    # Connect Supabase
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    supabase: Client = create_client(url, key)

    # Login form
    with st.form("login_form"):
        username = st.text_input("Username / Email / Student ID")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

    if submit:
        if not username or not password:
            st.warning("⚠️ Please enter both username and password")
            return

        try:
            response = supabase.table("users").select("*").eq("username", username).execute()

            if not response.data:
                st.error("❌ Invalid username or password")
                return

            user = response.data[0]

            # Demo password check (replace with hash validation later)
            if password == "Admin@123" and user["role"] == "admin":
                admin_dashboard(user)
            elif password == "Student@123" and user["role"] == "student":
                student_dashboard(user)
            else:
                st.error("❌ Invalid login.")
        except Exception as e:
            st.error("Database error")
            st.code(traceback.format_exc())

# =============================
# Admin Dashboard
# =============================
def admin_dashboard(user):
    st.success(f"👑 Admin Dashboard — {user['username']}")

    menu = st.sidebar.radio("📌 Navigation", ["Students", "Resets", "Backups"])

    if menu == "Students":
        st.subheader("👥 Manage Students")
        st.write("Add, edit, and manage student profiles, invoices, and maintenance.")
    elif menu == "Resets":
        st.subheader("🔄 Reset Logs")
        st.write("View student password reset requests.")
    elif menu == "Backups":
        st.subheader("💾 Backups")
        st.write("Download and restore backups of student data.")

# =============================
# Student Dashboard
# =============================
def student_dashboard(user):
    st.success(f"🎓 Student Dashboard — {user['username']}")

    menu = st.sidebar.radio("📌 Navigation", ["Profile", "Invoices", "Maintenance"])

    if menu == "Profile":
        st.subheader("👤 My Profile")
        st.write("Student details and contact info here.")
    elif menu == "Invoices":
        st.subheader("📄 My Invoices")
        st.write("View and download your invoices.")
    elif menu == "Maintenance":
        st.subheader("🛠 Maintenance Requests")
        st.write("Submit and track maintenance issues.")

# =============================
# Run App
# =============================
if __name__ == "__main__":
    main()
