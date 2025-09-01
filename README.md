# Gradspace (Supabase + Cron Reminders)

- Auth with first-login password change
- Student face page (profile, bills, payments, comments)
- Admin/Manager dashboards
- Settings with branding, billing defaults, notification toggles
- **Background reminders** via GitHub Actions running `cron_worker.py`
- PWA support (`.streamlit/public/*`)

## Secrets (Streamlit & GitHub Actions)
Add to Streamlit **Secrets** and GitHub repo **Actions secrets**:

```toml
[supabase]
url = "https://YOURPROJECT.supabase.co"
anon_key = "YOUR_SUPABASE_ANON_KEY"

[email]
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = "587"
EMAIL_USER = "you@example.com"
EMAIL_PASS = "your-app-password"

[app]
currency = "ZAR"
from_name = "Gradspace Team"
```

## Cron Reminders
- The workflow `.github/workflows/cron.yml` runs `cron_worker.py` daily.
- It marks invoices overdue and emails students (and CC managers if enabled).
