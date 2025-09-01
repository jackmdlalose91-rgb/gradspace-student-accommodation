# Gradspace — Security Update (QR, Invite-Only, Reset Audit)

Adds:
- Public landing + PWA install QR
- Private dashboards (login required)
- First-login password change
- Forgot password via Email + WhatsApp request
- Admin Reset Panel (QR + WhatsApp share + QR download)
- Reset Audit Logs viewer (filter + CSV export)
- Admin Backup downloads (Supabase Storage)

## Secrets (Streamlit Cloud)
```
[supabase]
url = "https://YOURPROJECT.supabase.co"
anon_key = "YOUR_SUPABASE_ANON_KEY"

[email]
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = "587"
EMAIL_USER = "you@example.com"
EMAIL_PASS = "your-app-password"
```

## Deploy
Upload files to GitHub → Redeploy Streamlit app → Run `schema.sql` in Supabase SQL Editor.
