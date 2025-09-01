# Gradspace Student Accommodation (Streamlit)

This package includes:
- Multi-role login (admin / manager / student) with **bcrypt** hashed passwords stored in `users.json`.
- **Forgot Password** with email reset code (uses SMTP from Streamlit Secrets).
- Students, Maintenance, Staff, Invoices pages with CSV export and photo uploads.
- PWA assets so users can "Install App" on mobile/desktop (`.streamlit/public/` files).

## Deploy on Streamlit Cloud
- Repo: `jackmdlalose91-rgb/gradspace-student-accommodation`
- Branch: `main`
- Main file path: `app.py`

## Configure Secrets (Settings → Secrets)
```
[users]  # (optional) not used in this version; users are in users.json
# admin = "YOURPASS|admin|Your Admin Name"

[email]
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = "587"
EMAIL_USER = "you@example.com"
EMAIL_PASS = "your-app-password"
```

## Default logins
- admin / admin123 (role: admin)
- manager / manager123 (role: manager)
- student / student123 (role: student)

Change or add users in the app via **Settings → Add/Update user** or directly edit `users.json` (hashes are automatic when using the UI).
