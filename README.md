# Gradspace — Full Accommodation System (Streamlit + Supabase)

This app manages **students, rooms, invoices, maintenance, and staff** with a clean admin dashboard.

## 🧰 Tech
- Frontend: **Streamlit**
- DB: **Supabase (Postgres + REST)**
- Auth (demo): users table with role + demo passwords
- Deploy: Streamlit Cloud

---

## 🚀 Quick Start

### 1) Supabase: create tables
Open **Supabase → SQL Editor**, paste and run `schema.sql` from this repo.

### 2) Insert first admin
```sql
insert into users (id, username, email, role, password_hash, first_login)
values ('admin-0001','admin','admin@example.com','admin','Admin@123', false);
```

### 3) Streamlit Secrets
In Streamlit Cloud → **Settings → Secrets**, paste:
```toml
[supabase]
url = "https://YOUR_PROJECT_ID.supabase.co"
anon_key = "YOUR_ANON_PUBLIC_KEY"
```

### 4) Deploy
- Push this repo to GitHub
- Deploy on Streamlit Cloud (main file: `app.py`)

### 5) Login
- Admin: `admin / Admin@123`

> Replace demo passwords with hashed ones later.

---

## 📑 Pages
- **Students** – Add/update, list all, assign room.
- **Rooms** – Create rooms, set capacity, status.
- **Invoices** – Create invoice, list all, mark status.
- **Maintenance** – Log + track maintenance requests.
- **Staff** – Add staff/admin accounts in `users` table.
- **Resets / Backups** – scaffolds for future.

---

## 🔒 Notes
- This build does **not** use email or bcrypt hashing yet (demo). Add later for production.
- Ensure **RLS is disabled** for the demo tables or add appropriate policies.

---

## 🧹 Migrations
Edit `schema.sql` and re-run in Supabase when you add columns/tables.
