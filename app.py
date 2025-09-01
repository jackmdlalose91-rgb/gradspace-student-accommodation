 
import streamlit as st
import pandas as pd
from datetime import date

# Initialize session state for data storage
if "students" not in st.session_state:
    st.session_state["students"] = []

st.title("🏠 Gradspace Student Accommodation Tracker")

# --- Add New Student Form ---
st.subheader("➕ Add Student Record")
with st.form("add_student"):
    name = st.text_input("Student Name")
    suite = st.selectbox("Suite", ["Gradspace Suite 1", "Gradspace Suite 2"])
    room = st.number_input("Room Number", min_value=1, step=1)  # unlimited rooms
    
    entry_date = st.date_input("Entry Date", value=date.today())
    exit_date = st.date_input("Exit Date", value=date.today())
    rent = st.number_input("Monthly Rent", min_value=0, step=50)
    rent_paid = st.selectbox("Rent Paid", ["No", "Yes"])
    
    # --- Extra student details ---
    student_email = st.text_input("Student Email")
    student_phone = st.text_input("Student Phone Number")
    student_address = st.text_area("Home Address")
    next_kin_name = st.text_input("Next of Kin Name")
    next_kin_contact = st.text_input("Next of Kin Contact")
    
    # Utility bills
    electricity = st.number_input("Electricity Bill", min_value=0, step=10)
    water = st.number_input("Water Bill", min_value=0, step=10)
    internet = st.number_input("Internet Bill", min_value=0, step=10)
    other = st.number_input("Other Utilities", min_value=0, step=10)

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
            "Email": student_email,
            "Phone": student_phone,
            "Address": student_address,
            "Next of Kin": next_kin_name,
            "Next of Kin Contact": next_kin_contact
        })
        st.success(f"✅ Record added for {name}")

# --- Display Records ---
st.subheader("📋 Student Records")
if st.session_state["students"]:
    df = pd.DataFrame(st.session_state["students"])

    # Highlight overdue (unpaid) vs paid
    def highlight_due(row):
        if row["Rent Paid"] == "No":
            return ["background-color: #ffcccc"] * len(row)  # light red
        else:
            return ["background-color: #ccffcc"] * len(row)  # light green

    st.dataframe(df.style.apply(highlight_due, axis=1))

    # Download option
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download CSV", csv, "student_records.csv", "text/csv")
else:
    st.info("No records yet. Add students using the form above.")
