# Gradspace Student Accommodation App

This is a student accommodation management app built with **Streamlit** and **Supabase**.

## 🚀 Features
- Secure login (Admin / Student / Staff)
- Student profiles, invoices, and reminders
- Maintenance and staff management
- Cron worker for scheduled tasks
- Supabase database integration
- QR code login & private app sharing (future upgrade)

---

## 📦 Setup Instructions

### 1. Clone Repository
```bash
git clone https://github.com/jackmdlalose91-rgb/gradspace-student-accommodation.git
cd gradspace-student-accommodation
```

### 2. Install Requirements
```bash
pip install -r requirements.txt
```

### 3. Configure Secrets
Create a `.streamlit/secrets.toml` file:

```toml
[supabase]
url = "https://YOUR_PROJECT_ID.supabase.co"
anon_key = "YOUR_ANON_PUBLIC_KEY"
```

⚠️ Replace with your actual Supabase credentials from **Project Settings → API**.

### 4. Initialize Database
Run the schema file in Supabase SQL Editor:

```sql
-- schema.sql contents
```

Insert an admin account manually:
```sql
insert into users (id, username, email, role, password_hash, first_login)
values (
  'admin-0001',
  'admin',
  'admin@example.com',
  'admin',
  crypt('Admin@123', gen_salt('bf')),  
  false
);
```

### 5. Run Locally
```bash
streamlit run app.py
```

### 6. Deploy to Streamlit Cloud
- Push all changes to GitHub
- Go to [Streamlit Cloud](https://share.streamlit.io/)
- Deploy your repo

### 7. Logs (Debugging)
If app shows a blank page, check logs:
- Open your app in Streamlit Cloud
- Go to **⋮ Menu → Settings → Logs**
- Fix missing libraries by editing `requirements.txt`

---

## 🔑 Default Admin Login
- **Username:** admin
- **Password:** Admin@123

(Change after first login)

---

## 📌 Notes
- Use Supabase for database + authentication
- Make sure `.streamlit/secrets.toml` is correct
- If QR code login/private link is required → enable via settings (future step)
